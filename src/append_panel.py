"""增量更新面板:把 data/twse_raw、data/tpex_raw 中「晚於現有 parquet 最後一日」的原始檔
解析後接到 data/processed/twse_daily.parquet 與 twii_daily.csv。

與 build_panel.py 的差異:
- 不重建歷史(原始檔已 gitignore,舊檔可能不在本機)。
- 股數:沿用 data/processed/shares_outstanding.csv(2026-07 快照)以維持歷史市值一致;
  新上市且舊表沒有的代號,才用新快照(data/t187ap03_*.json)補。
- TWSE 限流會回錯誤日期的表(FACTS §3),這裡再檢查一次內嵌日期 = 檔名日期。
"""
from __future__ import annotations

import json
import pathlib
import re
import sys

import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from build_panel import (_num, parse_price_file, parse_t86_file,   # noqa: E402
                         parse_tpex_inst, parse_tpex_price)

PROC = ROOT / "data" / "processed"
RAW_TWSE, RAW_TPEX = ROOT / "data" / "twse_raw", ROOT / "data" / "tpex_raw"


def _date_of(fp: pathlib.Path) -> pd.Timestamp:
    return pd.Timestamp(re.search(r"\d{4}-\d{2}-\d{2}", fp.name).group())


def main() -> int:
    panel = pd.read_parquet(PROC / "twse_daily.parquet")
    twii = pd.read_csv(PROC / "twii_daily.csv", parse_dates=["date"])
    last = panel["date"].max()
    print(f"existing panel through {last.date()} ({panel['date'].nunique()} days)")

    px, twii_rows = [], []
    for fp in sorted(RAW_TWSE.glob("price_*.json")):
        if _date_of(fp) <= last:
            continue
        d = json.loads(fp.read_text())
        if d.get("date") != _date_of(fp).strftime("%Y%m%d"):
            print(f"[SKIP] {fp.name}: embedded date {d.get('date')} != filename")
            continue
        res = parse_price_file(fp)
        if res is None:
            continue
        df, tw = res
        df["market"] = "TWSE"
        px.append(df)
        twii_rows.append((df["date"].iloc[0], tw))
    for fp in sorted(RAW_TPEX.glob("price_*.json")):
        if _date_of(fp) <= last:
            continue
        df = parse_tpex_price(fp)
        if df is not None and len(df):
            df["market"] = "TPEX"
            px.append(df)
    if not px:
        print("nothing new")
        return 0
    prices = pd.concat(px, ignore_index=True).drop_duplicates(["date", "stock"])

    # 備援:上市缺日用 Yahoo 補(見 yahoo_tw_fallback.py 說明);官方檔優先
    yh_dir = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else None
    if yh_dir and yh_dir.exists():
        from yahoo_tw_fallback import load_yahoo_dir, validate_against
        yh = load_yahoo_dir(yh_dir)
        stats = validate_against(panel.loc[panel.market == "TWSE", ["date", "stock", "close"]], yh)
        print("yahoo vs official overlap:", stats)
        have_twse = set(prices.loc[prices.market == "TWSE", "date"].unique())
        tpex_dates = set(prices.loc[prices.market == "TPEX", "date"].unique())
        fill_dates = sorted(d for d in tpex_dates if d not in have_twse and d > last)
        names = panel[panel.market == "TWSE"].drop_duplicates("stock").set_index("stock")["name"]
        fill = yh[yh["date"].isin(fill_dates)].copy()
        fill["name"] = fill["stock"].map(names)
        fill["amount"] = np.nan
        fill["market"] = "TWSE"
        fill["source"] = "yahoo"
        prices["source"] = "official"
        prices = pd.concat([prices, fill[prices.columns]], ignore_index=True)
        print(f"yahoo fill: {len(fill_dates)} TWSE dates, {len(fill)} rows "
              f"({fill_dates[0].date() if fill_dates else None} .. {fill_dates[-1].date() if fill_dates else None})")

    fl = []
    for fp in sorted(RAW_TWSE.glob("t86_*.json")):
        if _date_of(fp) > last and (x := parse_t86_file(fp)) is not None:
            fl.append(x)
    for fp in sorted(RAW_TPEX.glob("inst_*.json")):
        if _date_of(fp) > last and (x := parse_tpex_inst(fp)) is not None:
            fl.append(x)
    flows = (pd.concat(fl, ignore_index=True).drop_duplicates(["date", "stock"])
             if fl else pd.DataFrame(columns=["date", "stock", "foreign_net_sh"]))
    new = prices.merge(flows, on=["date", "stock"], how="left")

    sh = pd.read_csv(PROC / "shares_outstanding.csv", dtype={"stock": str})
    try:
        info = json.loads((ROOT / "data" / "t187ap03_L.json").read_text())
        info_o = json.loads((ROOT / "data" / "t187ap03_O.json").read_text())
        fresh = pd.DataFrame(
            [(c["公司代號"], _num(c["已發行普通股數或TDR原股發行股數"])) for c in info]
            + [(c["SecuritiesCompanyCode"], _num(c["IssueShares"])) for c in info_o],
            columns=["stock", "shares_out"]).drop_duplicates("stock")
        missing = fresh[~fresh["stock"].isin(sh["stock"])]
        if len(missing):
            print(f"shares: {len(missing)} new codes from fresh snapshot")
            sh = pd.concat([sh, missing], ignore_index=True)
            sh.to_csv(PROC / "shares_outstanding.csv", index=False)
    except Exception as e:  # noqa: BLE001
        print("fresh shares snapshot unavailable:", e)
    new = new.merge(sh, on="stock", how="left")
    new["mktcap"] = new["close"] * new["shares_out"]
    src = new.pop("source") if "source" in new else None
    new = new[panel.columns]
    if src is not None:
        new["source"] = src.values
        panel["source"] = "official"

    out = pd.concat([panel, new], ignore_index=True).sort_values(["date", "stock"])
    out.to_parquet(PROC / "twse_daily.parquet", index=False)
    tw_new = pd.DataFrame(twii_rows, columns=["date", "twii"]).dropna()
    twii = pd.concat([twii, tw_new]).drop_duplicates("date").sort_values("date")
    # 官方指數表只隨官方 MI_INDEX 檔而來;Yahoo 補的交易日改用 Yahoo ^TWII 收盤
    # (2026-07 核對:與官方 twii_daily 重疊 ~370 日逐日完全相同)
    us = pd.read_csv(ROOT / "data" / "us_indices_daily.csv", index_col=0, parse_dates=True)
    need = sorted(set(out["date"].unique()) - set(twii["date"]))
    fill = us["twii"].reindex(pd.DatetimeIndex(need)).dropna()
    if len(fill):
        twii = pd.concat([twii, pd.DataFrame({"date": fill.index, "twii": fill.values})]) \
            .drop_duplicates("date").sort_values("date")
        print(f"twii: filled {len(fill)} days from Yahoo ^TWII")
    twii.to_csv(PROC / "twii_daily.csv", index=False)
    print(f"appended {new['date'].nunique()} days / {len(new)} rows; "
          f"panel now through {out['date'].max().date()}, "
          f"{out['date'].nunique()} days, {out['stock'].nunique()} stocks; "
          f"twii rows {len(twii)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

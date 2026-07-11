"""把 TWSE/TPEx 原始 JSON 解析成分析用面板。

輸出(data/processed/):
- twse_daily.parquet:date, stock, name, open, close, volume, amount, foreign_net_sh
- twii_daily.csv:發行量加權股價指數收盤
- shares_outstanding.csv:已發行普通股數(t187ap03_L 當期快照)

已知限制(FACTS 記錄):
- 股價未還原權息 → 個股跨除息日的報酬有向下偏誤;對「週報酬橫斷面排序」影響有限
  (除息分散在 6–9 月、單週幅度小),正式版應改還原價。
- 市值 = 當期已發行股數 × 當日收盤(股數為 2026-07 快照,非歷史逐日),
  用於 VW 權重與濾網(>10 億)是可接受近似。
"""
from __future__ import annotations

import json
import pathlib
import re
import sys

import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW_TWSE = ROOT / "data" / "twse_raw"
OUT = ROOT / "data" / "processed"


def _num(s):
    if s is None:
        return np.nan
    s = str(s).replace(",", "").strip()
    if s in ("--", "", "-", "X", "除權息", "N/A"):
        return np.nan
    try:
        return float(s)
    except ValueError:
        return np.nan


def parse_price_file(fp: pathlib.Path) -> tuple[pd.DataFrame, float] | None:
    d = json.loads(fp.read_text())
    date = pd.to_datetime(d["date"], format="%Y%m%d")
    # 個股表:fields 含 證券代號+收盤價 且列數最多者
    stock_tbl, twii = None, np.nan
    for t in d.get("tables", []):
        f = t.get("fields", [])
        if "證券代號" in f and "收盤價" in f:
            if stock_tbl is None or len(t["data"]) > len(stock_tbl["data"]):
                stock_tbl = t
        if "指數" in f:
            for row in t.get("data", []):
                if row and row[0] == "發行量加權股價指數":
                    twii = _num(row[1])
    if stock_tbl is None:
        return None
    f = stock_tbl["fields"]
    ix = {k: f.index(k) for k in ("證券代號", "證券名稱", "成交股數", "成交金額",
                                  "開盤價", "收盤價")}
    rows = []
    for r in stock_tbl["data"]:
        code = r[ix["證券代號"]].strip()
        # 只留 4 碼普通股(排除 ETF 00xx、權證、特別股後綴)
        if not re.fullmatch(r"[1-9]\d{3}", code):
            continue
        rows.append((date, code, r[ix["證券名稱"]].strip(),
                     _num(r[ix["開盤價"]]), _num(r[ix["收盤價"]]),
                     _num(r[ix["成交股數"]]), _num(r[ix["成交金額"]])))
    df = pd.DataFrame(rows, columns=["date", "stock", "name", "open", "close",
                                     "volume", "amount"])
    return df, twii


def parse_t86_file(fp: pathlib.Path) -> pd.DataFrame | None:
    d = json.loads(fp.read_text())
    if d.get("stat") != "OK":
        return None
    date = pd.to_datetime(d["date"], format="%Y%m%d")
    f = d["fields"]
    try:
        i_code = f.index("證券代號")
        i_fn = f.index("外陸資買賣超股數(不含外資自營商)")
    except ValueError:
        return None
    rows = [(date, r[i_code].strip(), _num(r[i_fn])) for r in d["data"]
            if re.fullmatch(r"[1-9]\d{3}", r[i_code].strip())]
    return pd.DataFrame(rows, columns=["date", "stock", "foreign_net_sh"])


RAW_TPEX = ROOT / "data" / "tpex_raw"


def parse_tpex_price(fp: pathlib.Path) -> pd.DataFrame | None:
    d = json.loads(fp.read_text())
    tbl = None
    for t in d.get("tables", []):
        f = [c.strip() for c in t.get("fields", [])]
        if "代號" in f and "收盤" in f:
            tbl = t
            fields = f
            break
    if tbl is None:
        return None
    date = pd.to_datetime(fp.stem.split("_")[1])
    ix = {k: fields.index(k) for k in ("代號", "名稱", "收盤", "開盤", "成交股數")}
    rows = []
    for r in tbl["data"]:
        code = str(r[ix["代號"]]).strip()
        if not re.fullmatch(r"[1-9]\d{3}", code):
            continue
        rows.append((date, code, str(r[ix["名稱"]]).strip(),
                     _num(r[ix["開盤"]]), _num(r[ix["收盤"]]),
                     _num(r[ix["成交股數"]]), np.nan))
    return pd.DataFrame(rows, columns=["date", "stock", "name", "open", "close",
                                       "volume", "amount"])


def parse_tpex_inst(fp: pathlib.Path) -> pd.DataFrame | None:
    d = json.loads(fp.read_text())
    tbl = next((t for t in d.get("tables", []) if t.get("data")), None)
    if tbl is None:
        return None
    date = pd.to_datetime(fp.stem.split("_")[1])
    # 欄位群組:代號,名稱,(外資及陸資 買/賣/買賣超)…第 4 欄 = 外資買賣超
    rows = [(date, str(r[0]).strip(), _num(r[4])) for r in tbl["data"]
            if re.fullmatch(r"[1-9]\d{3}", str(r[0]).strip())]
    return pd.DataFrame(rows, columns=["date", "stock", "foreign_net_sh"])


def build() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    px, twii_rows = [], []
    for fp in sorted(RAW_TWSE.glob("price_*.json")):
        res = parse_price_file(fp)
        if res is None:
            continue
        df, twii = res
        df["market"] = "TWSE"
        px.append(df)
        twii_rows.append((df["date"].iloc[0], twii))
    for fp in sorted(RAW_TPEX.glob("price_*.json")):
        df = parse_tpex_price(fp)
        if df is not None and len(df):
            df["market"] = "TPEX"
            px.append(df)
    prices = pd.concat(px, ignore_index=True)

    t86 = [x for fp in sorted(RAW_TWSE.glob("t86_*.json"))
           if (x := parse_t86_file(fp)) is not None]
    t86 += [x for fp in sorted(RAW_TPEX.glob("inst_*.json"))
            if (x := parse_tpex_inst(fp)) is not None]
    flows = pd.concat(t86, ignore_index=True) \
        .drop_duplicates(subset=["date", "stock"])
    prices = prices.drop_duplicates(subset=["date", "stock"], keep="first")
    panel = prices.merge(flows, on=["date", "stock"], how="left")

    # 已發行股數(上市 t187ap03_L + 上櫃 mopsfin_t187ap03_O)
    info = json.loads((ROOT / "data" / "t187ap03_L.json").read_text())
    sh_l = [(c["公司代號"], _num(c["已發行普通股數或TDR原股發行股數"])) for c in info]
    try:
        info_o = json.loads((ROOT / "data" / "t187ap03_O.json").read_text())
        sh_o = [(c["SecuritiesCompanyCode"], _num(c["IssueShares"])) for c in info_o]
    except Exception:  # noqa: BLE001
        sh_o = []
    sh = pd.DataFrame(sh_l + sh_o, columns=["stock", "shares_out"]) \
        .drop_duplicates(subset="stock")
    panel = panel.merge(sh, on="stock", how="left")
    panel["mktcap"] = panel["close"] * panel["shares_out"]

    panel.to_parquet(OUT / "twse_daily.parquet", index=False)
    pd.DataFrame(twii_rows, columns=["date", "twii"]).dropna() \
        .to_csv(OUT / "twii_daily.csv", index=False)
    sh.to_csv(OUT / "shares_outstanding.csv", index=False)
    print(f"panel: {panel.shape}, stocks: {panel['stock'].nunique()}, "
          f"days: {panel['date'].nunique()}, "
          f"tpex_share: {(panel['market'] == 'TPEX').mean():.2f}")


if __name__ == "__main__":
    sys.exit(build())

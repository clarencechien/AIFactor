"""ai_premium_tw — 真實資料實驗(TWSE 上市樣本)。

前置:fetch_twse/fetch_tpex 抓完、build_panel.py 建好 data/processed/、
     build_consumption_factor.py 產出 data/openrouter_weekly.csv。
因子:consumption = OpenRouter 週 token log 成長 z-score(降級單腿,2024-03 起)
     supply      = SOX 週報酬對 S&P500 迴歸殘差 z-score(供給端純化)

跑:
  R1   Design 1 事件研究(消費 beta 分組;論文 IA.16 前沿日曆,T+1 五日 CAR,
       隔夜/盤中拆解,非前沿安慰劑);R1b 用 SOX-殘差 beta 做穩健性
  R2   Design 2 雙因子賽馬(H1 消費 vs H2 供給),五分位 VW 排序 + FM + 動能糾纏,
       以區間估計語言報告(檢定力見 reports/experiment_report.md E2P)
  R3   Design 3 外資中介:5×3 雙重排序 + λ 水準對照 + 隔夜/盤中路徑分解
輸出 reports/real_results.json
"""
from __future__ import annotations

import json
import pathlib
import sys

import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from design1_event_study import block_bootstrap_pvalue          # noqa: E402
from design2_horse_race import (fama_macbeth, momentum_entanglement,  # noqa: E402
                                newey_west_t, vw_quintile_hl)
from design3_flow_mediation import double_sort                   # noqa: E402
from rolling_beta import rolling_ai_beta                         # noqa: E402

PROC = ROOT / "data" / "processed"
MIN_CAP = 1e9      # 市值 > 新台幣 10 億
MIN_PX = 10.0      # 股價 > 10 元


def load_matrices():
    """回傳 dict:日頻 close/open/flow 矩陣、週頻報酬、市場、因子。"""
    panel = pd.read_parquet(PROC / "twse_daily.parquet")
    panel = panel.sort_values(["date", "stock"])

    close = panel.pivot(index="date", columns="stock", values="close")
    open_ = panel.pivot(index="date", columns="stock", values="open")
    fnet = panel.pivot(index="date", columns="stock", values="foreign_net_sh")
    cap = panel.pivot(index="date", columns="stock", values="mktcap")

    # 濾網(逐日):價>10、市值>10億;不符者當日設 NaN(形成期自然排除)
    mask = (close > MIN_PX) & (cap > MIN_CAP)
    close, open_ = close.where(mask), open_.where(mask)

    twii = pd.read_csv(PROC / "twii_daily.csv", parse_dates=["date"]) \
        .set_index("date")["twii"]

    us = pd.read_csv(ROOT / "data" / "us_indices_daily.csv",
                     index_col=0, parse_dates=True)

    # 週頻(W-FRI)
    close_w = close.resample("W-FRI").last()
    ret_w = np.log(close_w).diff()
    twii_w = np.log(twii.resample("W-FRI").last()).diff()
    sox_w = np.log(us["sox"].resample("W-FRI").last()).diff()
    spx_w = np.log(us["spx"].resample("W-FRI").last()).diff()

    # 供給端因子:SOX 對 SPX 全樣本殘差,z-score
    idx = sox_w.dropna().index.intersection(spx_w.dropna().index)
    x = np.column_stack([np.ones(len(idx)), spx_w.loc[idx].values])
    coef, *_ = np.linalg.lstsq(x, sox_w.loc[idx].values, rcond=None)
    resid = pd.Series(sox_w.loc[idx].values - x @ coef, index=idx)
    factor_w = ((resid - resid.mean()) / resid.std())

    # 消費因子(降級單腿):OpenRouter 週 token log 成長,z-score。
    # token 週為週一起算,對齊到該週的週五(+4 天);週末 token 溢入 ≈ 2/7,
    # 屬對齊近似(FACTS 旗標),對共變估計影響二階。
    orw = pd.read_csv(ROOT / "data" / "openrouter_weekly.csv",
                      parse_dates=["week_monday"])
    tok = pd.Series(orw["total_tokens"].values,
                    index=orw["week_monday"] + pd.Timedelta(days=4))
    g = np.log(tok).diff().dropna()
    factor_cons = ((g - g.mean()) / g.std())

    # 對齊週索引(交集以消費因子可得性為準 → 2024-03 起)
    weeks = ret_w.index.intersection(twii_w.dropna().index) \
        .intersection(factor_w.index).intersection(factor_cons.index)
    weeks = weeks[weeks >= "2024-01-01"]
    ret_w, twii_w = ret_w.loc[weeks], twii_w.loc[weeks]
    factor_w, factor_cons = factor_w.loc[weeks], factor_cons.loc[weeks]

    # 外資流:週累積買賣超金額佔市值比(×1e4 = bps)
    flow_val = (fnet * close).resample("W-FRI").sum()
    cap_w = cap.resample("W-FRI").last()
    flow_w = (flow_val / cap_w).loc[weeks[weeks.isin(flow_val.index)]]

    cap_form = cap_w.reindex(ret_w.index)  # VW 權重(形成週市值)
    return dict(close_d=close, open_d=open_, twii_d=twii, panel_dates=close.index,
                ret_w=ret_w, twii_w=twii_w, factor_w=factor_w,
                factor_cons=factor_cons, flow_w=flow_w, cap_w=cap_form)


def compute_betas(m, which: str = "cons"):
    R = m["ret_w"].values
    f = m["factor_cons"].values if which == "cons" else m["factor_w"].values
    return rolling_ai_beta(R, f, m["twii_w"].values)


def design1(m, betas):
    cal = pd.read_csv(ROOT / "data" / "model_releases_paper_ia16.csv",
                      parse_dates=["date_utc"])
    dates = m["panel_dates"]
    close, open_ = m["close_d"], m["open_d"]
    ret_d = close.pct_change()
    on_d = open_ / close.shift(1) - 1
    in_d = close / open_ - 1
    twii_ret = m["twii_d"].reindex(dates).pct_change()
    ar_d = ret_d.sub(twii_ret, axis=0)          # 市場調整(β=1 近似)

    week_idx = m["ret_w"].index

    def run_events(sub):
        rows = []
        for _, ev in sub.iterrows():
            # 台股 T+1 = 發布日後第一個實際交易日
            after = dates[dates > ev.date_utc]
            if len(after) < 5:
                continue
            t1 = after[0]
            di = dates.get_loc(t1)
            if di + 5 > len(dates):
                continue
            # 事前 beta:事件前最後一個完整形成週
            wk_prior = week_idx[week_idx < t1]
            if not len(wk_prior):
                continue
            wi = week_idx.get_loc(wk_prior[-1])
            b = betas[wi]
            ok = ~np.isnan(b)
            if ok.sum() < 100:
                continue
            lo_c, hi_c = np.nanquantile(b[ok], [0.3, 0.7])
            hi, lo = ok & (b >= hi_c), ok & (b <= lo_c)
            win = slice(di, di + 5)
            out = {}
            for nm, mat in [("total", ar_d), ("overnight", on_d), ("intraday", in_d)]:
                car = mat.iloc[win].sum(axis=0).values
                # 通道用原始報酬,H−L 相減已消掉市場成分
                out[nm] = float(np.nanmean(car[hi]) - np.nanmean(car[lo]))
            rows.append(dict(date=str(ev.date_utc.date()), model=ev.model, **out))
        return pd.DataFrame(rows)

    res = {}
    for name, flag in [("frontier", 1), ("nonfrontier_placebo", 0)]:
        df = run_events(cal[cal.frontier_flag == flag])
        stats = {}
        for ch in ("total", "overnight", "intraday"):
            x = df[ch].dropna().values
            if len(x) > 3:
                mean = float(x.mean())
                t = mean / (x.std(ddof=1) / np.sqrt(len(x)))
                bp = block_bootstrap_pvalue(x)
            else:
                mean, t, bp = np.nan, np.nan, None
            stats[ch] = dict(mean_hl_pct=100 * mean, t=t, boot_p=bp, n=len(x))
        res[name] = dict(n_events=len(df), stats=stats,
                         per_event=df.to_dict("records"))
    return res


def design2(m, betas):
    R, cap = m["ret_w"].values, m["cap_w"].values
    T, N = R.shape
    # 逐週 VW(權重=形成週市值)
    hl = np.full(T, np.nan)
    qmeans = np.full((T, 5), np.nan)
    from rolling_beta import quintile_assign
    for t in range(1, T):
        q = quintile_assign(betas[t - 1])
        w = cap[t - 1]
        r = R[t]
        ok = (q >= 0) & ~np.isnan(r) & ~np.isnan(w)
        if ok.sum() < 50:
            continue
        for g in range(5):
            sel = ok & (q == g)
            if sel.any():
                qmeans[t, g] = np.average(r[sel], weights=w[sel])
        hl[t] = qmeans[t, 4] - qmeans[t, 0]
    mean, t = newey_west_t(hl)
    x = hl[~np.isnan(hl)]
    se = np.abs(mean / t) if t else np.nan
    ci = (mean - 1.96 * se, mean + 1.96 * se)
    fm = fama_macbeth(R, betas)
    mom = momentum_entanglement(R, betas)
    return dict(hl_bps=1e4 * mean, t=t, n_weeks=int(len(x)),
                ci_bps=[1e4 * ci[0], 1e4 * ci[1]],
                quintile_mean_bps=[1e4 * np.nanmean(qmeans[:, g]) for g in range(5)],
                fm_lambda_bps=fm["ai_beta"]["lambda_bps"], fm_t=fm["ai_beta"]["t_stat"],
                momentum_by_quintile=list(map(float, mom)))


def design3(m, betas):
    R = m["ret_w"].values
    flow = m["flow_w"].reindex(index=m["ret_w"].index,
                               columns=m["ret_w"].columns).values
    cap = np.nanmedian(m["cap_w"].values, axis=0)  # 靜態權重供 double_sort 簡化
    ds = double_sort(R, betas, flow, np.where(np.isnan(cap), 1.0, cap))
    fm_base = fama_macbeth(R, betas)
    lag_flow = np.vstack([flow[1:], np.full((1, flow.shape[1]), np.nan)])
    fm_flow = fama_macbeth(R, betas, controls={"flow_t": lag_flow, "flow_t1": flow})

    # 路徑分解:週頻隔夜/盤中
    on_w = (m["open_d"] / m["close_d"].shift(1) - 1).resample("W-FRI") \
        .apply(lambda x: (1 + x).prod() - 1).reindex(m["ret_w"].index)
    in_w = (m["close_d"] / m["open_d"] - 1).resample("W-FRI") \
        .apply(lambda x: (1 + x).prod() - 1).reindex(m["ret_w"].index)
    path = {}
    for nm, mat in [("overnight", on_w.values), ("intraday", in_w.values)]:
        r = vw_quintile_hl(mat, betas, np.where(np.isnan(cap), 1.0, cap))
        path[nm] = dict(hl_bps=r["hl_bps_per_week"], t=r["t_stat"])
    return dict(double_sort={k: v for k, v in ds.items()},
                fm_lambda_base=fm_base["ai_beta"],
                fm_lambda_withflow=fm_flow["ai_beta"], path=path)


def main():
    m = load_matrices()
    print(f"weeks={len(m['ret_w'])}, stocks={m['ret_w'].shape[1]}", flush=True)
    b_cons = compute_betas(m, "cons")
    b_sox = compute_betas(m, "sox")
    print("betas done; coverage last week: cons",
          int((~np.isnan(b_cons[-1])).sum()), "sox",
          int((~np.isnan(b_sox[-1])).sum()), flush=True)
    out = {
        "R1_design1_event_study_consbeta": design1(m, b_cons),
        "R1b_design1_soxbeta_robustness": design1(m, b_sox),
        "R2_horse_race": {
            "consumption_openrouter": design2(m, b_cons),   # H1 主檢定
            "supply_sox_residual": design2(m, b_sox),        # H2 代理
        },
        "R3_design3_flow_mediation_consbeta": design3(m, b_cons),
        "_meta": {
            "sample": "TWSE+TPEx 普通股(4 碼),價>10、市值>10億,未還原權息",
            "factors": ("consumption = OpenRouter 週 token log 成長 z-score"
                        "(Wayback 縫合,2024-03 起,重疊驗證 max 0.04%);"
                        "supply = SOX~SPX 週殘差 z-score"),
            "calendar": "論文 Table IA.16(19 前沿 + 28 非前沿)",
            "date": "2026-07-10",
        },
    }
    fp = ROOT / "reports" / "real_results.json"
    fp.write_text(json.dumps(out, indent=2, ensure_ascii=False, default=float))
    print("saved →", fp)


if __name__ == "__main__":
    main()

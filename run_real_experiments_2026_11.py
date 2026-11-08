"""ai_premium_tw — 2026-11 複跑:樣本延長到 2026-11-06,並加「過去四個月」診斷。

相對 run_real_experiments.py(2026-07-10 版)的差異:
- 消費因子延長到 2026-10-30 週(OpenRouter 即時圖 + 舊 Wayback 縫合;11-02 週未完不用)
- 供給因子(SOX 殘差)延長到 2026-11-06 週
- R1 除論文 IA.16 日曆外,加跑「延伸日曆」(data/model_releases.csv,含 2026-05~11 事件)
- R4 新增:子期間(≤2026-07-10 vs 之後)、2026-10-06 高點後回檔週、11-02 崩盤週的
  AI-beta 五分位表現、token 成長趨勢 —— 回答「AI 熄火了嗎」
輸出 reports/real_results_2026-11.json
"""
from __future__ import annotations

import json
import pathlib
import sys

import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

import run_real_experiments as base                                 # noqa: E402
from design2_horse_race import newey_west_t                         # noqa: E402
from rolling_beta import quintile_assign                            # noqa: E402

SPLIT = pd.Timestamp("2026-07-10")       # 上一版樣本終點
TWII_PEAK = pd.Timestamp("2026-10-06")   # 加權指數收盤高點(Yahoo 日資料)


def load_matrices_ext():
    """base.load_matrices 的延伸:把『供給因子可得但消費因子缺』的尾週保留給 SOX 檢定。"""
    m = base.load_matrices()
    # base 會把週索引交集到消費因子 → 尾端(11-02 週)被切掉;另存一份只交集 SOX 的
    panel = pd.read_parquet(base.PROC / "twse_daily.parquet").sort_values(["date", "stock"])
    close = panel.pivot(index="date", columns="stock", values="close")
    cap = panel.pivot(index="date", columns="stock", values="mktcap")
    mask = (close > base.MIN_PX) & (cap > base.MIN_CAP)
    close = close.where(mask)
    ret_w_all = np.log(close.resample("W-FRI").last()).diff()
    m["ret_w_all"] = ret_w_all
    m["cap_w_all"] = cap.resample("W-FRI").last().reindex(ret_w_all.index)
    return m


def quintile_week_returns(R_row, cap_row, beta_prev):
    q = quintile_assign(beta_prev)
    ok = (q >= 0) & ~np.isnan(R_row) & ~np.isnan(cap_row)
    out = [np.nan] * 5
    for g in range(5):
        sel = ok & (q == g)
        if sel.any():
            out[g] = float(np.average(R_row[sel], weights=cap_row[sel]))
    return out


def hl_series(m, betas):
    """逐週 VW 五分位報酬與 H−L(與 base.design2 同邏輯,但回傳序列)。"""
    R, cap = m["ret_w"].values, m["cap_w"].values
    T = R.shape[0]
    qm = np.full((T, 5), np.nan)
    for t in range(1, T):
        if (~np.isnan(betas[t - 1])).sum() < 50:
            continue
        qm[t] = quintile_week_returns(R[t], cap[t - 1], betas[t - 1])
    qm = pd.DataFrame(qm, index=m["ret_w"].index, columns=[f"Q{i}" for i in range(1, 6)])
    qm["HL"] = qm["Q5"] - qm["Q1"]
    return qm


def summarize(x: pd.Series) -> dict:
    x = x.dropna()
    mean, t = newey_west_t(x.values)
    if np.isnan(mean) and len(x):          # n<10:NW 不算,仍回報平均(t 留 NaN,只看方向)
        mean = float(x.mean())
    se = abs(mean / t) if t and not np.isnan(t) else np.nan
    return dict(hl_bps=1e4 * mean, t=t, n_weeks=int(len(x)),
                ci_bps=[1e4 * (mean - 1.96 * se), 1e4 * (mean + 1.96 * se)],
                cum_pct=100 * float(np.expm1(x.sum())))


def design4(m, b_cons, b_sox):
    out = {}
    qm = {"consumption": hl_series(m, b_cons), "supply": hl_series(m, b_sox)}
    for nm, df in qm.items():
        out[nm] = {
            "full": summarize(df["HL"]),
            "pre_2026_07_10": summarize(df.loc[df.index <= SPLIT, "HL"]),
            "post_2026_07_10": summarize(df.loc[df.index > SPLIT, "HL"]),
            "post_twii_peak": summarize(df.loc[df.index > TWII_PEAK, "HL"]),
            "quintile_mean_bps_post": [1e4 * df.loc[df.index > SPLIT, f"Q{i}"].mean()
                                       for i in range(1, 6)],
            "quintile_cum_pct_post": [100 * float(np.expm1(df.loc[df.index > SPLIT, f"Q{i}"].sum()))
                                      for i in range(1, 6)],
            "quintile_cum_pct_post_peak": [100 * float(np.expm1(df.loc[df.index > TWII_PEAK, f"Q{i}"].sum()))
                                           for i in range(1, 6)],
            "quintile_cum_pct_pre": [100 * float(np.expm1(df.loc[df.index <= SPLIT, f"Q{i}"].sum()))
                                     for i in range(1, 6)],
            "weekly_hl_bps_post": {str(k.date()): round(1e4 * v, 1)
                                   for k, v in df.loc[df.index > SPLIT, "HL"].dropna().items()},
            "weekly_q_post": {str(k.date()): [round(1e4 * v, 1) for v in row]
                              for k, row in df.loc[df.index > SPLIT, [f"Q{i}" for i in range(1, 6)]].iterrows()},
        }
    # 崩盤週(2026-11-02~06):用 10-30 的 beta 分組,看高低曝險組各跌多少
    Rall, capall = m["ret_w_all"], m["cap_w_all"]
    last_beta_week = m["ret_w"].index[-1]
    crash = {}
    for wk in Rall.index[Rall.index > last_beta_week]:
        row = {}
        for nm, b in (("consumption", b_cons), ("supply", b_sox)):
            qr = quintile_week_returns(Rall.loc[wk].values, m["cap_w"].iloc[-1].values, b[-1])
            row[nm] = dict(quintile_pct=[100 * v for v in qr], hl_pct=100 * (qr[4] - qr[0]))
        row["twii_pct"] = 100 * float(np.expm1(np.log(m["twii_d"]).diff().loc[
            (m["twii_d"].index > wk - pd.Timedelta(days=7)) & (m["twii_d"].index <= wk)].sum()))
        crash[str(wk.date())] = row
    out["weeks_after_factor_end"] = crash

    # 市場脈絡
    us = pd.read_csv(ROOT / "data" / "us_indices_daily.csv", index_col=0, parse_dates=True)
    twii_d = m["twii_d"].dropna()
    def path(s, pts):
        return {k: float(s.asof(pd.Timestamp(v))) for k, v in pts.items()}
    pts = {"2026-07-09": "2026-07-09", "sox_peak_2026-06-22": "2026-06-22",
           "twii_peak_2026-10-06": "2026-10-06", "2026-11-06": "2026-11-06"}
    out["market_context"] = {
        "sox": path(us["sox"].dropna(), pts), "spx": path(us["spx"].dropna(), pts),
        "twii": path(twii_d, pts),
        "sox_drawdown_from_peak_pct": 100 * (us["sox"].dropna().iloc[-1] / us["sox"].max() - 1),
        "twii_drawdown_from_peak_pct": 100 * (twii_d.iloc[-1] / twii_d.max() - 1),
    }
    # 台積電與 AI 曝險最高/最低組的近四個月
    close = pd.read_parquet(base.PROC / "twse_daily.parquet").pivot(index="date", columns="stock", values="close")
    tsmc = close["2330"].dropna()
    out["tsmc_2330"] = {"2026-07-09": float(tsmc.asof(SPLIT)), "peak_date": str(tsmc.idxmax().date()),
                        "peak": float(tsmc.max()), "2026-11-06": float(tsmc.iloc[-1]),
                        "ret_since_0709_pct": 100 * (tsmc.iloc[-1] / tsmc.asof(SPLIT) - 1)}
    # token 成長趨勢
    orw = pd.read_csv(ROOT / "data" / "openrouter_weekly.csv", parse_dates=["week_monday"]).set_index("week_monday")["total_tokens"]
    g = np.log(orw).diff()
    out["openrouter_tokens"] = {
        "last_week": str(orw.index[-1].date()), "last_value": float(orw.iloc[-1]),
        "growth_since_2026_04_20_x": float(orw.iloc[-1] / orw.loc["2026-04-20"]),
        "growth_yoy_x": float(orw.iloc[-1] / orw.loc["2025-10-27"]),
        "mean_weekly_log_growth": {"2025": float(g.loc["2025"].mean()), "2026H1": float(g.loc["2026-01":"2026-06"].mean()),
                                   "2026-07..10": float(g.loc["2026-07":].mean())},
        "weekly_pct_change_since_2026_05": {str(k.date()): round(100 * float(np.expm1(v)), 1)
                                            for k, v in g.loc["2026-05":].items()},
        "weekly_level_T_since_2026_05": {str(k.date()): round(float(v) / 1e12, 1)
                                         for k, v in orw.loc["2026-05":].items()},
    }
    return out


def design1_calendar(m, betas, calendar_csv: str, min_date: str | None = None):
    """base.design1 但換日曆(含子期間濾網)。"""
    cal_fp = ROOT / "data" / calendar_csv
    orig = base.pd.read_csv

    def patched(fp, *a, **k):
        df = orig(fp, *a, **k)
        if str(fp).endswith("model_releases_paper_ia16.csv"):
            df = orig(cal_fp, *a, **k)
            if min_date:
                df = df[df.date_utc >= pd.Timestamp(min_date)]
        return df
    base.pd.read_csv = patched
    try:
        return base.design1(m, betas)
    finally:
        base.pd.read_csv = orig


def main():
    m = load_matrices_ext()
    print(f"weeks={len(m['ret_w'])} ({m['ret_w'].index[0].date()}..{m['ret_w'].index[-1].date()}), "
          f"stocks={m['ret_w'].shape[1]}; all-weeks through {m['ret_w_all'].index[-1].date()}", flush=True)
    b_cons = base.compute_betas(m, "cons")
    b_sox = base.compute_betas(m, "sox")
    out = {
        "R1_design1_paper_calendar_consbeta": base.design1(m, b_cons),
        "R1c_design1_extended_calendar_consbeta": design1_calendar(m, b_cons, "model_releases.csv"),
        "R1d_design1_extended_calendar_2026H2_only": design1_calendar(m, b_cons, "model_releases.csv", "2026-05-01"),
        "R1e_design1_extended_calendar_soxbeta": design1_calendar(m, b_sox, "model_releases.csv"),
        "R2_horse_race": {
            "consumption_openrouter": base.design2(m, b_cons),
            "supply_sox_residual": base.design2(m, b_sox),
        },
        "R3_design3_flow_mediation_consbeta": base.design3(m, b_cons),
        "R4_subperiods_and_cooling": design4(m, b_cons, b_sox),
        "_meta": {
            "sample": "TWSE+TPEx 普通股(4 碼),價>10、市值>10億,未還原權息",
            "weeks": [str(m["ret_w"].index[0].date()), str(m["ret_w"].index[-1].date()), int(len(m["ret_w"]))],
            "factors": ("consumption = OpenRouter 週 token log 成長 z-score(Wayback 縫合 2024-03~2026-04 + "
                        "2026-11-08 即時 rankings 圖 2026-04~2026-10,重疊 24 週 max 0.43%);"
                        "supply = SOX~SPX 週殘差 z-score(到 2026-11-06)"),
            "calendars": "論文 IA.16(19+28)/ 延伸日曆 data/model_releases.csv(含 2026-05~11 事件,OpenRouter 目錄日)",
            "date": "2026-11-08",
        },
    }
    fp = ROOT / "reports" / "real_results_2026-11.json"
    fp.write_text(json.dumps(out, indent=2, ensure_ascii=False, default=float))
    print("saved →", fp)


if __name__ == "__main__":
    main()

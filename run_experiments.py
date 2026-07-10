"""ai_premium_tw — 全實驗執行器(2026-07-10 環境:真實資料被網路政策封鎖)。

跑的內容(全部合成資料,驗證管線正確性 + 檢定力,非台股實證):
  E1  Design 1 事件研究:虛無 size 檢查 / 注入回收 / 隔夜通道辨識 / 安慰劑
  E2  Design 2 賽馬:虛無 / H1 型 / H2 型情境,含動能糾纏檢查
  E2P 檢定力分析:H−L 溢酬 × 因子品質(論文級 vs 降級單腿)→ 拒絕率
  E3  Design 3 中介:虛無 / 強中介情境的雙重排序 + FM 衰減 + 通道拆解
輸出:reports/experiment_results.json + stdout 摘要。
"""
from __future__ import annotations

import json
import pathlib
import sys
import time

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from design1_event_study import run_design1                     # noqa: E402
from design2_horse_race import horse_race, vw_quintile_hl        # noqa: E402
from design3_flow_mediation import (double_sort, mediation_fm,   # noqa: E402
                                    path_decomposition_weekly)
from rolling_beta import rolling_ai_beta                         # noqa: E402
from synthetic import SimConfig, simulate_daily_around_events, \
    simulate_weekly_panel                                        # noqa: E402


def e1_event_study() -> dict:
    out = {}
    # (a) 虛無:無事件效果 → 不應顯著
    cfg = SimConfig(seed=11, event_hl_car_pct=0.0)
    d = simulate_daily_around_events(cfg)
    placebo = d["event_days"] + 12   # 事件間隔 >20 天,+12 不與 5 日窗重疊
    r = run_design1(d["ret_total"], d["overnight"], d["intraday"], d["mkt"],
                    d["beta_est"], d["event_days"], placebo)
    out["null"] = {k: dict(hl_pct=100 * v["mean_hl"], t=v["t_stat"],
                           boot_p=v.get("boot_p"))
                   for k, v in r.items()}
    # (b) 注入論文量級:H−L CAR +1.9%,80% 走隔夜(H3 型傳導)
    cfg = SimConfig(seed=12, event_hl_car_pct=1.9, overnight_share=0.8)
    d = simulate_daily_around_events(cfg)
    placebo = d["event_days"] + 12
    r = run_design1(d["ret_total"], d["overnight"], d["intraday"], d["mkt"],
                    d["beta_est"], d["event_days"], placebo)
    out["injected_1.9pct_overnight80"] = {
        k: dict(hl_pct=100 * v["mean_hl"], t=v["t_stat"], boot_p=v.get("boot_p"))
        for k, v in r.items()}
    return out


def e2_horse_race() -> dict:
    out = {}
    scenarios = {
        "null": SimConfig(seed=21),
        "H1_type_consumption_18bps": SimConfig(seed=22, premium_consumption_bps=18),
        "H2_type_capex_only_18bps": SimConfig(seed=23, premium_capex_bps=18),
        "paper_scale_consumption_64bps": SimConfig(seed=24, premium_consumption_bps=64),
    }
    for name, cfg in scenarios.items():
        p = simulate_weekly_panel(cfg)
        r = horse_race(p["returns"], p["mkt"], p["factor_obs"], p["capex_factor"],
                       p["me"])
        out[name] = {
            lbl: dict(hl_bps=v["sort"]["hl_bps_per_week"], t=v["sort"]["t_stat"],
                      fm_lambda_bps=v["fm"]["ai_beta"]["lambda_bps"],
                      fm_t=v["fm"]["ai_beta"]["t_stat"],
                      mom_q1_q5=[float(v["momentum_by_quintile"][0]),
                                 float(v["momentum_by_quintile"][4])])
            for lbl, v in r.items()}
    return out


def e2p_power(n_sims: int = 200) -> dict:
    """檢定力:目標 H−L ∈ {10,20,30,64} bps × 因子品質(0=論文級, 1.0=降級單腿)。

    降級單腿 = 觀測因子混入等方差噪音(token 單腿 vs 三腿 PCA 的粗略對應)。
    拒絕 = H−L 之 NW t > 1.96。另記錄「有效檢定力」對 EM 量級 18bps 的含義。
    """
    grid_premium = [0, 10, 20, 30, 64]
    grid_noise = [0.0, 1.0]
    res = {}
    for noise in grid_noise:
        for prem in grid_premium:
            rej, est = 0, []
            for s in range(n_sims):
                cfg = SimConfig(seed=1000 + s, n_stocks=400,
                                premium_consumption_bps=prem,
                                factor_obs_noise=noise)
                p = simulate_weekly_panel(cfg)
                b = rolling_ai_beta(p["returns"], p["factor_obs"], p["mkt"])
                r = vw_quintile_hl(p["returns"], b, p["me"])
                if np.isfinite(r["t_stat"]) and r["t_stat"] > 1.96:
                    rej += 1
                est.append(r["hl_bps_per_week"])
            res[f"noise{noise}_prem{prem}"] = dict(
                power=rej / n_sims,
                mean_recovered_hl_bps=float(np.nanmean(est)))
    return res


def e3_mediation() -> dict:
    out = {}
    for name, cfg in {
        "null_premium20_no_mediation": SimConfig(seed=31, premium_consumption_bps=20,
                                                 flow_mediation=0.0),
        "mediated80_premium20": SimConfig(seed=32, premium_consumption_bps=20,
                                          flow_mediation=0.8),
    }.items():
        p = simulate_weekly_panel(cfg)
        b = rolling_ai_beta(p["returns"], p["factor_obs"], p["mkt"])
        ds = double_sort(p["returns"], b, p["flow"], p["me"])
        med = mediation_fm(p["returns"], b, p["flow"])
        out[name] = dict(
            double_sort={k: dict(hl_bps=v["hl_bps"], t=v["t_stat"])
                         for k, v in ds.items()},
            fm_attenuation_pct=med["attenuation_pct"],
            fm_base_lambda=med["base"]["ai_beta"]["lambda_bps"],
            fm_withflow_lambda=med["with_flow"]["ai_beta"]["lambda_bps"])
    return out


def main() -> int:
    t0 = time.time()
    results = {}
    print("E1 Design1 事件研究驗證 ...", flush=True)
    results["E1_event_study"] = e1_event_study()
    print("E2 Design2 賽馬驗證 ...", flush=True)
    results["E2_horse_race"] = e2_horse_race()
    print("E2P 檢定力分析(~2000 sims,最花時間)...", flush=True)
    results["E2P_power"] = e2p_power()
    print("E3 Design3 中介驗證 ...", flush=True)
    results["E3_mediation"] = e3_mediation()
    results["_meta"] = dict(
        runtime_sec=round(time.time() - t0, 1),
        data="SYNTHETIC_ONLY — 非台股實證;見 FACTS.md §0 網路封鎖記錄",
        date="2026-07-10")
    out = ROOT / "reports" / "experiment_results.json"
    out.write_text(json.dumps(results, indent=2, ensure_ascii=False, default=float))
    print(f"done in {results['_meta']['runtime_sec']}s → {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

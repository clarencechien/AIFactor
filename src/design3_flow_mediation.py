"""Design 3 — 外資流中介檢定(H3;handoff §3 Design 3)。

1. 雙重排序:AI beta(5)× 事前 4 週外資累積買賣超(3)→ 15 格,
   看 H−L 溢酬是否集中於外資買超格。
2. 中介迴歸:Fama-MacBeth 加入當期/落後外資流,量 beta 係數衰減。
3. 路徑分解:H−L 報酬拆隔夜/盤中(週頻聚合)。
"""
from __future__ import annotations

import numpy as np

from design2_horse_race import fama_macbeth, newey_west_t
from rolling_beta import quintile_assign


def _tercile(x: np.ndarray) -> np.ndarray:
    out = np.full(x.shape, -1, dtype=int)
    ok = ~np.isnan(x)
    if ok.sum() < 3:
        return out
    ranks = x[ok].argsort().argsort()
    out[ok] = np.minimum((ranks * 3) // ok.sum(), 2)
    return out


def double_sort(returns: np.ndarray, betas: np.ndarray, flow: np.ndarray,
                me: np.ndarray, flow_lookback: int = 4) -> dict:
    """5×3 獨立雙重排序。回傳各流組內的 beta H−L(bps/週)與 t 值。"""
    T, _ = returns.shape
    hl_by_flow = np.full((T, 3), np.nan)
    for t in range(flow_lookback + 1, T):
        q = quintile_assign(betas[t - 1])
        cumflow = np.nansum(flow[t - flow_lookback:t], axis=0)
        fq = _tercile(cumflow)
        r = returns[t]
        ok = (q >= 0) & (fq >= 0) & ~np.isnan(r)
        for fg in range(3):
            hi = ok & (q == 4) & (fq == fg)
            lo = ok & (q == 0) & (fq == fg)
            if hi.any() and lo.any():
                hl_by_flow[t, fg] = (np.average(r[hi], weights=me[hi])
                                     - np.average(r[lo], weights=me[lo]))
    out = {}
    for fg, name in enumerate(["F1_sell", "F2_mid", "F3_buy"]):
        m, tt = newey_west_t(hl_by_flow[:, fg])
        out[name] = dict(hl_bps=m * 1e4, t_stat=tt)
    m, tt = newey_west_t(hl_by_flow[:, 2] - hl_by_flow[:, 0])
    out["buy_minus_sell_diff"] = dict(hl_bps=m * 1e4, t_stat=tt)
    return out


def mediation_fm(returns: np.ndarray, betas: np.ndarray, flow: np.ndarray) -> dict:
    """FM:無流量 vs 加入當期+落後 4 週流量,比較 β 溢酬衰減幅度。

    注意:當期流量與當期報酬同時決定(內生),此檢定是描述性的
    「條件化後溢酬還剩多少」,不是因果識別 — handoff §7.5 已認。
    """
    T, N = returns.shape
    base = fama_macbeth(returns, betas)
    lag_flow = np.vstack([np.full((1, N), np.nan), flow[:-1]])
    # fama_macbeth 用 t-1 索引取 controls → 傳 flow 本身即「當期」(t-1+1=t 對不上,
    # 故此處把當期流量前移一列讓索引對齊)
    cur_flow_aligned = np.vstack([flow[1:], np.full((1, N), np.nan)])
    with_flow = fama_macbeth(returns, betas,
                             controls={"flow_t": cur_flow_aligned,
                                       "flow_t1": flow})
    lam0 = base["ai_beta"]["lambda_bps"]
    lam1 = with_flow["ai_beta"]["lambda_bps"]
    return dict(base=base, with_flow=with_flow,
                attenuation_pct=float(100 * (1 - lam1 / lam0)) if lam0 else np.nan)


def path_decomposition_weekly(overnight_w: np.ndarray, intraday_w: np.ndarray,
                              betas: np.ndarray, me: np.ndarray) -> dict:
    """H−L 溢酬的隔夜/盤中通道拆解(週頻)。"""
    from design2_horse_race import vw_quintile_hl
    on = vw_quintile_hl(overnight_w, betas, me)
    intr = vw_quintile_hl(intraday_w, betas, me)
    return dict(overnight=dict(hl_bps=on["hl_bps_per_week"], t=on["t_stat"]),
                intraday=dict(hl_bps=intr["hl_bps_per_week"], t=intr["t_stat"]))

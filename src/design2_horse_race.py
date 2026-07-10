"""Design 2 — 雙因子賽馬(H1 消費因子 vs H2 資本支出因子)。

流程(handoff §3 Design 2):
- 13 週滾動 beta(rolling_beta.py,min 9 週,無前視)
- 每週五分位、價值加權、週頻再平衡、全樣本斷點
- H−L 價差 t 檢定(Newey-West)+ Fama-MacBeth(控制 lnME/lnBM/Mom/Rev 可選)
- 動能糾纏檢查:各分位事前 12 週動能
"""
from __future__ import annotations

import numpy as np

from rolling_beta import quintile_assign, rolling_ai_beta


def newey_west_t(x: np.ndarray, lags: int = 4) -> tuple[float, float]:
    """序列均值的 NW t 值。回傳 (mean, t)。"""
    x = x[~np.isnan(x)]
    n = len(x)
    if n < 10:
        return float("nan"), float("nan")
    e = x - x.mean()
    s = (e @ e) / n
    for L in range(1, lags + 1):
        w = 1 - L / (lags + 1)
        s += 2 * w * (e[L:] @ e[:-L]) / n
    se = np.sqrt(s / n)
    return float(x.mean()), float(x.mean() / se)


def vw_quintile_hl(returns: np.ndarray, betas: np.ndarray, me: np.ndarray,
                   n_groups: int = 5) -> dict:
    """第 t 週用 beta_{t-1} 分組,持有 t 週(無前視)。回傳 H−L 序列與統計。

    returns: (T,N) 週報酬;betas: (T,N) 滾動 beta;me: (N,) 市值。
    """
    T, _ = returns.shape
    hl = np.full(T, np.nan)
    q_rets = np.full((T, n_groups), np.nan)
    for t in range(1, T):
        q = quintile_assign(betas[t - 1])
        if (q >= 0).sum() < 50:
            continue
        r, ok = returns[t], (q >= 0) & ~np.isnan(returns[t])
        for g in range(n_groups):
            m = ok & (q == g)
            if m.any():
                q_rets[t, g] = np.average(r[m], weights=me[m])
        hl[t] = q_rets[t, -1] - q_rets[t, 0]
    mean, tstat = newey_west_t(hl)
    return dict(hl_series=hl, quintile_returns=q_rets,
                hl_bps_per_week=mean * 1e4, t_stat=tstat)


def fama_macbeth(returns: np.ndarray, betas: np.ndarray,
                 controls: dict[str, np.ndarray] | None = None) -> dict:
    """FM 橫斷面迴歸:r_{i,t} = a_t + λ_t β_{i,t-1} + γ_t' X_{i,t-1}。

    controls: name → (T,N) 或 (N,) 陣列。回傳 λ 的均值與 NW t。
    """
    T, _ = returns.shape
    names = ["ai_beta"] + (list(controls) if controls else [])
    lam = np.full((T, len(names)), np.nan)
    for t in range(1, T):
        cols = [betas[t - 1]]
        if controls:
            for c in controls.values():
                cols.append(c[t - 1] if c.ndim == 2 else c)
        X = np.column_stack(cols)
        y = returns[t]
        ok = ~np.isnan(y) & ~np.isnan(X).any(axis=1)
        if ok.sum() < len(names) + 20:
            continue
        Xk = np.column_stack([np.ones(ok.sum()), X[ok]])
        coef, *_ = np.linalg.lstsq(Xk, y[ok], rcond=None)
        lam[t] = coef[1:]
    out = {}
    for j, nm in enumerate(names):
        m, tt = newey_west_t(lam[:, j])
        out[nm] = dict(lambda_bps=m * 1e4, t_stat=tt)
    return out


def momentum_entanglement(returns: np.ndarray, betas: np.ndarray,
                          lookback: int = 12) -> np.ndarray:
    """各分位的事前動能(仿論文 Table 2)。回傳 (5,) 平均事前 12 週累積報酬。"""
    T, _ = returns.shape
    acc = np.zeros(5)
    cnt = np.zeros(5)
    for t in range(lookback, T):
        q = quintile_assign(betas[t])
        mom = np.nansum(returns[t - lookback:t], axis=0)
        for g in range(5):
            m = (q == g) & ~np.isnan(mom)
            if m.any():
                acc[g] += mom[m].mean()
                cnt[g] += 1
    return acc / np.maximum(cnt, 1)


def horse_race(returns: np.ndarray, mkt: np.ndarray, factor_a: np.ndarray,
               factor_b: np.ndarray, me: np.ndarray,
               labels: tuple[str, str] = ("consumption", "capex")) -> dict:
    """兩因子各自完整跑一輪,回傳可比的 H−L 與 FM 結果。"""
    out = {}
    for lbl, f in zip(labels, (factor_a, factor_b)):
        b = rolling_ai_beta(returns, f, mkt)
        sort_res = vw_quintile_hl(returns, b, me)
        fm = fama_macbeth(returns, b)
        mom = momentum_entanglement(returns, b)
        out[lbl] = dict(sort=sort_res, fm=fm, momentum_by_quintile=mom)
    return out

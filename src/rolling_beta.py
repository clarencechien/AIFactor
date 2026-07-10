"""13 週滾動 AI beta(論文 §3 方法;handoff §1.1 第 2 點)。

規格:
- 個股週報酬對 AI factor 的滾動迴歸係數,控制市場超額報酬
- 窗長 13 週、最少 9 週有效觀測
- 無前視:第 t 週的 beta 只用 t-12..t 的資料,用於 t+1 起的排序/事件分組

實作:雙變數迴歸 (factor, market) 以 partialling-out 封閉解向量化,
對 (T, N) 報酬矩陣一次算完,不跑逐窗 OLS。
"""
from __future__ import annotations

import numpy as np


def rolling_ai_beta(
    returns: np.ndarray,      # (T, N) 個股週報酬
    ai_factor: np.ndarray,    # (T,)  AI 因子
    market: np.ndarray,       # (T,)  市場超額報酬
    window: int = 13,
    min_obs: int = 9,
) -> np.ndarray:
    """回傳 (T, N) 的 beta 矩陣;第 t 列 = 用 [t-window+1, t] 窗估的 AI beta。

    缺值(NaN)報酬以 pairwise 有效觀測處理,低於 min_obs 的窗輸出 NaN。
    """
    T, N = returns.shape
    f = ai_factor.reshape(T, 1)
    m = market.reshape(T, 1)
    valid = ~np.isnan(returns)
    r0 = np.where(valid, returns, 0.0)

    out = np.full((T, N), np.nan)
    for t in range(window - 1, T):
        sl = slice(t - window + 1, t + 1)
        v = valid[sl]                      # (w, N)
        n = v.sum(axis=0)                  # 每檔有效週數
        ok = n >= min_obs
        if not ok.any():
            continue
        rw, fw, mw = r0[sl], f[sl], m[sl]
        # 逐檔以其有效觀測 demean(缺值權重 0)
        n_safe = np.maximum(n, 1)
        rbar = rw.sum(axis=0) / n_safe
        fbar = (fw * v).sum(axis=0) / n_safe
        mbar = (mw * v).sum(axis=0) / n_safe
        rd = (rw - rbar) * v
        fd = (fw - fbar) * v
        md = (mw - mbar) * v
        # partial out market: beta = cov(r, f~)/var(f~), f~ = f 對 m 殘差
        Smm = (md * md).sum(axis=0)
        Sfm = (fd * md).sum(axis=0)
        Sff = (fd * fd).sum(axis=0)
        Srf = (rd * fd).sum(axis=0)
        Srm = (rd * md).sum(axis=0)
        with np.errstate(divide="ignore", invalid="ignore"):
            g = Sfm / Smm                          # f 對 m 的斜率
            var_ftilde = Sff - g * Sfm
            cov_rftilde = Srf - g * Srm
            beta = cov_rftilde / var_ftilde
        beta[~ok] = np.nan
        beta[~np.isfinite(beta)] = np.nan
        out[t] = beta
    return out


def quintile_assign(beta_row: np.ndarray, n_groups: int = 5) -> np.ndarray:
    """單週橫斷面五分位(全樣本斷點=當週全體有效 beta)。回傳 0..4,NaN → -1。"""
    out = np.full(beta_row.shape, -1, dtype=int)
    ok = ~np.isnan(beta_row)
    if ok.sum() < n_groups:
        return out
    ranks = beta_row[ok].argsort().argsort()
    out[ok] = np.minimum((ranks * n_groups) // ok.sum(), n_groups - 1)
    return out

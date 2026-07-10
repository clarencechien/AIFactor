"""Design 1 — 前沿模型發布事件研究(handoff §3 Design 1)。

輸入:日頻報酬面板(含 open/close 或已拆好的通道)、事前 AI beta、事件日索引。
量測:T+1 起五日累積異常報酬(市場模型調整)之 H−L 差
      + t 檢定 + block bootstrap
      + 隔夜/盤中通道拆解(論文沒做的加值)
      + 非前沿事件安慰劑。
"""
from __future__ import annotations

import numpy as np


def market_adjust(ret: np.ndarray, mkt: np.ndarray, beta_mkt: np.ndarray | None = None
                  ) -> np.ndarray:
    """市場模型調整:AR = r - beta_m × mkt(beta 未給則用 1)。"""
    if beta_mkt is None:
        return ret - mkt[:, None]
    return ret - mkt[:, None] * beta_mkt[None, :]


def event_hl_car(ar: np.ndarray, pre_beta: np.ndarray, event_days: np.ndarray,
                 horizon: int = 5, tail: float = 0.30) -> dict:
    """每個事件:發布前 beta 分高/低組(前後 tail 分位),T+1..T+horizon CAR 的 H−L。

    ar: (T_days, N) 異常報酬;pre_beta: (N,) 或 (n_events, N) 事前 beta。
    回傳 dict(per_event_hl, mean_hl, t_stat, n_events)。
    """
    hls = []
    for i, ed in enumerate(event_days):
        b = pre_beta[i] if pre_beta.ndim == 2 else pre_beta
        ok = ~np.isnan(b)
        if ok.sum() < 20:
            continue
        lo_cut, hi_cut = np.nanquantile(b, [tail, 1 - tail])
        hi = ok & (b >= hi_cut)
        lo = ok & (b <= lo_cut)
        car = ar[ed: ed + horizon].sum(axis=0)          # 事件日=T+1(已映射)
        hls.append(car[hi].mean() - car[lo].mean())
    hls = np.array(hls)
    t = hls.mean() / (hls.std(ddof=1) / np.sqrt(len(hls))) if len(hls) > 1 else np.nan
    return dict(per_event_hl=hls, mean_hl=float(hls.mean()), t_stat=float(t),
                n_events=int(len(hls)))


def block_bootstrap_pvalue(per_event_hl: np.ndarray, n_boot: int = 5000,
                           seed: int = 42) -> float:
    """事件層級 bootstrap(事件間近似獨立 → 以事件為 block 重抽)雙尾 p 值。"""
    rng = np.random.default_rng(seed)
    n = len(per_event_hl)
    obs = per_event_hl.mean()
    centered = per_event_hl - obs                        # 虛無:均值 0
    idx = rng.integers(0, n, size=(n_boot, n))
    boot_means = centered[idx].mean(axis=1)
    return float((np.abs(boot_means) >= abs(obs)).mean())


def run_design1(ret_total: np.ndarray, overnight: np.ndarray, intraday: np.ndarray,
                mkt: np.ndarray, pre_beta: np.ndarray, event_days: np.ndarray,
                placebo_days: np.ndarray | None = None) -> dict:
    """完整 Design 1:總報酬 + 通道拆解 + 安慰劑。"""
    out = {}
    for name, r in [("total", ret_total), ("overnight", overnight),
                    ("intraday", intraday)]:
        ar = market_adjust(r, mkt * (1.0 if name == "total" else
                                     0.3 if name == "overnight" else 0.7))
        res = event_hl_car(ar, pre_beta, event_days)
        res["boot_p"] = block_bootstrap_pvalue(res["per_event_hl"])
        out[name] = res
    if placebo_days is not None and len(placebo_days):
        ar = market_adjust(ret_total, mkt)
        out["placebo_nonfrontier"] = event_hl_car(ar, pre_beta, placebo_days)
    return out

"""合成台股資料產生器 — 管線驗證與檢定力分析用。

⚠️ 這不是台股。它的唯一用途是:
(a) 驗證 Design 1/2/3 程式在「已知真相」下能正確回收注入結構(power)
(b) 驗證在虛無情境下不產生假陽性(size)
(c) 量化 130 週樣本 + 降級因子對 H1/H2/H3 的檢定力上限

校準參數(量級取自公開常識,非精確估計):
- 個股週報酬波動 ~5%,市場週波動 ~2%,個股 beta ~N(1, 0.3)
- 130 週(2024-01 ~ 2026-06),N=800 檔(近似上市+上櫃流動池)
- 外資流:與當週報酬正相關(價格壓力 + 順勢),自相關 0.3
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np


@dataclass
class SimConfig:
    n_weeks: int = 130
    n_stocks: int = 800
    seed: int = 0
    # 市場結構
    mkt_vol_w: float = 0.02
    idio_vol_w: float = 0.05
    beta_mkt_mean: float = 1.0
    beta_mkt_sd: float = 0.3
    # AI 因子結構
    factor_vol: float = 1.0            # 因子已標準化
    ai_impact: float = 0.01            # 1σ 因子衝擊 × 1σ 曝險 → 1% 週報酬
    # 訊噪校準:13 週滾動 beta 的估計誤差 se ≈ idio_vol/(ai_impact·√12) ≈ 1.44,
    # 真實曝險橫斷面 σ=1 → 估計/真實相關 ≈ 0.57,與論文「收縮修正 ~25%」量級相容。
    # 注入的溢酬:以「完美排序下的 H−L 目標值(bps/週)」參數化;
    # 內部除以 2.8(常態下 E[z|Q5]−E[z|Q1])換算成每 1σ 曝險的價格。
    premium_consumption_bps: float = 0.0
    premium_capex_bps: float = 0.0
    # 因子觀測品質:降級單腿因子 = 真因子 + 觀測噪音
    factor_obs_noise: float = 0.0      # 0=論文級;>0=降級版(方差比例)
    # H3 中介結構
    flow_mediation: float = 0.0        # 0=無;1=溢酬完全集中於外資買超週
    overnight_share: float = 0.5       # 溢酬中經隔夜通道實現的比例
    # 事件研究注入:前沿發布日 T+1..T+5 高低組 CAR 差(%)
    event_hl_car_pct: float = 0.0
    beta_est_corr: float = 0.6         # 事前 beta 估計與真實曝險的相關(估計噪音)
    rng: np.random.Generator = field(init=False, repr=False)

    def __post_init__(self):
        self.rng = np.random.default_rng(self.seed)


def simulate_weekly_panel(cfg: SimConfig) -> dict:
    """產生週頻面板。回傳 dict:
    returns (T,N), mkt (T,), factor_true (T,), factor_obs (T,),
    capex_factor (T,), beta_ai_true (N,), beta_capex_true (N,),
    flow (T,N) 外資買賣超(標準化), me (N,) 市值權重用
    """
    rng = cfg.rng
    T, N = cfg.n_weeks, cfg.n_stocks

    f_cons = rng.standard_normal(T)                    # AI 消費因子(真)
    f_capex = 0.4 * f_cons + np.sqrt(1 - 0.16) * rng.standard_normal(T)  # 與消費相關 0.4
    mkt = rng.standard_normal(T) * cfg.mkt_vol_w + 0.001

    b_mkt = rng.normal(cfg.beta_mkt_mean, cfg.beta_mkt_sd, N)
    b_ai = rng.standard_normal(N)                       # 真實曝險,σ=1
    b_cx = rng.standard_normal(N)

    # 完美排序 H−L 目標 → 每 1σ 曝險價格(2.8 = E[z|Q5]−E[z|Q1],常態)
    lam_c = cfg.premium_consumption_bps / 2.8 / 1e4
    lam_x = cfg.premium_capex_bps / 2.8 / 1e4

    zc = (b_ai - b_ai.mean()) / b_ai.std()
    zx = (b_cx - b_cx.mean()) / b_cx.std()
    mu = lam_c * zc + lam_x * zx                        # (N,)

    eps = rng.standard_normal((T, N)) * cfg.idio_vol_w
    ret = (mkt[:, None] * b_mkt[None, :]
           + f_cons[:, None] * b_ai[None, :] * cfg.ai_impact
           + f_capex[:, None] * b_cx[None, :] * cfg.ai_impact
           + eps)

    # 外資流:與同週報酬相關 + 自相關;H3 中介 = 溢酬只在買超時實現
    flow = np.zeros((T, N))
    innov = rng.standard_normal((T, N))
    for t in range(T):
        prev = flow[t - 1] if t > 0 else 0.0
        flow[t] = 0.3 * prev + 0.5 * (ret[t] / ret.std()) + 0.8 * innov[t]

    if cfg.flow_mediation > 0:
        buy = (flow > 0).astype(float)
        # 溢酬按買超狀態重新分配:買超週承載 (1+m) 倍、賣超週 (1-m) 倍
        med = 1.0 + cfg.flow_mediation * (2 * buy - 1)
        ret += mu[None, :] * med
    else:
        ret += mu[None, :]

    f_obs = f_cons.copy()
    if cfg.factor_obs_noise > 0:
        f_obs = (f_cons + np.sqrt(cfg.factor_obs_noise) * rng.standard_normal(T))
        f_obs /= np.sqrt(1 + cfg.factor_obs_noise)

    me = np.exp(rng.normal(0, 1.2, N))                  # 市值權重(對數常態)
    return dict(returns=ret, mkt=mkt, factor_true=f_cons, factor_obs=f_obs,
                capex_factor=f_capex, beta_ai_true=b_ai, beta_capex_true=b_cx,
                flow=flow, me=me)


def simulate_daily_around_events(cfg: SimConfig, n_events: int = 26,
                                 n_days: int = 650) -> dict:
    """日頻模擬(Design 1 用):含 open/close、事件日效果、隔夜/盤中通道。

    事件效果:高 AI beta 組在事件日 T+1..T+5 相對低組累積 +event_hl_car_pct%,
    其中 overnight_share 比例走隔夜跳空、其餘走盤中。
    """
    rng = cfg.rng
    N = cfg.n_stocks
    b_ai = rng.standard_normal(N)
    zb = (b_ai - b_ai.mean()) / b_ai.std()

    mkt_d = rng.standard_normal(n_days) * cfg.mkt_vol_w / np.sqrt(5)
    b_mkt = rng.normal(cfg.beta_mkt_mean, cfg.beta_mkt_sd, N)
    idio = rng.standard_normal((n_days, N)) * cfg.idio_vol_w / np.sqrt(5)
    ret_total = mkt_d[:, None] * b_mkt[None, :] + idio

    # 均勻散佈事件日(避開頭尾 30 天),注入 5 日效果
    event_days = np.linspace(30, n_days - 35, n_events).astype(int)
    daily_eff = (cfg.event_hl_car_pct / 100.0) / 5.0
    for ed in event_days:
        for k in range(5):
            ret_total[ed + k] += daily_eff * zb  # 對 beta 線性,H−L(前後30%)≈ 注入值×E[z|尾部]差

    # 拆通道:overnight = share × total(事件部分), 平時隔夜約 30% 波動
    on_base = 0.3 * ret_total + rng.standard_normal((n_days, N)) * 0.002
    overnight = on_base.copy()
    for ed in event_days:
        for k in range(5):
            overnight[ed + k] += daily_eff * zb * (cfg.overnight_share - 0.3)
    intraday = (1 + ret_total) / (1 + overnight) - 1

    close = 100 * np.cumprod(1 + ret_total, axis=0)
    prev_close = np.vstack([np.full((1, N), 100.0), close[:-1]])
    open_ = prev_close * (1 + overnight)

    # 事前 beta 估計 = 真實曝險 + 估計噪音(相關 = beta_est_corr)
    c = cfg.beta_est_corr
    beta_est = c * zb + np.sqrt(1 - c * c) * rng.standard_normal(N)

    return dict(ret_total=ret_total, overnight=overnight, intraday=intraday,
                open=open_, close=close, mkt=mkt_d, beta_ai_true=b_ai,
                beta_est=beta_est, event_days=event_days, zb=zb)

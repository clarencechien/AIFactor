"""因子建構(handoff Design 2)。

消費因子(降級版,誠實標註):
- 論文 = token/美元/用戶三腿週頻 log 成長之 PC1(權重 0.665/0.559/0.496,解釋 56.5%)
- 我們只有 OpenRouter 公開排行的 token 量單腿 → factor = token 週 log 成長標準化
- 品質差異已寫入 FACTS.md:H1 檢定力天生偏弱,解讀不得誇大

資本支出因子(自建):
- 成分 A:四大 hyperscaler capex guidance 修正,季頻線性內插到週頻(粗糙,標註)
- 成分 B:SOX 週報酬對 S&P 500 迴歸殘差(供給端純化)
- 因子 = 兩成分 z-score 等權;穩健性另跑 PC1
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def consumption_factor_single_leg(tokens_weekly: pd.Series) -> pd.Series:
    """token 量單腿:log 成長 → z-score。index=週五日期。"""
    g = np.log(tokens_weekly).diff().dropna()
    return ((g - g.mean()) / g.std()).rename("ai_consumption")


def pc1(df: pd.DataFrame) -> tuple[pd.Series, np.ndarray, float]:
    """第一主成分(供未來拿到三腿資料時用;回傳 PC1、權重、解釋比例)。"""
    x = (df - df.mean()) / df.std()
    cov = np.cov(x.T.values)
    w_, v_ = np.linalg.eigh(cov)
    w1 = v_[:, -1]
    if w1.sum() < 0:  # 符號規約:成長為正
        w1 = -w1
    pc = pd.Series(x.values @ w1, index=df.index, name="pc1")
    return pc, w1, float(w_[-1] / w_.sum())


def sox_residual(sox_ret_w: pd.Series, spx_ret_w: pd.Series) -> pd.Series:
    """SOX 週報酬對 S&P 500 全樣本迴歸殘差(供給端純化)。"""
    df = pd.concat([sox_ret_w, spx_ret_w], axis=1, keys=["sox", "spx"]).dropna()
    x = np.column_stack([np.ones(len(df)), df["spx"].values])
    coef, *_ = np.linalg.lstsq(x, df["sox"].values, rcond=None)
    resid = df["sox"].values - x @ coef
    return pd.Series(resid, index=df.index, name="sox_resid")


def capex_factor(capex_guidance_w: pd.Series, sox_resid_w: pd.Series,
                 method: str = "equal") -> pd.Series:
    """z-score 等權(method='equal')或 PC1(method='pc1')。"""
    df = pd.concat([capex_guidance_w, sox_resid_w], axis=1).dropna()
    z = (df - df.mean()) / df.std()
    if method == "pc1":
        f, _, _ = pc1(z)
        return f.rename("ai_capex")
    return z.mean(axis=1).rename("ai_capex")


def interpolate_quarterly_to_weekly(q: pd.Series, weeks: pd.DatetimeIndex) -> pd.Series:
    """季頻 guidance 修正 → 週頻線性內插(粗糙;FACTS 已標註)。"""
    return q.reindex(q.index.union(weeks)).interpolate(method="time").reindex(weeks)

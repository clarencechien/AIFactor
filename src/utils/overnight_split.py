"""日報酬拆解:隔夜跳空 vs 盤中(handoff Design 1 步驟 5 / Design 3 路徑分解)。

overnight_t = open_t / close_{t-1} - 1   (ADR/美股夜盤傳導通道)
intraday_t  = close_t / open_t - 1       (本地盤中定價通道)
(1+overnight)(1+intraday) = 1 + total_return
"""
from __future__ import annotations

import pandas as pd


def split_overnight_intraday(px: pd.DataFrame) -> pd.DataFrame:
    """px: MultiIndex(date, stock) 或含 [date, stock, open, close] 欄位的長表。

    回傳同索引長表,欄位 = [ret_total, ret_overnight, ret_intraday]。
    """
    df = px.sort_values(["stock", "date"]).copy()
    g = df.groupby("stock", sort=False)
    prev_close = g["close"].shift(1)
    df["ret_overnight"] = df["open"] / prev_close - 1.0
    df["ret_intraday"] = df["close"] / df["open"] - 1.0
    df["ret_total"] = df["close"] / prev_close - 1.0
    return df.dropna(subset=["ret_total"])


def check_identity(df: pd.DataFrame, tol: float = 1e-10) -> bool:
    """(1+o)(1+i) == 1+r 的恆等式檢查,防止 open/close 欄位錯置。"""
    lhs = (1 + df["ret_overnight"]) * (1 + df["ret_intraday"]) - 1
    return bool(((lhs - df["ret_total"]).abs() < tol).all())

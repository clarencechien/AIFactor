"""上市(TWSE)備援價量:Yahoo Finance chart JSON(<code>.TW)→ 與面板同欄位的長表。

為什麼存在:2026-11-08 複跑時 www.twse.com.tw 對本執行環境回「因為安全性考量…」封鎖頁
(非限流,是 WAF 阻擋),官方 MI_INDEX/T86 只抓到 2026-07~08 間 17 個交易日。
上市個股 2026-07-10 之後的缺日改用 Yahoo;上櫃(TPEx)仍全部官方。

品質控制:
- 與官方面板重疊期(2025-11 ~ 2026-07)逐筆核對收盤價,輸出相對差中位數/最大值與完全相符比例。
- Yahoo 無外資買賣超 → foreign_net_sh = NaN(Design 3 在該期間只剩上櫃樣本);無成交金額。
- 收盤為未還原價(與官方一致);Yahoo 的 adjclose 不使用。
"""
from __future__ import annotations

import json
import pathlib

import numpy as np
import pandas as pd


def load_yahoo_dir(d: pathlib.Path) -> pd.DataFrame:
    rows = []
    for fp in sorted(d.glob("*.json")):
        try:
            j = json.loads(fp.read_text())
        except json.JSONDecodeError:
            continue
        res = (j.get("chart") or {}).get("result")
        if not res:
            continue
        r = res[0]
        ts = r.get("timestamp")
        q = (r.get("indicators") or {}).get("quote", [{}])[0]
        if not ts or not q:
            continue
        tz = r["meta"].get("exchangeTimezoneName", "Asia/Taipei")
        idx = (pd.to_datetime(ts, unit="s", utc=True).tz_convert(tz)
               .normalize().tz_localize(None))
        df = pd.DataFrame({"date": idx, "open": q.get("open"), "close": q.get("close"),
                           "volume": q.get("volume")})
        df["stock"] = fp.stem
        rows.append(df)
    out = pd.concat(rows, ignore_index=True)
    out = out.dropna(subset=["close"]).drop_duplicates(["date", "stock"], keep="last")
    return out


def validate_against(official: pd.DataFrame, yahoo: pd.DataFrame) -> dict:
    """official: 面板 (date, stock, close);回傳重疊期核對統計。"""
    m = official.merge(yahoo, on=["date", "stock"], suffixes=("_off", "_yh"))
    rel = (m["close_yh"] - m["close_off"]).abs() / m["close_off"]
    return dict(n_overlap=int(len(m)), exact_share=float((rel < 1e-6).mean()),
                rel_median=float(rel.median()), rel_p99=float(rel.quantile(0.99)),
                rel_max=float(rel.max()),
                n_bad_gt_1pct=int((rel > 0.01).sum()))

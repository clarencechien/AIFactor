"""美國模型發布時間 → 台股事件交易日 (T+1) 映射。

規則(handoff Design 1 步驟 2):
- 美國公司(Anthropic/OpenAI/Google/Meta)發布多在美東白天,對應台北已是深夜/隔日
  → 台股第一個可反應時點 = 發布日 (UTC) 的下一個台股交易日。
- DeepSeek(中國,UTC+8)發布若在台股盤前(<09:00 台北)則當日即 T+1,否則下一交易日。
  本版簡化:一律用「下一個台股交易日」,DeepSeek 例外留待有盤中時間戳時處理(旗標)。

⚠️ 假日表為知識庫近似值(APPROXIMATE),正式跑真實資料前必須以
TWSE 官方行事曆 (https://www.twse.com.tw/rwd/zh/holidaySchedule/holidaySchedule) 覆核。
"""
from __future__ import annotations

import datetime as dt

CALENDAR_STATUS = "APPROXIMATE_KB"  # 供 FACTS 帳本引用

# TWSE 休市日(不含週末),知識庫近似
TWSE_HOLIDAYS: set[dt.date] = {
    # 2024
    *[dt.date(2024, 1, 1)],
    *[dt.date(2024, 2, d) for d in (6, 7, 8, 9, 12, 13, 14)],  # 春節前後(含彈性休市)
    dt.date(2024, 2, 28), dt.date(2024, 4, 4), dt.date(2024, 4, 5),
    dt.date(2024, 5, 1), dt.date(2024, 6, 10), dt.date(2024, 9, 17),
    dt.date(2024, 10, 10),
    # 2025
    dt.date(2025, 1, 1),
    *[dt.date(2025, 1, d) for d in (23, 24, 27, 28, 29, 30, 31)],  # 春節
    dt.date(2025, 2, 28), dt.date(2025, 4, 3), dt.date(2025, 4, 4),
    dt.date(2025, 5, 1), dt.date(2025, 5, 30), dt.date(2025, 10, 6),
    dt.date(2025, 10, 10), dt.date(2025, 10, 24),
    # 2026(近似,春節 2/17)
    dt.date(2026, 1, 1), dt.date(2026, 1, 2),
    *[dt.date(2026, 2, d) for d in (13, 16, 17, 18, 19, 20)],
    dt.date(2026, 2, 27), dt.date(2026, 4, 3), dt.date(2026, 4, 6),
    dt.date(2026, 5, 1), dt.date(2026, 6, 19), dt.date(2026, 9, 25),
    dt.date(2026, 10, 9),
}


def is_twse_trading_day(d: dt.date) -> bool:
    return d.weekday() < 5 and d not in TWSE_HOLIDAYS


def next_twse_trading_day(d: dt.date) -> dt.date:
    """d 之後(不含 d)的第一個台股交易日。"""
    cur = d + dt.timedelta(days=1)
    while not is_twse_trading_day(cur):
        cur += dt.timedelta(days=1)
    return cur


def event_day_tw(release_date_utc: dt.date, provider: str = "") -> dt.date:
    """發布日 (UTC) → 台股事件日 T+1。

    美系實驗室:美東發布時台北已收盤 → 下一交易日。
    DeepSeek:無盤中時間戳時同樣取下一交易日(保守;見模組 docstring)。
    """
    return next_twse_trading_day(release_date_utc)


def trading_days_between(start: dt.date, end: dt.date) -> list[dt.date]:
    out, cur = [], start
    while cur <= end:
        if is_twse_trading_day(cur):
            out.append(cur)
        cur += dt.timedelta(days=1)
    return out

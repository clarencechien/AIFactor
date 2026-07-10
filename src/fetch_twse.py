"""TWSE 上市資料抓取:日價量 + 三大法人買賣超。

⚠️ 2026-07-10:本 Claude Code 環境的網路政策封鎖 openapi.twse.com.tw / www.twse.com.tw
(CONNECT 403),此腳本在本環境不可執行,已於 FACTS.md §0 記錄。
程式為可重跑交付,在開放網路環境直接 `python fetch_twse.py --start 2024-01-01` 即可。

資料端點:
- 日收盤(全市場單日):https://www.twse.com.tw/rwd/zh/afterTrading/MI_INDEX?date=YYYYMMDD&type=ALLBUT0999&response=json
- 三大法人個股買賣超:https://www.twse.com.tw/rwd/zh/fund/T86?date=YYYYMMDD&selectType=ALLBUT0999&response=json
還原權息:TWSE 原始價未還原;正式因子計算前須用除權息表調整(TODO,或以 FinMind 備援)。
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import sys
import time
import urllib.request

BASE_PRICE = ("https://www.twse.com.tw/rwd/zh/afterTrading/MI_INDEX"
              "?date={d}&type=ALLBUT0999&response=json")
BASE_T86 = ("https://www.twse.com.tw/rwd/zh/fund/T86"
            "?date={d}&selectType=ALLBUT0999&response=json")
OUT_DIR = pathlib.Path(__file__).resolve().parent.parent / "data" / "twse_raw"


def fetch_day(date: dt.date, kind: str = "price", pause: float = 3.0) -> dict | None:
    url = (BASE_PRICE if kind == "price" else BASE_T86).format(d=date.strftime("%Y%m%d"))
    req = urllib.request.Request(url, headers={"User-Agent": "ai-premium-tw/0.1"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            payload = json.loads(r.read())
    except Exception as e:  # noqa: BLE001 — 記錄後跳過,由 resume 邏輯補
        print(f"[WARN] {date} {kind}: {e}", file=sys.stderr)
        return None
    time.sleep(pause)  # TWSE 有速率限制,禮貌性間隔
    return payload if payload.get("stat") == "OK" else None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2024-01-01")
    ap.add_argument("--end", default=dt.date.today().isoformat())
    ap.add_argument("--kind", choices=["price", "t86", "both"], default="both")
    ap.add_argument("--pause", type=float, default=3.0)
    args = ap.parse_args()

    sys.path.insert(0, str(pathlib.Path(__file__).parent))
    from utils.tz_map import trading_days_between

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    days = trading_days_between(dt.date.fromisoformat(args.start),
                                dt.date.fromisoformat(args.end))
    kinds = ["price", "t86"] if args.kind == "both" else [args.kind]
    n_ok = 0
    for d in days:
        for k in kinds:
            fp = OUT_DIR / f"{k}_{d.isoformat()}.json"
            if fp.exists():
                continue
            data = fetch_day(d, k, pause=args.pause)
            if data:
                fp.write_text(json.dumps(data, ensure_ascii=False))
                n_ok += 1
    print(f"fetched {n_ok} files → {OUT_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

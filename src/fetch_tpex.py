"""TPEx 上櫃資料抓取:日價量 + 三大法人買賣超。

⚠️ 本環境網路封鎖(見 FACTS.md §0),交付供開放環境重跑。

端點(TPEx OpenAPI / 舊制 JSON):
- 日收盤:https://www.tpex.org.tw/www/zh-tw/afterTrading/otc?date=YYYY/MM/DD&type=EW&response=json
- 三大法人:https://www.tpex.org.tw/www/zh-tw/insti/dailyTrade?type=Daily&date=YYYY/MM/DD&response=json
(TPEx 端點歷經改版,執行時若 404 請對照 https://www.tpex.org.tw/openapi/ 更新路徑)
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import sys
import time
import urllib.request

BASE_PRICE = ("https://www.tpex.org.tw/www/zh-tw/afterTrading/otc"
              "?date={d}&type=EW&response=json")
BASE_INST = ("https://www.tpex.org.tw/www/zh-tw/insti/dailyTrade"
             "?type=Daily&date={d}&response=json")
OUT_DIR = pathlib.Path(__file__).resolve().parent.parent / "data" / "tpex_raw"


def fetch_day(date: dt.date, kind: str, pause: float = 3.0) -> dict | None:
    d = date.strftime("%Y/%m/%d")
    url = (BASE_PRICE if kind == "price" else BASE_INST).format(d=d)
    req = urllib.request.Request(url, headers={"User-Agent": "ai-premium-tw/0.1"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            payload = json.loads(r.read())
    except Exception as e:  # noqa: BLE001
        print(f"[WARN] {date} {kind}: {e}", file=sys.stderr)
        return None
    time.sleep(pause)
    return payload


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2024-01-01")
    ap.add_argument("--end", default=dt.date.today().isoformat())
    ap.add_argument("--kind", choices=["price", "inst", "both"], default="both")
    ap.add_argument("--pause", type=float, default=3.0)
    args = ap.parse_args()

    sys.path.insert(0, str(pathlib.Path(__file__).parent))
    from utils.tz_map import trading_days_between

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    days = trading_days_between(dt.date.fromisoformat(args.start),
                                dt.date.fromisoformat(args.end))
    n_ok = 0
    kinds = ["price", "inst"] if args.kind == "both" else [args.kind]
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

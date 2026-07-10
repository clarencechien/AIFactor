"""OpenRouter 公開排行 token 量 — Wayback Machine 週頻回補(Design 2 降級消費因子)。

⚠️ 本環境網路封鎖 archive.org 與 openrouter.ai(見 FACTS.md §0),交付供開放環境重跑。

方法(handoff Design 2):
1. 對每個目標週五,查 Wayback availability API 找最近快照:
   http://archive.org/wayback/available?url=openrouter.ai/rankings&timestamp=YYYYMMDD
2. 抓快照 HTML,解析各模型 token 量(頁面為 Next.js,資料在 __NEXT_DATA__ JSON 內;
   版面歷經改版,解析器需按快照時期分支 — 先存原始 HTML,解析與抓取分離)。
3. 輸出 data/openrouter_weekly.csv:week_friday, total_tokens, n_models, snapshot_url。

品質旗標:只有 token 量單腿;快照缺週用 NaN,不內插(因子端處理)。
前例:Demirer et al. (2025) 以爬取的 OpenRouter 公開資料做 LLM 定價研究。
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import sys
import time
import urllib.request

AVAIL = "http://archive.org/wayback/available?url=openrouter.ai/rankings&timestamp={ts}"
OUT_DIR = pathlib.Path(__file__).resolve().parent.parent / "data" / "openrouter_snapshots"


def fridays(start: dt.date, end: dt.date) -> list[dt.date]:
    d = start + dt.timedelta(days=(4 - start.weekday()) % 7)
    out = []
    while d <= end:
        out.append(d)
        d += dt.timedelta(days=7)
    return out


def fetch_snapshot_url(day: dt.date) -> str | None:
    url = AVAIL.format(ts=day.strftime("%Y%m%d"))
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            j = json.loads(r.read())
        snap = j.get("archived_snapshots", {}).get("closest", {})
        return snap.get("url") if snap.get("available") else None
    except Exception as e:  # noqa: BLE001
        print(f"[WARN] avail {day}: {e}", file=sys.stderr)
        return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2024-01-01")
    ap.add_argument("--end", default=dt.date.today().isoformat())
    args = ap.parse_args()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    n_ok = 0
    for f in fridays(dt.date.fromisoformat(args.start), dt.date.fromisoformat(args.end)):
        fp = OUT_DIR / f"rankings_{f.isoformat()}.html"
        if fp.exists():
            continue
        snap = fetch_snapshot_url(f)
        if not snap:
            continue
        try:
            with urllib.request.urlopen(snap, timeout=60) as r:
                fp.write_bytes(r.read())
            n_ok += 1
        except Exception as e:  # noqa: BLE001
            print(f"[WARN] fetch {f}: {e}", file=sys.stderr)
        time.sleep(2)  # archive.org 禮貌間隔
    print(f"saved {n_ok} snapshots → {OUT_DIR}(解析另行執行,先存原始檔)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""降級版 AI 消費因子:OpenRouter rankings 頁的 Wayback 快照 → 週頻 token 總量。

方法(2026-07-10 定版):
- rankings 頁的 Next.js flight payload 被切成多個 `self.__next_f.push` chunk,
  先重組完整 payload 再解析。
- 頁面內嵌多張圖表(token、美元、請求數等);**token 圖 = 週頻(週一索引)、
  點數 ≥ 40、量級最大者**。2025-01 之前的版式只有請求數圖 → token 序列只能
  從 2024-03-04 起(20250303 快照的尾隨一年圖),2024 年 1–2 月缺頭(FACTS 旗標)。
- 縫合:同週多快照取最新;各快照最後一週未完丟棄;重疊差異輸出品質檢查。

輸出:data/openrouter_weekly.csv(week_monday, total_tokens, snapshot_src)
"""
from __future__ import annotations

import json
import pathlib
import re
import sys
import time
import urllib.request

import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
SNAP_DIR = ROOT / "data" / "openrouter_snapshots"
UA = {"User-Agent": "Mozilla/5.0 ai-premium-tw research"}

TARGET_TS = ["20250303", "20260302", "20260401", "20260501"]


def closest_snapshot(ts: str) -> str | None:
    url = (f"https://archive.org/wayback/available?"
           f"url=openrouter.ai/rankings&timestamp={ts}")
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        j = json.loads(r.read())
    s = j.get("archived_snapshots", {}).get("closest", {})
    return s.get("url") if s.get("available") else None


def flight_text(html: str) -> str:
    parts = re.findall(r'self\.__next_f\.push\(\[1,"((?:[^"\\]|\\.)*)"\]\)', html)
    return "".join(parts).encode().decode("unicode_escape", errors="ignore")


def all_charts(txt: str) -> list[list[dict]]:
    out = []
    for m in re.finditer(r'"data":(\[\{"x":"20\d\d-\d\d-\d\d")', txt):
        start = m.start(1)
        depth, end = 0, None
        for i in range(start, min(start + 2_000_000, len(txt))):
            depth += txt[i] == "["
            depth -= txt[i] == "]"
            if depth == 0:
                end = i + 1
                break
        if end:
            try:
                out.append(json.loads(txt[start:end]))
            except json.JSONDecodeError:
                pass
    return out


def token_chart(html: str) -> pd.DataFrame | None:
    """挑 token 圖:週頻(間隔 7 天)、≥40 點、中位總量最大。"""
    charts = all_charts(flight_text(html))
    best, best_mid = None, -1.0
    for arr in charts:
        if len(arr) < 40:
            continue
        xs = pd.to_datetime([p["x"] for p in arr])
        if (xs.to_series().diff().dropna().dt.days != 7).any():
            continue
        tot = [sum(v for v in p["ys"].values() if isinstance(v, (int, float)))
               for p in arr]
        mid = sorted(tot)[len(tot) // 2]
        if mid > best_mid:
            best_mid = mid
            best = pd.DataFrame({"week_monday": xs, "total_tokens": tot})
    return best


def main() -> int:
    SNAP_DIR.mkdir(parents=True, exist_ok=True)
    frames = []
    for ts in TARGET_TS:
        fp = SNAP_DIR / f"rankings_{ts}.html"
        if not fp.exists():
            url = closest_snapshot(ts)
            if not url:
                print(f"[WARN] no snapshot near {ts}", file=sys.stderr)
                continue
            m = re.search(r"/web/(\d{14})", url)
            url = f"https://web.archive.org/web/{m.group(1)}if_/https://openrouter.ai/rankings"
            print(f"fetch {ts} <- {url}")
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=120) as r:
                fp.write_bytes(r.read())
            time.sleep(2)
        df = token_chart(fp.read_text(encoding="utf-8", errors="ignore"))
        if df is None:
            print(f"[WARN] no token chart in {ts}", file=sys.stderr)
            continue
        df = df.sort_values("week_monday").iloc[:-1]     # 快照當週未完
        df["snapshot_src"] = ts
        frames.append(df)
        print(f"{ts}: {len(df)} wk {df.week_monday.min().date()} -> "
              f"{df.week_monday.max().date()}, median {df.total_tokens.median():.2e}")

    allw = pd.concat(frames, ignore_index=True)
    piv = allw.pivot_table(index="week_monday", columns="snapshot_src",
                           values="total_tokens")
    ov = piv.dropna(thresh=2)
    if len(ov):
        rel = ((ov.max(axis=1) - ov.min(axis=1)) / ov.max(axis=1))
        print(f"overlap weeks: {len(ov)}, rel diff median {rel.median():.4f} "
              f"max {rel.max():.4f}")
    out = (allw.sort_values("snapshot_src").groupby("week_monday").last()
           .reset_index()[["week_monday", "total_tokens", "snapshot_src"]])
    out.to_csv(ROOT / "data" / "openrouter_weekly.csv", index=False)
    print(f"saved {len(out)} weeks -> data/openrouter_weekly.csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

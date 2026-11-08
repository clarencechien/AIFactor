"""Tiny SVG chart helpers for the imitator chassis: 640-wide viewBox, font-size 12 via classes,
series colours var(--c1..c6) in order, hairline solid gridlines, bars <=24px rx4, lines 2px, dots r>=4."""
from __future__ import annotations
import math

W = 640
def _nice_ticks(lo, hi, n=4):
    span = hi - lo
    if span == 0: span = abs(hi) or 1
    raw = span / n
    mag = 10 ** math.floor(math.log10(raw))
    for m in (1, 2, 2.5, 5, 10):
        step = m * mag
        if raw <= step: break
    t0 = math.floor(lo / step) * step
    ticks = []
    t = t0
    while t <= hi + 1e-9:
        ticks.append(round(t, 10)); t += step
    return ticks

def fmt(v, unit=""):
    if abs(v) >= 100 or float(v).is_integer(): s = f"{v:,.0f}"
    elif abs(v) >= 10: s = f"{v:.1f}"
    else: s = f"{v:.2f}".rstrip("0").rstrip(".")
    return s + unit

def grouped_bars(groups, series, values, *, unit="", aria="", height=300, zero_line=True,
                 ml=48, mr=16, mt=16, mb=44, label_ext=None, ylabel=None):
    """groups: x categories; series: names; values[s][g]."""
    n_g, n_s = len(groups), len(series)
    pw, ph = W - ml - mr, height - mt - mb
    allv = [v for row in values for v in row if v is not None]
    lo, hi = min(0, min(allv)), max(0, max(allv))
    ticks = _nice_ticks(lo, hi)
    lo, hi = min(lo, ticks[0]), max(hi, ticks[-1])
    y = lambda v: mt + ph - (v - lo) / (hi - lo) * ph
    out = [f'<svg viewBox="0 0 {W} {height}" role="img" aria-label="{aria}">']
    for t in ticks:
        out.append(f'<line class="grid" x1="{ml}" y1="{y(t):.1f}" x2="{W-mr}" y2="{y(t):.1f}"/>')
        out.append(f'<text class="axis" x="{ml-8}" y="{y(t)+4:.1f}" text-anchor="end">{fmt(t, unit)}</text>')
    if zero_line and lo < 0 < hi:
        out.append(f'<line class="grid" x1="{ml}" y1="{y(0):.1f}" x2="{W-mr}" y2="{y(0):.1f}" style="stroke:var(--rule-hard)"/>')
    gw = pw / n_g
    bw = min(24, (gw * 0.7) / n_s)
    for gi, g in enumerate(groups):
        x0 = ml + gi * gw + (gw - bw * n_s) / 2
        for si in range(n_s):
            v = values[si][gi]
            if v is None: continue
            top, bot = y(max(v, 0)), y(min(v, 0))
            h = max(bot - top, 1)
            out.append(f'<rect class="bar" x="{x0 + si*bw:.1f}" y="{top:.1f}" width="{bw-2:.1f}" height="{h:.1f}" fill="var(--c{si+1})"/>')
            if label_ext and (si, gi) in label_ext:
                ly = top - 6 if v >= 0 else bot + 14
                out.append(f'<text class="label" x="{x0 + si*bw + (bw-2)/2:.1f}" y="{ly:.1f}" text-anchor="middle">{label_ext[(si,gi)]}</text>')
        out.append(f'<text class="axis" x="{ml + gi*gw + gw/2:.1f}" y="{height-mb+18}" text-anchor="middle">{g}</text>')
    if ylabel:
        out.append(f'<text class="axis" x="{ml}" y="{mt-4}" text-anchor="start">{ylabel}</text>')
    out.append('</svg>')
    return "\n".join(out)

def lines(xlabels, series, values, *, unit="", aria="", height=300, ml=52, mr=16, mt=16, mb=44,
          xtick_every=None, endpoint_labels=True, log=False, ylabel=None, yticks=None, extra_marks=None, end_values=None):
    """values[s] list of y (None allowed). xlabels shared."""
    n = len(xlabels)
    pw, ph = W - ml - mr, height - mt - mb
    allv = [v for row in values for v in row if v is not None]
    tf = (lambda v: math.log10(v)) if log else (lambda v: v)
    lo, hi = min(allv), max(allv)
    if yticks is None:
        if log:
            e0, e1 = math.floor(math.log10(lo)), math.ceil(math.log10(hi))
            yticks = [10 ** e for e in range(e0, e1 + 1)]
        else:
            yticks = _nice_ticks(min(0, lo) if lo > 0 and lo < hi * 0.3 else lo, hi)
    tlo, thi = min(tf(yticks[0]), tf(lo)), max(tf(yticks[-1]), tf(hi))
    y = lambda v: mt + ph - (tf(v) - tlo) / (thi - tlo) * ph
    x = lambda i: ml + i / max(n - 1, 1) * pw
    out = [f'<svg viewBox="0 0 {W} {height}" role="img" aria-label="{aria}">']
    for t in yticks:
        out.append(f'<line class="grid" x1="{ml}" y1="{y(t):.1f}" x2="{W-mr}" y2="{y(t):.1f}"/>')
        out.append(f'<text class="axis" x="{ml-8}" y="{y(t)+4:.1f}" text-anchor="end">{fmt(t, unit)}</text>')
    step = xtick_every or max(1, n // 6)
    for i in range(0, n, step):
        out.append(f'<text class="axis" x="{x(i):.1f}" y="{height-mb+18}" text-anchor="middle">{xlabels[i]}</text>')
    if extra_marks:
        for k, (i, text) in enumerate(extra_marks):
            xi = x(i)
            out.append(f'<line class="grid" x1="{xi:.1f}" y1="{mt}" x2="{xi:.1f}" y2="{mt+ph}" style="stroke:var(--rule-hard)"/>')
            right = xi > ml + pw * 0.6
            out.append(f'<text class="label" x="{xi + (-6 if right else 6):.1f}" y="{mt + 12 + 16*k}" text-anchor="{"end" if right else "start"}">{text}</text>')
    for si, row in enumerate(values):
        pts = [(x(i), y(v)) for i, v in enumerate(row) if v is not None]
        d = " ".join(("M" if k == 0 else "L") + f"{px:.1f} {py:.1f}" for k, (px, py) in enumerate(pts))
        out.append(f'<path class="line" d="{d}" stroke="var(--c{si+1})"/>')
        if endpoint_labels and pts:
            px, py = pts[-1]
            out.append(f'<circle class="dot" cx="{px:.1f}" cy="{py:.1f}" r="4.5" fill="var(--c{si+1})"/>')
            if end_values:
                out.append(f'<text class="label" x="{px - 8:.1f}" y="{py - 8 - 14*si:.1f}" text-anchor="end">{end_values[si]}</text>')
    if ylabel:
        out.append(f'<text class="axis" x="{ml}" y="{mt-4}" text-anchor="start">{ylabel}</text>')
    out.append('</svg>')
    return "\n".join(out)

def datatable(headers, rows, summary="資料表", num_cols=None):
    num_cols = set(num_cols or range(1, len(headers)))
    h = "".join(f'<th{" class=\"num\"" if i in num_cols else ""}>{c}</th>' for i, c in enumerate(headers))
    body = []
    for r in rows:
        body.append("<tr>" + "".join(f'<td{" class=\"num\"" if i in num_cols else ""}>{c}</td>' for i, c in enumerate(r)) + "</tr>")
    return (f'<details class="datatable"><summary>{summary}</summary><div class="table-scroll plain">'
            f'<table><thead><tr>{h}</tr></thead><tbody>{"".join(body)}</tbody></table></div></details>')

# -*- coding: utf-8 -*-
"""Build reports/ai_premium_tw_report_2026-11.html from results JSON + data CSVs (imitator v3)."""
from __future__ import annotations
import json, sys, pathlib, math
import numpy as np, pandas as pd
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from svgchart import grouped_bars, lines, datatable, fmt

ROOT = pathlib.Path(__file__).resolve().parent.parent
SCR = pathlib.Path(__file__).resolve().parent  # imitator/report.css 需放在 scripts/imitator/
R = json.load(open(ROOT / 'reports/real_results_2026-11.json'))
J = json.load(open(ROOT / 'reports/real_results.json'))
CSS = open(SCR / 'imitator/report.css', encoding='utf-8').read()
assert 'imitator report chassis' in CSS

def b(x, d=1):  # bps formatting with sign
    return f"{x:+.{d}f}"
def pct(x, d=1):
    return f"{x:+.{d}f}%"
def t_(x):
    return f"{x:.2f}"
def nz(x, f='{:+.1f}'):
    return '—' if x is None or (isinstance(x, float) and math.isnan(x)) else f.format(x)

# ---------- numbers ----------
R2c, R2s = R['R2_horse_race']['consumption_openrouter'], R['R2_horse_race']['supply_sox_residual']
J2c, J2s = J['R2_horse_race']['consumption_openrouter'], J['R2_horse_race']['supply_sox_residual']
R4 = R['R4_subperiods_and_cooling']; C4, S4 = R4['consumption'], R4['supply']
MK, TS, OR = R4['market_context'], R4['tsmc_2330'], R4['openrouter_tokens']
R1 = R['R1_design1_paper_calendar_consbeta']; J1 = J['R1_design1_event_study_consbeta']
R1c = R['R1c_design1_extended_calendar_consbeta']
R3 = R['R3_design3_flow_mediation_consbeta']; J3 = J['R3_design3_flow_mediation_consbeta']
meta = R['_meta']; weeks0, weeks1, nweeks = meta['weeks']
R2c_n_stocks = f"{pd.read_parquet(ROOT / 'data/processed/twse_daily.parquet', columns=['stock'])['stock'].nunique():,}"
crash_wk = next(iter(R4['weeks_after_factor_end'])) if R4['weeks_after_factor_end'] else None
CR = R4['weeks_after_factor_end'].get(crash_wk) if crash_wk else None

sox_dd = MK['sox_drawdown_from_peak_pct']; twii_dd = MK['twii_drawdown_from_peak_pct']
sox_0709 = 100 * (MK['sox']['2026-11-06'] / MK['sox']['2026-07-09'] - 1)
twii_0709 = 100 * (MK['twii']['2026-11-06'] / MK['twii']['2026-07-09'] - 1)
spx_0709 = 100 * (MK['spx']['2026-11-06'] / MK['spx']['2026-07-09'] - 1)
twii_peak_to_now = 100 * (MK['twii']['2026-11-06'] / MK['twii']['twii_peak_2026-10-06'] - 1)
sox_peak_to_now = 100 * (MK['sox']['2026-11-06'] / MK['sox']['sox_peak_2026-06-22'] - 1)
tok_x_since_apr = OR['growth_since_2026_04_20_x']; tok_yoy = OR['growth_yoy_x']
g = OR['mean_weekly_log_growth']
wk_pct = lambda lg: 100 * math.expm1(lg)

# ---------- chart 1: tokens ----------
orw = pd.read_csv(ROOT / 'data/openrouter_weekly.csv', parse_dates=['week_monday']).set_index('week_monday')['total_tokens'] / 1e12
xl = [d.strftime('%Y-%m') for d in orw.index]
i_apr = list(orw.index).index(pd.Timestamp('2026-04-20'))
i_jul = int(np.searchsorted(orw.index.values, np.datetime64('2026-07-06')))
c1 = lines(xl, ['OpenRouter 每週 token(兆)'], [list(orw.values)], unit='', aria='OpenRouter 每週處理 token 數,2024 年 3 月到 2026 年 10 月,對數座標', log=True, height=320,
           xtick_every=26, yticks=[0.01, 0.1, 1, 10, 100, 1000],
           extra_marks=[(i_apr, '七月版資料終點 2026-04-20'), (i_jul, '七月版報告 07-10')], end_values=[f'{orw.iloc[-1]:.0f} 兆'])
c1_rows = [(d.strftime('%Y-%m-%d'), f"{v:,.2f}" if v < 10 else f"{v:,.1f}") for d, v in orw.items() if d >= pd.Timestamp('2026-04-01')]
c1_tbl = datatable(['週(週一)', 'token(兆)'], c1_rows, summary='資料表 · 2026-04 起逐週 token 量(2026-04-27 之後為本次新接資料)')

# ---------- chart 2: indices indexed ----------
us = pd.read_csv(ROOT / 'data/us_indices_daily.csv', index_col=0, parse_dates=True)
seg = us.loc['2026-07-09':'2026-11-06'].ffill()
base = seg.iloc[0]
idx = (seg / base * 100)
xl2 = [d.strftime('%m-%d') for d in idx.index]
month_starts = [i for i, d in enumerate(idx.index) if i == 0 or idx.index[i-1].month != d.month]
i_peak = list(idx.index).index(pd.Timestamp('2026-10-06')); i_crash = list(idx.index).index(pd.Timestamp('2026-11-05'))
def _sparse_lines(xlabels, series, values, **kw):
    s = lines(xlabels, series, values, **kw)
    return s
c2 = lines(xl2, ['費城半導體 SOX', '台股加權 TWII', 'S&P 500'], [list(idx['sox'].round(1)), list(idx['twii'].round(1)), list(idx['spx'].round(1))],
           aria='費半、台股加權與 S&P 500 自 2026-07-09 起的指數化走勢(起點=100)', height=320, xtick_every=22,
           yticks=[60, 70, 80, 90, 100, 110], extra_marks=[(i_peak, '台股高點 10-06'), (i_crash, '11-05 費半 −12%')])
c2_rows = [(d.strftime('%Y-%m-%d'), f"{r.sox:.1f}", f"{r.twii:.1f}", f"{r.spx:.1f}") for d, r in idx.iterrows() if d.weekday() == 4 or d in (idx.index[0], idx.index[-1], pd.Timestamp('2026-10-06'), pd.Timestamp('2026-11-05'))]
c2_tbl = datatable(['日期', 'SOX', 'TWII', 'S&P 500'], c2_rows, summary='資料表 · 每週五與關鍵日的指數化水準(2026-07-09 = 100)')

# ---------- chart 3: quintiles full ----------
qc = R2c['quintile_mean_bps']; qs = R2s['quintile_mean_bps']
c3 = grouped_bars(['Q1 最低曝險', 'Q2', 'Q3', 'Q4', 'Q5 最高曝險'], ['消費因子(OpenRouter token)', '供給因子(SOX 殘差)'], [qc, qs], unit='',
                  aria=f'AI Beta 五分位的市值加權平均週報酬(bps),{R2c["n_weeks"]} 個持有週', height=300,
                  label_ext={(0, 0): fmt(qc[0]), (0, 4): fmt(qc[4]), (1, 0): fmt(qs[0]), (1, 4): fmt(qs[4])}, ylabel='bps/週')
c3_tbl = datatable(['五分位', '消費因子 bps/週', '供給因子 bps/週'], [(f"Q{i+1}", f"{qc[i]:.1f}", f"{qs[i]:.1f}") for i in range(5)] + [('H−L', f"{R2c['hl_bps']:.1f}", f"{R2s['hl_bps']:.1f}")], summary='資料表 · 五分位平均週報酬與 H−L')

# ---------- chart 4: post period cumulative Q1 vs Q5 ----------
wq = C4['weekly_q_post']; dates4 = list(wq.keys())
cum = {k: [] for k in (0, 4)}
for k in cum:
    acc = 0.0
    for d in dates4:
        v = wq[d][k]; acc += (0 if v is None or (isinstance(v, float) and math.isnan(v)) else v) / 1e4
        cum[k].append(100 * math.expm1(acc))
twii_w = np.log(us['twii'].dropna().resample('W-FRI').last()).diff()
twii_cum = []; acc = 0.0
for d in dates4:
    acc += float(twii_w.get(pd.Timestamp(d), 0.0) or 0.0); twii_cum.append(100 * math.expm1(acc))
xl4 = [d[5:] for d in dates4]
i4_peak = max([i for i, d in enumerate(dates4) if d <= '2026-10-09'], default=0)
c4 = '' if not dates4 else lines(xl4, ['Q5 最高 AI 曝險', 'Q1 最低 AI 曝險', '加權指數'], [[round(v, 2) for v in cum[4]], [round(v, 2) for v in cum[0]], [round(v, 2) for v in twii_cum]],
           unit='%', aria='2026-07-10 之後,消費因子 AI Beta 最高組與最低組的累積市值加權報酬,對照加權指數', height=320, xtick_every=3,
           extra_marks=[(i4_peak, '台股高點 10-06')])
c4_rows = [(dates4[i], f"{wq[dates4[i]][4]:.0f}" if wq[dates4[i]][4] == wq[dates4[i]][4] else '—', f"{wq[dates4[i]][0]:.0f}" if wq[dates4[i]][0] == wq[dates4[i]][0] else '—', f"{C4['weekly_hl_bps_post'].get(dates4[i], float('nan')):.0f}", f"{cum[4][i]:.1f}%", f"{cum[0][i]:.1f}%", f"{twii_cum[i]:.1f}%") for i in range(len(dates4))]
c4_tbl = datatable(['週(週五)', 'Q5 週報酬 bps', 'Q1 週報酬 bps', 'H−L bps', 'Q5 累積', 'Q1 累積', '加權累積'], c4_rows, summary='資料表 · 2026-07-10 之後逐週 Q5/Q1 報酬與累積')

# ---------- chart 5: crash week ----------
if CR:
    cq = CR['consumption']['quintile_pct']; sq = CR['supply']['quintile_pct']
    c5 = grouped_bars(['Q1 最低', 'Q2', 'Q3', 'Q4', 'Q5 最高'], ['依消費因子 Beta 分組', '依供給因子 Beta 分組'], [[round(v, 2) for v in cq], [round(v, 2) for v in sq]], unit='%',
                      aria=f'{crash_wk} 當週,AI Beta 五分位各自的市值加權週報酬', height=300,
                      label_ext={(0, 0): f"{cq[0]:.1f}%", (0, 4): f"{cq[4]:.1f}%", (1, 0): f"{sq[0]:.1f}%", (1, 4): f"{sq[4]:.1f}%"}, ylabel='週報酬 %')
    c5_tbl = datatable(['五分位', '消費 Beta 分組', '供給 Beta 分組'], [(f"Q{i+1}", f"{cq[i]:.2f}%", f"{sq[i]:.2f}%") for i in range(5)] + [('H−L', f"{CR['consumption']['hl_pct']:.2f}%", f"{CR['supply']['hl_pct']:.2f}%"), ('加權指數', f"{CR['twii_pct']:.2f}%", f"{CR['twii_pct']:.2f}%")], summary=f'資料表 · {crash_wk} 當週五分位報酬')
else:
    c5 = c5_tbl = ''

# ---------- comparison tables ----------
def ci(x): return f"[{x[0]:.0f}, {x[1]:.0f}]"
cmp_rows = [
 ('消費因子 H−L(bps/週)', f"{J2c['hl_bps']:+.1f}(t={J2c['t']:.2f})", f"{R2c['hl_bps']:+.1f}(t={R2c['t']:.2f})"),
 ('　95% 信賴區間', ci(J2c['ci_bps']), ci(R2c['ci_bps'])),
 ('　樣本週數', str(J2c['n_weeks']), str(R2c['n_weeks'])),
 ('供給因子 H−L(bps/週)', f"{J2s['hl_bps']:+.1f}(t={J2s['t']:.2f})", f"{R2s['hl_bps']:+.1f}(t={R2s['t']:.2f})"),
 ('　95% 信賴區間', ci(J2s['ci_bps']), ci(R2s['ci_bps'])),
 ('FM λ 消費 beta(bps)', f"{J2c['fm_lambda_bps']:+.1f}(t={J2c['fm_t']:.2f})", f"{R2c['fm_lambda_bps']:+.1f}(t={R2c['fm_t']:.2f})"),
 ('動能糾纏 Q1 / Q5', f"{J2c['momentum_by_quintile'][0]:.3f} / {J2c['momentum_by_quintile'][4]:.3f}", f"{R2c['momentum_by_quintile'][0]:.3f} / {R2c['momentum_by_quintile'][4]:.3f}"),
 ('前沿發布五日 H−L(論文日曆)', f"{J1['frontier']['stats']['total']['mean_hl_pct']:+.3f}%(t={J1['frontier']['stats']['total']['t']:.2f},n={J1['frontier']['n_events']})", f"{R1['frontier']['stats']['total']['mean_hl_pct']:+.3f}%(t={R1['frontier']['stats']['total']['t']:.2f},n={R1['frontier']['n_events']})"),
 ('　其中盤中通道', f"{J1['frontier']['stats']['intraday']['mean_hl_pct']:+.3f}%(t={J1['frontier']['stats']['intraday']['t']:.2f})", f"{R1['frontier']['stats']['intraday']['mean_hl_pct']:+.3f}%(t={R1['frontier']['stats']['intraday']['t']:.2f})"),
 ('前沿發布五日 H−L(延伸日曆,含 2026 事件)', '—', f"{R1c['frontier']['stats']['total']['mean_hl_pct']:+.3f}%(t={R1c['frontier']['stats']['total']['t']:.2f},n={R1c['frontier']['n_events']})"),
 ('　其中隔夜通道', '—', f"{R1c['frontier']['stats']['overnight']['mean_hl_pct']:+.3f}%(t={R1c['frontier']['stats']['overnight']['t']:.2f})"),
 ('外資雙重排序 買−賣差(bps)', f"{J3['double_sort']['buy_minus_sell_diff']['hl_bps']:+.1f}(t={J3['double_sort']['buy_minus_sell_diff']['t_stat']:.2f})", f"{R3['double_sort']['buy_minus_sell_diff']['hl_bps']:+.1f}(t={R3['double_sort']['buy_minus_sell_diff']['t_stat']:.2f})"),
 ('H−L 路徑:隔夜 / 盤中(bps)', f"{J3['path']['overnight']['hl_bps']:+.1f} / {J3['path']['intraday']['hl_bps']:+.1f}", f"{R3['path']['overnight']['hl_bps']:+.1f} / {R3['path']['intraday']['hl_bps']:+.1f}"),
]
cmp_tbl = '<div class="table-scroll"><table><thead><tr><th>檢定</th><th class="num">2026-07-10 版</th><th class="num">2026-11-08 版</th></tr></thead><tbody>' + ''.join(f'<tr><td>{a}</td><td class="num">{b_}</td><td class="num">{c}</td></tr>' for a, b_, c in cmp_rows) + '</tbody></table></div>'

def sub_row(name, d):
    return (name, f"{d['n_weeks']}", nz(d['hl_bps']), nz(d['t'], '{:.2f}'), ci(d['ci_bps']) if d['ci_bps'][0] == d['ci_bps'][0] else '—', f"{d['cum_pct']:+.1f}%")
sub_rows = [sub_row('消費因子 · 全樣本', C4['full']), sub_row('消費因子 · 2026-07-10 以前', C4['pre_2026_07_10']), sub_row('消費因子 · 2026-07-10 之後', C4['post_2026_07_10']), sub_row('消費因子 · 台股 10-06 高點之後', C4['post_twii_peak']),
            sub_row('供給因子 · 全樣本', S4['full']), sub_row('供給因子 · 2026-07-10 以前', S4['pre_2026_07_10']), sub_row('供給因子 · 2026-07-10 之後', S4['post_2026_07_10']), sub_row('供給因子 · 台股 10-06 高點之後', S4['post_twii_peak'])]
sub_tbl = '<div class="table-scroll"><table><thead><tr><th>子期間</th><th class="num">週數</th><th class="num">H−L bps/週</th><th class="num">t</th><th class="num">95% CI</th><th class="num">H−L 累積</th></tr></thead><tbody>' + ''.join('<tr>' + f'<td>{r[0]}</td>' + ''.join(f'<td class="num">{x}</td>' for x in r[1:]) + '</tr>' for r in sub_rows) + '</tbody></table></div>'

post_c = C4['post_2026_07_10']; post_s = S4['post_2026_07_10']; pk_c = C4['post_twii_peak']; pk_s = S4['post_twii_peak']
qcum_post = C4['quintile_cum_pct_post']; qcum_pk = C4.get('quintile_cum_pct_post_peak', [float('nan')]*5)
scum_pk = S4.get('quintile_cum_pct_post_peak', [float('nan')]*5)
hl_post = C4['weekly_hl_bps_post']
cum_to_1002 = 100*math.expm1(sum(v for d, v in hl_post.items() if d <= '2026-10-02')/1e4)
q5_to_1002 = 100*math.expm1(sum(wq[d][4] for d in dates4 if d <= '2026-10-02')/1e4)
q1_to_1002 = 100*math.expm1(sum(wq[d][0] for d in dates4 if d <= '2026-10-02')/1e4)
cq_ = CR['consumption']['quintile_pct'] if CR else [0]*5
q5_oct9_nov6 = 100*((1+qcum_pk[4]/100)*(1+cq_[4]/100)-1)
q1_oct9_nov6 = 100*((1+qcum_pk[0]/100)*(1+cq_[0]/100)-1)
hl_jul_nov = 100*((1+post_c['cum_pct']/100)*(1+CR['consumption']['hl_pct']/100)-1) if CR else post_c['cum_pct']
n_big_post = sum(1 for v in hl_post.values() if abs(v) > 200)

# ---------- HTML ----------
html = f'''<!doctype html>
<html lang="zh-Hant">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="imitator-style" content="v3">
<meta name="imitator-register" content="複檢單 — 車主說 AI 熄火了,技師把用量、基本面、價格三個系統分開測,再把七月的路試重跑一次">
<meta name="imitator-reference" content="1980 年代修車廠的三聯式無碳複寫工單 — 黃色客戶聯、等寬欄位、逐項勾選、原子筆簽收">
<meta name="imitator-paper" content="hsl(48 48% 92%)">
<meta name="imitator-accent" content="hsl(224 58% 40%)">
<title>AI 熄火了嗎?四個月後的複檢</title>
<meta name="description" content="2026 年 7 月我們說台股沒有 AI 溢酬。四個月後費半跌掉三分之一、台股一個月跌兩成。把 OpenRouter 用量、台積電與 hyperscaler 基本面、股價三個系統分開測,再把台股全市場實驗重跑一次。">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+Condensed:wght@500;700&family=Noto+Sans+TC:wght@400;700&family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
{CSS}

/* REGISTER:  複檢單 — 車主(讀者)七月拿到一份「台股沒有 AI 溢酬」的路試報告,現在回廠問「AI 熄火了嗎」。
              技師不回答是或否,把供油(用量)、壓縮(基本面)、點火(價格)三個系統分開測,再把七月的路試整個重跑。
   REFERENCE: 1980 年代修車廠的三聯式無碳複寫工單,黃色客戶聯 — 表頭窄體大寫、等寬打字欄位、逐項勾選、
              技師用原子筆在結論欄簽名。每一項「檢測結果」旁邊都有讀數,沒有讀數的判斷不算數。
   PAPER:     無碳複寫紙的黃色客戶聯 — hsl(48 48% 92%)。暖黃,因為這是車主帶回家貼在冰箱上的那一聯,不是原稿。
   VOICE:     技師原子筆的鈷藍 hsl(224 58% 40%) 只給三件事:標題裡那個字、工單項目編號、連結。
              標題 IBM Plex Sans Condensed(工單表頭的窄體)+ Noto Sans TC;欄位標籤、讀數、簽收用 IBM Plex Mono。
              裁決用字寫出來(「未熄火」「熄火」),不用紅綠燈顏色暗示。
   NOT:       不是儀表板,沒有互動元件。圖是檢測讀數,每張附數字表;沒有「關鍵要點」框,結論就是工單最後一欄。
   DARK:      夜班修車廠的工作燈下 — 紙變成帶黃調的暖近黑 hsl(44 16% 9%),原子筆藍提亮為 hsl(222 75% 74%)。
   RECENT:    unavailable(無 IMITATOR_TOKEN)。已避開:七月版 ai-premium(近白 #FBFAF7 + 藍灰)、
              mockup(骨白 44° + 靛 223° 30%)— 本篇紙 48° 48% 明顯偏黃、accent 224° 40% 更亮更飽和,
              以及 autopsy(奶油紙 + 紅章)、epic(暖奶油 + 幕紅)等 specimen。*/
:root {{
  --paper: hsl(48 48% 92%);        /* 黃色客戶聯 */
  --card: hsl(48 52% 96%);
  --ink: hsl(225 25% 14%);         /* 原子筆藍黑 */
  --ink-2: hsl(225 14% 32%);
  --mist: hsl(40 10% 40%);
  --rule: hsl(46 30% 80%);
  --rule-hard: hsl(46 28% 62%);
  --accent: hsl(224 58% 40%);      /* 技師的鈷藍原子筆 */
  --accent-soft: hsl(224 45% 89%);
  --sans: "Noto Sans TC", "PingFang TC", "Microsoft JhengHei", sans-serif;
  --disp: "IBM Plex Sans Condensed", "Noto Sans TC", sans-serif;
  --mono: "IBM Plex Mono", ui-monospace, Menlo, monospace;
  --serif: "Noto Sans TC", sans-serif;
}}
@media (prefers-color-scheme: dark) {{
  :root:where(:not([data-theme="light"])) {{
    --paper: hsl(44 16% 9%); --card: hsl(44 14% 13%);
    --ink: hsl(45 25% 92%); --ink-2: hsl(45 12% 76%); --mist: hsl(45 8% 62%);
    --rule: hsl(44 10% 22%); --rule-hard: hsl(44 10% 34%);
    --accent: hsl(222 75% 74%); --accent-soft: hsl(222 35% 24%);
  }}
}}
:root[data-theme="dark"] {{
  --paper: hsl(44 16% 9%); --card: hsl(44 14% 13%);
  --ink: hsl(45 25% 92%); --ink-2: hsl(45 12% 76%); --mist: hsl(45 8% 62%);
  --rule: hsl(44 10% 22%); --rule-hard: hsl(44 10% 34%);
  --accent: hsl(222 75% 74%); --accent-soft: hsl(222 35% 24%);
}}
/* 工單欄位:等寬、字距、頂線像表格邊 */
.display {{ font-weight: 700; letter-spacing: -.01em; }}
.eyebrow {{ text-transform: none; }}
.field {{ font-family: var(--mono); font-size: var(--fs-xs); letter-spacing: .06em; color: var(--mist); display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 12rem), minmax(0, 1fr))); gap: var(--sp-2) var(--sp-5); border-top: 1px solid var(--rule-hard); border-bottom: 1px solid var(--rule); padding: var(--sp-3) 0; margin: var(--sp-5) 0; }}
.field > div {{ min-width: 0; }}
.field b {{ display: block; color: var(--ink-2); font-weight: 500; margin-top: .15em; overflow-wrap: anywhere; }}
.verdict {{ font-family: var(--mono); font-size: var(--fs-sm); display: grid; grid-template-columns: minmax(0, 1fr); gap: var(--sp-2); margin: var(--sp-5) 0; }}
.verdict > div {{ display: grid; grid-template-columns: 7.5rem minmax(0, 1fr); gap: var(--sp-3); align-items: baseline; padding: var(--sp-2) 0; border-bottom: 1px solid var(--rule); min-width: 0; }}
.verdict .k {{ color: var(--mist); letter-spacing: .06em; font-size: var(--fs-xs); }}
.verdict .v {{ color: var(--ink); min-width: 0; }}
.verdict .v .chip {{ margin-right: .5em; vertical-align: baseline; }}
@media (max-width: 40rem) {{ .verdict > div {{ grid-template-columns: minmax(0, 1fr); gap: var(--sp-1); }} }}
.sign {{ font-family: var(--mono); font-size: var(--fs-xs); color: var(--mist); letter-spacing: .06em; border-top: 1px solid var(--rule-hard); padding-top: var(--sp-3); margin-top: var(--sp-6); }}
.sign b {{ color: var(--accent); font-weight: 500; }}
figure .title {{ font-weight: 700; margin: 0 0 var(--sp-1); }}
figure .subtitle {{ color: var(--mist); font-size: var(--fs-sm); margin: 0 0 var(--sp-3); }}
figure figcaption {{ color: var(--ink-2); font-size: var(--fs-sm); margin-top: var(--sp-3); }}
.cansay {{ font-family: var(--mono); font-size: var(--fs-xs); color: var(--mist); letter-spacing: .04em; margin-top: var(--sp-3); }}
.cansay b {{ color: var(--ink-2); font-weight: 500; }}
</style>
<body>
<div class="progress"></div>
<button class="theme-toggle" id="theme-toggle" type="button" aria-pressed="false">theme · auto</button>

<main class="report">

<p class="eyebrow">複檢單 · ai_premium_tw · 2026-11-08 · 接 2026-07-10 版路試報告</p>
<h1 class="display">熄火的是<em>股價</em>,<br>不是引擎</h1>
<p class="lede">七月我們說台股沒有 AI 溢酬。四個月後費城半導體指數從高點跌掉三分之一、台股一個月跌兩成,車主回廠問:AI 熄火了嗎?這張複檢單把三個系統分開測:用量、基本面、價格。然後把七月那場台股全市場實驗,用延長到 2026 年 11 月 6 日的資料整個重跑一次。</p>
<p class="byline">描述性研究,不是投資建議,沒有任何一檔股票的買賣訊號。</p>

<div class="field reveal">
  <div>車主敘述<b>「AI 行情熄火了」</b></div>
  <div>上次進廠<b>2026-07-10 · 結論:台股無 AI 溢酬</b></div>
  <div>本次里程<b>{weeks0} → {weeks1} · {nweeks} 週(持有週 {R2c['n_weeks']})</b></div>
  <div>樣本<b>上市櫃普通股 {R2c_n_stocks} 檔 · TWSE/TPEx 官方 + Yahoo 備援</b></div>
</div>

<p class="eyebrow">讀數 · READINGS</p>
<h2>先把四個儀表一起看</h2>
<div class="tiles wide stagger">
  <div class="stat"><p class="label">OpenRouter 每週 token(2026-10-26 當週)</p><div class="value">{OR['last_value']/1e12:,.0f} 兆</div><div class="delta up">四月版資料終點以來 ×{tok_x_since_apr:.1f}</div></div>
  <div class="stat"><p class="label">台積電 2026 Q3 營收</p><div class="value">+50%</div><div class="delta">年增,連六季創高;Q4 指引續增</div></div>
  <div class="stat"><p class="label">費城半導體 SOX</p><div class="value">{sox_dd:.0f}%</div><div class="delta down">自 2026-06-22 高點;七月版報告以來 {sox_0709:.0f}%</div></div>
  <div class="stat"><p class="label">台股加權指數</p><div class="value">{twii_dd:.0f}%</div><div class="delta down">自 2026-10-06 高點;七月版以來 {twii_0709:.0f}%</div></div>
</div>
<p>四個讀數指向兩個方向。<span class="mark">用量和基本面的儀表還在往上走,股價的儀表掉了一大截。</span>「熄火」這個詞只對得上其中一個。所以這張單子不問「AI 熄火了嗎」,改問三個可以分開檢測的問題:用量還在長嗎、基本面還在長嗎、市場付的價格怎麼了。最後再問第四個,也是七月那份報告真正的問題:台股有沒有在為 AI 曝險定價。</p>

<p class="eyebrow">項目 01 · 供油 FUEL · 用量</p>
<h2>引擎的轉速:token 還在加速</h2>
<p>七月版報告的消費因子,靠的是 OpenRouter 公開排行榜頁面裡嵌的週用量圖,用網路時光機縫到 2026 年 4 月就斷了,因為那之後頁面改成純前端繪圖。這次我們直接讀該頁面載入時呼叫的圖表 API,拿到 2025 年 11 月到 2026 年 11 月的逐週 token 量;和舊序列重疊的 24 週,最大相對差 0.43%,可以接上。</p>
<figure class="reveal">
  <p class="title">OpenRouter 每週處理的 token 量(兆,對數座標)</p>
  <p class="subtitle">2024-03 到 2026-10,共 {len(orw)} 週。對數座標上每一格是十倍。</p>
  <div class="chart">{c1}</div>
  {c1_tbl}
  <figcaption>從七月版的資料終點(2026-04-20 當週 {orw.loc['2026-04-20']:.1f} 兆)到 2026-10-26 當週 {orw.iloc[-1]:.0f} 兆,半年成長 {tok_x_since_apr:.1f} 倍;年增 {tok_yoy:.0f} 倍。週均對數成長率:2025 年 {g['2025']:.3f}、2026 上半年 {g['2026H1']:.3f}、2026 年 7 到 10 月 {g['2026-07..10']:.3f} —— 股價下跌的這四個月,用量成長沒有減速,還略快。</figcaption>
</figure>
<p>要誠實說清楚這個讀數量的是什麼。它是處理的 token 數,不是收入。2026 年 11 月第一週 OpenRouter 用量第一名是 DeepSeek V4.1 Flash,單週 56 兆 token,前十名裡有七個是中國實驗室的低價模型;token 暴增的一部分來自「每顆 token 變便宜了,所以大家用得更兇」。論文(Borri、Liu 與 Tsyvinski 的《AI Premium》)在 2026 年 4 月就記錄過同一件事:agentic 工作流讓 token 量佔比衝到一半以上,單價同步下跌。所以供油系統的讀數是:<b>燃料流量還在加速,但每公升變便宜了。</b>這對 AI 應用是好消息,對賣算力的人是雙面刃。</p>
<p class="cansay"><b>資料能說</b> 真實付費用量仍在加速成長 ✓　<b>資料不能說</b> 美元營收是否同步 ✗(只有 token 單腿)</p>

<p class="eyebrow">項目 02 · 壓縮 COMPRESSION · 基本面</p>
<h2>汽缸壓力:台積電與四大雲端的帳本</h2>
<p>這一項我們沒有自建資料,用的是公開財報與媒體轉述,所以寫在單子上的是「讀到的數字」而不是「量到的數字」,數字之間有出入的地方照實標。</p>
<div class="table-scroll"><table>
<thead><tr><th>指標</th><th>讀數(2026-10 / 11)</th><th class="nowrap">和七月比</th></tr></thead>
<tbody>
<tr><td>台積電 Q3 營收</td><td>新台幣 1.49 兆,年增約 50%(各家報導 39% 到 51%),連續六季創高;高效能運算佔營收 68%(去年同期 57%)</td><td class="num">加速</td></tr>
<tr><td>台積電展望</td><td>Q4 指引 523 到 543 億美元,2026 全年美元營收成長上修到約 44%;法說會原話:「需求遠超過我們今天的供給能力」</td><td class="num">上修</td></tr>
<tr><td>四大雲端 2026 資本支出</td><td>Amazon、Alphabet、Meta、Microsoft 合計約 8,000 億美元量級;Alphabet 上修到 1,950 到 2,050 億並預告 2027「顯著增加」;Microsoft 的 1,700 與 1,900 億兩個數字並存,差異來自會計口徑</td><td class="num">上修</td></tr>
<tr><td>Meta 2026 資本支出</td><td>區間收斂為 1,350 到 1,450 億;未給 2027 數字</td><td class="num">持平</td></tr>
</tbody></table></div>
<p>壓縮系統的讀數:<b>沒有一個基本面數字在這四個月轉向。</b>市場在十月中擔心的不是需求,是「這些資本支出用什麼錢付」:利率升、AI 基建靠舉債,財務成本成了新變數。這是估值的問題,不是引擎的問題。但也要說清楚它的極限:這些是落後指標,台積電的 Q3 是七到九月的事,而且「需求遠超供給」是供應商的話,不是買方的話。</p>
<p class="cansay"><b>資料能說</b> 到 2026 Q3 為止,供應鏈營收與雲端 capex 指引仍在上修 ✓　<b>資料不能說</b> 2027 年的訂單 ✗</p>

<p class="eyebrow">項目 03 · 點火 IGNITION · 價格</p>
<h2>火星塞:四個月跌掉的是估值</h2>
<figure class="reveal">
  <p class="title">費半、台股加權、S&amp;P 500:自七月版報告日起的走勢</p>
  <p class="subtitle">2026-07-09 = 100。三個系列共用一條 y 軸。</p>
  <div class="chart">{c2}</div>
  <div class="legend"><span class="key"><span class="swatch" style="background:var(--c1)"></span>費城半導體 SOX</span><span class="key"><span class="swatch" style="background:var(--c2)"></span>台股加權 TWII</span><span class="key"><span class="swatch" style="background:var(--c3)"></span>S&amp;P 500</span></div>
  {c2_tbl}
  <figcaption>七月版報告日到 2026-11-06:費半 {sox_0709:.1f}%、台股加權 {twii_0709:.1f}%、S&amp;P 500 {spx_0709:.1f}%。費半的高點在 6 月 22 日,台股的高點卻晚到 10 月 6 日(49,823 點),然後一個月跌 {abs(twii_peak_to_now):.0f}%。11 月 5 日費半單日跌 12.2%,隔天台股盤中跌 3,737 點,是史上最大盤中跌點。</figcaption>
</figure>
<p>把這四個月的新聞排成時間軸,每一次下跌的理由都和「AI 用量減少」無關:6 月 26 日是 AI 基建成本太高;7 月 17 日是台積電財報超標但資本支出比預期多,股價反而跌;7 月 29 日起一週晶片股市值蒸發一兆美元;10 月 15 日是通膨數據偏熱、市場擔心升息,而 AI 基建靠舉債;11 月 5 日是美國期中選舉後,市場擔心新國會加強資料中心審查,費半單日跌 12.2%、台幣跌破 33 元、外資大舉匯出。<span class="mark">每一條理由都在說「這些現金流值多少錢」,沒有一條在說「現金流不見了」。</span></p>
<p>所以點火系統的讀數是:<b>價格對同一份基本面重新開價,打了三折到兩折。</b>這就是「熄火」在市場語言裡的真正意思,它是一個關於估值的詞。費半在六月到十月、台股在十月到十一月,各自經歷了一次本益比壓縮;台股晚了三個半月,然後用一個月追完。</p>
<p class="cansay"><b>資料能說</b> 四個月的下跌是估值壓縮,新聞歸因全在成本、利率、政策 ✓　<b>資料不能說</b> 壓縮完了沒有 ✗</p>

<p class="eyebrow">項目 04 · 路試 ROAD TEST · 七月的實驗重跑</p>
<h2>台股有沒有為 AI 曝險定價:加上四個月後再測一次</h2>
<p>七月那份報告的核心實驗是:把全球 AI 用量的週變動當成一個「AI 因子」,算出每一檔台股對它的敏感度(AI Beta),每週把股票按 Beta 分五組,看最高組有沒有持續贏過最低組。論文在美股測到每週 64 個基點,台股測到零。這次樣本從 {J2c['n_weeks']} 週延長到 {R2c['n_weeks']} 週,新增的部分正好涵蓋這一輪下跌。</p>
<figure class="reveal">
  <p class="title">AI Beta 五分位的平均週報酬(市值加權,{R2c['n_weeks']} 個持有週)</p>
  <p class="subtitle">若台股在為 AI 曝險付錢,長條應該由左往右遞增。</p>
  <div class="chart">{c3}</div>
  <div class="legend"><span class="key"><span class="swatch" style="background:var(--c1)"></span>消費因子(OpenRouter token)</span><span class="key"><span class="swatch" style="background:var(--c2)"></span>供給因子(SOX 殘差)</span></div>
  {c3_tbl}
  <figcaption>消費因子 H−L = {R2c['hl_bps']:+.1f} bps/週(t = {R2c['t']:.2f}),95% 信賴區間 {ci(R2c['ci_bps'])};七月版是 {J2c['hl_bps']:+.1f} bps、區間 {ci(J2c['ci_bps'])}。供給因子 H−L = {R2s['hl_bps']:+.1f} bps(t = {R2s['t']:.2f})。兩個區間都排除了論文的美股量級 64 bps。</figcaption>
</figure>
<p>七月的結論一字不改:<span class="mark">台股沒有 AI 溢酬,點估計是零,信賴區間排除美股量級。</span>多了四個月、多了一次兩成的修正,零還是零。Fama-MacBeth 橫斷面迴歸的 AI Beta 溢酬 {R2c['fm_lambda_bps']:+.0f} bps(t = {R2c['fm_t']:.2f})不顯著;五分位之間的事前動能差異乾淨(Q1 {R2c['momentum_by_quintile'][0]:.3f} 對 Q5 {R2c['momentum_by_quintile'][4]:.3f}),這個零不是動能借來的。</p>

<h3>真正的新問題:下跌時,高 AI 曝險的股票有沒有跌得比較多?</h3>
<p>這是車主最想知道的。如果「AI 熄火」是一個被市場系統性定價的事件,那麼對 AI 用量最敏感的那一組股票,在下跌的四個月裡應該明顯跑輸最不敏感的那一組。</p>
<figure class="reveal">
  <p class="title">2026-07-10 之後:最高與最低 AI 曝險組的累積報酬,對照加權指數</p>
  <p class="subtitle">每週用前一週的消費因子 Beta 分組,市值加權,{post_c['n_weeks']} 週。</p>
  <div class="chart">{c4}</div>
  <div class="legend"><span class="key"><span class="swatch" style="background:var(--c1)"></span>Q5 最高 AI 曝險</span><span class="key"><span class="swatch" style="background:var(--c2)"></span>Q1 最低 AI 曝險</span><span class="key"><span class="swatch" style="background:var(--c3)"></span>加權指數</span></div>
  {c4_tbl}
  <figcaption>七月版報告之後的 {post_c['n_weeks']} 週:H−L 平均 {post_c['hl_bps']:+.1f} bps/週(t = {post_c['t']:.2f}),累積 {post_c['cum_pct']:+.1f}%;Q5 累積 {qcum_post[4]:+.1f}%、Q1 累積 {qcum_post[0]:+.1f}%。台股 10 月 6 日高點之後的 {pk_c['n_weeks']} 週:H−L 平均 {nz(pk_c['hl_bps'], '{:+.0f}')} bps/週、累積 {pk_c['cum_pct']:+.1f}%({pk_c['n_weeks']} 週不算 t 值)。供給因子分組同期:高點後 H−L 累積 {pk_s['cum_pct']:+.1f}%。</figcaption>
</figure>
<p>先說結果,再說它有多吵。七月版報告之後到 10 月 30 日的 {post_c['n_weeks']} 週,最高 AI 曝險組(Q5)累積 {qcum_post[4]:+.1f}%,最低組(Q1)累積 {qcum_post[0]:+.1f}%,H−L 平均 {post_c['hl_bps']:+.0f} bps/週但 t 值只有 {post_c['t']:.2f},信賴區間 {ci(post_c['ci_bps'])}。單看這一段,高曝險組反而比較抗跌。但拆開看是兩段相反的行情:<span class="mark">到 10 月 2 日為止,Q5 比 Q1 多漲了 {cum_to_1002:.0f} 個百分點(Q5 {q5_to_1002:+.1f}%、Q1 {q1_to_1002:+.1f}%);台股 10 月 6 日見高點之後,Q5 在四週內跌 {abs(qcum_pk[4]):.1f}%、Q1 跌 {abs(qcum_pk[0]):.1f}%。</span>多頭段按 AI 曝險漲,下跌段按 AI 曝險跌。</p>
<p>更值得記的是「吵」的程度。七月版樣本裡,H−L 的週波動是 204 bps,{post_c['n_weeks']} 週的新樣本是 322 bps;單週 H−L 超過正負 2% 的週數,舊樣本 105 週裡有 32 週,新樣本 {post_c['n_weeks']} 週裡有 {n_big_post} 週。這是七月版沒有的現象:<b>AI 曝險第一次變成台股橫斷面每週最主要的分組變數</b>,只是它的平均報酬還是零。</p>
{('''<figure class="reveal">
  <p class="title">崩盤週(''' + crash_wk + ''' 當週)五分位各自跌多少</p>
  <p class="subtitle">用 10 月 30 日的 Beta 分組,看 11 月 2 日到 6 日這一週。這一週 OpenRouter 用量資料尚未完整,所以沒有進主檢定,單獨列出。</p>
  <div class="chart">''' + c5 + '''</div>
  <div class="legend"><span class="key"><span class="swatch" style="background:var(--c1)"></span>依消費因子 Beta 分組</span><span class="key"><span class="swatch" style="background:var(--c2)"></span>依供給因子 Beta 分組</span></div>
  ''' + c5_tbl + '''
  <figcaption>加權指數當週 ''' + f"{CR['twii_pct']:+.1f}%" + '''。消費 Beta 分組 H−L ''' + f"{CR['consumption']['hl_pct']:+.2f}%" + ''';供給 Beta 分組 H−L ''' + f"{CR['supply']['hl_pct']:+.2f}%" + '''。</figcaption>
</figure>''') if CR else ''}
<p>然後是 11 月 2 日到 6 日。加權指數當週 {CR['twii_pct']:+.1f}%,全市場市值加權 −12.9%。用 10 月 30 日的消費因子 Beta 分五組:最低曝險組 {cq_[0]:+.1f}%,最高曝險組 {cq_[4]:+.1f}%,差距 {CR['consumption']['hl_pct']:+.1f} 個百分點;從 Q3 到 Q5 一路遞增的跌幅,是全樣本裡第一次出現教科書式的排序。這一組 Q5 市值最大的八檔是欣興、南亞科、緯穎、健策、川湖、南電、華邦電、大立光,當週跌幅 14% 到 27%;Q1 市值最大的是聯發科和五家金控,跌 3% 到 13%。用 OpenRouter token 成長率算出來的 Beta,到 10 月底已經把台股的 AI 伺服器、載板、記憶體族群排進了最高曝險組,這件事本身就是訊號:市場正在用「AI 用量」這把尺重新給台股分組。</p>
<p>把三段接起來看:7 月 17 日到 10 月 2 日 H−L {cum_to_1002:+.1f}%,10 月 9 日到 11 月 6 日 Q5 累積 {q5_oct9_nov6:+.1f}%、Q1 累積 {q1_oct9_nov6:+.1f}%;四個月合計 H−L 約 {hl_jul_nov:+.1f}%。<span class="mark">承擔 AI 曝險這四個月,先拿到十六個百分點,再全部交回去。</span>這正是「沒有溢酬」在一輪完整漲跌裡長的樣子:曝險影響股價,但長期不給補償。</p>

<h3>其他兩個設計,順手重跑</h3>
<p><b>事件研究。</b>用論文自己的 19 個前沿模型發布日曆(止於 2025 年 8 月的 GPT-5),結果與七月版完全相同:發布後五日高低曝險組差距 {R1['frontier']['stats']['total']['mean_hl_pct']:+.2f}%(t = {R1['frontier']['stats']['total']['t']:.2f}),不顯著,訊號集中在盤中;七月版留檔的「非前沿發布日隔夜報酬偏負」(−0.32%,t = −3.44)也原樣還在。我們另外把日曆延伸到 2026 年 11 月,加入 Claude Opus 4.8 與 5、GPT-5.6 與 GPT-6、Gemini 4、Claude Opus 5.5 等 2026 年的旗艦發布(日期取 OpenRouter 目錄上架日,屬二手來源),前沿事件增為 {R1c['frontier']['n_events']} 個:五日 H−L {R1c['frontier']['stats']['total']['mean_hl_pct']:+.2f}%(t = {R1c['frontier']['stats']['total']['t']:.2f}),仍是零,隔夜通道 {R1c['frontier']['stats']['overnight']['mean_hl_pct']:+.2f}%(t = {R1c['frontier']['stats']['overnight']['t']:.2f})不顯著。只看 2026 年 5 月之後的 7 個前沿事件,五日 H−L {R['R1d_design1_extended_calendar_2026H2_only']['frontier']['stats']['total']['mean_hl_pct']:+.2f}%(t = {R['R1d_design1_extended_calendar_2026H2_only']['frontier']['stats']['total']['t']:.2f}):點估計是歷來最大,樣本也是歷來最小,只能當方向看。</p>
<p><b>外資通道。</b>七月版否決了「溢酬由外資買超與隔夜跳空傳導」的假說。這次樣本延長後結論相同:外資買超組與賣超組之間的 H−L 差 {R3['double_sort']['buy_minus_sell_diff']['hl_bps']:+.1f} bps(t = {R3['double_sort']['buy_minus_sell_diff']['t_stat']:.2f});控制外資流後 AI Beta 的溢酬估計沒有衰減。要注意一個資料限制:2026 年 7 月 10 日之後上市股票的外資買賣超,因為證交所端點封鎖本次執行環境,只有 3 個交易日有官方資料,其餘缺值;上櫃外資資料完整。所以這一項的新增樣本主要是上櫃股票。</p>

<p class="eyebrow">項目 05 · 技師結論 VERDICT</p>
<h2>工單最後一欄</h2>
<div class="verdict reveal">
  <div><span class="k">供油 · 用量</span><span class="v"><span class="chip">未熄火</span>OpenRouter 週 token 半年 ×{tok_x_since_apr:.1f},7 到 10 月成長率沒有放慢。單價下跌是伴隨現象,不是反證。</span></div>
  <div><span class="k">壓縮 · 基本面</span><span class="v"><span class="chip">未熄火</span>台積電連六季創高且上修全年;四大雲端 2026 capex 仍在上修。全部是落後指標。</span></div>
  <div><span class="k">點火 · 價格</span><span class="v"><span class="chip">熄火</span>費半自高點 {sox_dd:.0f}%、台股自高點 {twii_dd:.0f}%。這是對同一份現金流的重新開價,歸因在成本、利率、政策。</span></div>
  <div><span class="k">路試 · 台股 AI 因子</span><span class="v"><span class="chip">與七月相同</span>台股沒有 AI 溢酬因子。全樣本 H−L {R2c['hl_bps']:+.1f} bps/週、區間 {ci(R2c['ci_bps'])}。新發現:這四個月 AI 曝險成了橫斷面的主軸,先漲後跌、合計歸零;崩盤週高曝險組跌幅是低曝險組的 {cq_[4]/cq_[0]:.1f} 倍。</span></div>
</div>
<p class="pull">車主問的是一台車,其實是三個系統。引擎還在轉,壓縮正常,熄的是點火,也就是市場願意為每一單位算力付的價格。</p>

<h3>三個反思</h3>
<p><b>一、「熄火」是價格的詞,不是技術的詞。</b>這四個月的新聞裡,沒有一條在說人們用 AI 用得少了;每一條都在說算力的成本、資金的成本、政策的成本。把「AI 股跌了」翻譯成「AI 熄火了」,是把儀表板上的一個表當成了全部。七月版報告說過市場在為「用 AI 的公司」付錢,不是為「造 AI 零件的公司」;這一輪跌最重的正是造零件的那一邊,與論文裡負曝險名單塞滿半導體的發現是同一件事的兩面。</p>
<p><b>二、台股沒有 AI 溢酬,不等於 AI 曝險不影響台股。</b>七月版的「零」量的是平均補償。這四個月給了一個更完整的畫面:高曝險組在多頭段多漲十六個百分點,在五週的下跌段把它全部還回去,崩盤週的跌幅是低曝險組的近兩倍。這就是「風險被定價、但不被補償」:市場用 AI 用量這把尺給台股分組的力道比七月強得多(H−L 週波動從 204 bps 升到 322 bps),分組之後卻不付錢。對持有欣興、南亞科、緯穎這一類被排進最高曝險組的股票的人,這句話的白話版是:你承擔的是一個會放大漲跌、但長期不給額外報酬的曝險。</p>
<p><b>三、下一次複檢,什麼叫「真的熄火」,現在就寫死。</b>我們不想在下一輪翻資料翻到想要的答案為止,所以先寫下判準:(a)用量:OpenRouter 週 token 的 13 週移動平均低於前一個 13 週;(b)基本面:台積電高效能運算營收季減,或四大雲端的 2027 年 capex 指引合計下修一成以上;(c)價格不是判準,價格是儀表。三項裡只要 (a) 或 (b) 任一成立,下一份工單才會寫「引擎熄火」。</p>

<p class="eyebrow">Q&amp;A · 車主常問</p>
<h2>你可能正想問的</h2>
<h3>跌了兩成,可以撿了嗎?</h3>
<p>這張工單能告訴你的是:引擎沒壞,跌的是價格。它不能告訴你價格跌夠了沒有,因為「估值壓縮到哪裡停」取決於利率、政策與資金成本,這三樣我們一個都沒測。七月版對 SaaS 的那句話照搬到這裡:「開始重新定價」和「定價完了」是兩回事。</p>
<h3>台積電是不是跟著費半走?</h3>
<p>價格水準上是,但時間差很有意思:費半的高點在 6 月 22 日,台積電的高點({TS['peak_date']},{TS['peak']:,.0f} 元)和加權指數的高點是同一天,比費半晚了三個半月;台積電佔加權指數權重近四成,台股的「晚熄火」基本上就是台積電的晚熄火。從七月版報告日到 11 月 6 日,台積電 {TS['ret_since_0709_pct']:+.1f}%,加權指數 {twii_0709:+.1f}%,費半 {sox_0709:+.1f}%。但「差異化反應」這件事,七月版測過:台股高低 AI 曝險股之間的差距,不是從美股夜盤傳過來的,這次延長樣本後路徑分解依然是隔夜 {R3['path']['overnight']['hl_bps']:+.0f} bps、盤中 {R3['path']['intraday']['hl_bps']:+.0f} bps,方向沒變。</p>
<h3>七月說台股沒有 AI 因子,這次大跌不就是 AI 股跌最多嗎?</h3>
<p>是的,而且資料支持這個直覺:10 月 9 日到 11 月 6 日,最高 AI 曝險組累積 {q5_oct9_nov6:+.0f}%、最低組 {q1_oct9_nov6:+.0f}%;崩盤週 Q5 {cq_[4]:+.1f}% 對 Q1 {cq_[0]:+.1f}%。但「沒有 AI 因子」說的是另一件事:從 2024 年 3 月到現在的 {R2c['n_weeks']} 個持有週,高曝險組平均每週只比低曝險組多 {R2c['hl_bps']:.0f} bps,統計上與零無異。這一輪下跌前,高曝險組在 7 月到 10 月初先多漲了 {cum_to_1002:.0f} 個百分點。所以兩件事同時為真:AI 曝險決定了這一輪誰漲得多、誰跌得深;但承擔這個曝險,到目前為止平均沒有拿到補償。前者是風險,後者是溢酬,七月版和這一版量的都是後者。</p>
<h3>這份複檢可信嗎?跟七月比改了什麼?</h3>
<p>方法、假說、證偽條件都沒改,只延長了資料。改變的是資料來源,照實列出:(1)OpenRouter 用量從 Wayback 快照改為讀該頁面的圖表 API,重疊 24 週最大差 0.43%;(2)上市股票 2026 年 7 月 10 日後的價量,因證交所端點對本執行環境回安全性封鎖頁,只有 29 個交易日有官方價量(外資買賣超只有 3 日),其餘用 Yahoo Finance 逐檔補齊,並以 7 月 9 日的官方價為基準校正 Yahoo 的除權回溯調整,並用 2025 年 11 月到 2026 年 7 月的重疊期逐筆核對收盤價(核對結果見附錄);(3)上櫃股票全部官方資料;(4)2026 年的模型發布日期取自 OpenRouter 目錄上架日,屬二手來源。程式碼與資料在同一個 GitHub 倉庫,任何人可以重跑。</p>

<p class="eyebrow">附件 · 檢測數據 APPENDIX</p>
<h2>七月版與十一月版對照</h2>
{cmp_tbl}
<h3>子期間</h3>
{sub_tbl}
<h3>誠實的限制</h3>
<ul>
<li>樣本仍只有兩年八個月,且其中兩年半是多頭;下跌只有四個月、{post_c['n_weeks']} 個交易週。子期間的任何 t 值都要用「週數」讀,{pk_c['n_weeks']} 週的子樣本只能看方向與量級,不能看顯著性。</li>
<li>檢定力天花板不變:七月版的模擬顯示,這個長度的樣本對 20 bps 級別的真溢酬只有不到 10% 的偵測率。所以主張仍是區間結論:若台股有 AI 溢酬,95% 上界約 {R2c['ci_bps'][1]:.0f} bps/週。</li>
<li>消費因子只有 token 量單腿(論文有 token、美元、用戶三腿),供給因子缺 hyperscaler 資本支出腿。token 單價下跌代表 token 腿相對美元腿被高估了成長。</li>
<li>股價未還原權息;市值用 2026 年 7 月股數快照乘當日收盤;上市股票 7 月 10 日後多數交易日無外資買賣超與成交金額(Yahoo 備援無此欄)。Yahoo 歷史價對除權、減資做過回溯調整(重疊期 118 檔比值為常數),我們以 7 月 9 日官方價為基準把每檔換回官方基準,接點日的異常報酬檔數與鄰近日同量級;副作用是這 86 檔在新期間內的除權日不再出現未還原的下跌。</li>
<li>崩盤週(11 月 2 日到 6 日)的 OpenRouter 用量資料未完整,該週不進主檢定,只以前一週 Beta 單獨列出。</li>
<li>項目 02 的基本面數字全部是公開報導的轉述,各家數字有出入處已標;沒有自建資料。</li>
</ul>
<h3>資料與來源</h3>
<ul>
<li>台股價量與法人:台灣證券交易所 MI_INDEX / T86、櫃買中心 afterTrading / insti 官方 JSON(2024-01-02 到 2026-07-09 全部官方;2026-07-13 之後上櫃全部官方、上市 29 日官方 + 其餘 Yahoo Finance <code>&lt;code&gt;.TW</code>)。</li>
<li>AI 用量:OpenRouter rankings 頁 <code>model-rankings-chart</code> 圖表資料(2026-11-08 讀取,涵蓋 2025-11-03 到 2026-11-02 各週),接上七月版的 Wayback 縫合序列。</li>
<li>美股指數:Yahoo Finance ^SOX、^GSPC、^TWII 日收盤。</li>
<li>模型發布日曆:論文 Table IA.16(到 2025-08);2026 年事件以 OpenRouter 目錄上架日為準,Claude Opus 4.8(5/28)、Claude Opus 5(7/24)、GPT-6 Astra(9/3)、Gemini 4 Argon(10/13)另有多家媒體報導佐證。</li>
<li>市場新聞歸因:<a href="https://www.schwab.com/learn/story/market-volatility">Schwab(11/5 費半 −12.2%、距高點 −32%)</a>、<a href="https://www.bloomberg.com/news/articles/2026-11-05/chips-selloff-worsens-as-fears-about-ai-trade-grip-stock-market">Bloomberg(期中選舉後 AI 交易鬆動)</a>、<a href="https://www.cnbc.com/2026/07/29/chip-selloff-sk-hynix-samsung-softbank.html">CNBC 7/29(晶片股一週蒸發一兆美元)</a>、<a href="https://www.cnbc.com/2026/10/15/sk-hynix-samsung-softbank-stocks-asia-tech-rout-ai-funding-worries.html">CNBC 10/15(AI 融資成本疑慮)</a>、<a href="https://www.cnbc.com/2026/06/26/global-tech-stocks-ai-infrastructure-costs-selloff-softbank-apple.html">CNBC 6/26(AI 基建成本)</a>、<a href="https://udn.com/news/story/7238/9862265">經濟日報(美國恐嚴管 AI)</a>、<a href="https://www.chinatimes.com/realtimenews/20261106001437-260410">中時(費半暴跌 12% 元凶)</a>、<a href="https://money.udn.com/money/story/5607/9861110">經濟日報(台股盤中史上最大跌點)</a>。</li>
<li>基本面:<a href="https://www.cnbc.com/2026/10/15/tsmc-third-quarter-profit-global-ai-.html">CNBC(台積電 Q3 連六季創高)</a>、<a href="https://www.bloomberg.com/news/articles/2026-10-08/tsmc-s-quarterly-revenue-jumps-51-after-ai-demand-holds-up">Bloomberg(台積電 Q3 營收 +51%)</a>、<a href="https://www.hl.co.uk/news/ai-hyperscalers-are-expected-to-finish-the-year-spending-a-whopping-828-billion-on-capex">Hargreaves Lansdown(四大雲端 2026 capex 約 8,280 億)</a>、<a href="https://www.globaldatacenterhub.com/p/microsoft-q3-fy2026-the-190b-capex">Global Data Center Hub(Microsoft 1,900 億 capex 口徑)</a>。</li>
</ul>

<p class="sign">ai_premium_tw 複檢單 · 2026-11-08 · 技師簽收 <b>ai_premium_tw</b> · 全部程式碼與資料:github.com/clarencechien/AIFactor(branch: claude/adoring-gates-qjkoix)· 事實帳本 FACTS.md<br>
原始論文:Borri, N., Liu, Y., &amp; Tsyvinski, A. (2026). AI Premium. arXiv:2606.30583v2 · 台股樣本:{R2c_n_stocks} 檔上市櫃普通股 × {weeks0} 到 {weeks1} · 市場新聞歸因依 Reuters、Bloomberg、CNBC、經濟日報、中時等公開報導。本報告為描述性研究,非投資建議。</p>

</main>

<script>
(() => {{
  const root = document.documentElement, btn = document.getElementById('theme-toggle');
  let dark = matchMedia('(prefers-color-scheme: dark)').matches;
  btn.textContent = 'theme · ' + (dark ? 'dark' : 'light');
  btn.addEventListener('click', () => {{
    dark = !dark; root.dataset.theme = dark ? 'dark' : 'light';
    btn.textContent = 'theme · ' + (dark ? 'dark' : 'light'); btn.setAttribute('aria-pressed', 'true');
  }});
}})();
</script>
</body>
</html>
'''
out = ROOT / 'reports/ai_premium_tw_report_2026-11.html'
out.write_text(html, encoding='utf-8')
print('wrote', out, len(html.encode('utf-8')), 'bytes')

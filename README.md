# ai_premium_tw — 台股 AI 溢酬驗證專案

複製並延伸 Borri, Liu & Tsyvinski《AI Premium》(arXiv:2606.30583v2)方法到台股。
定位:**市場定價結構的描述性研究,不是交易系統,不產生下單清單。**

📄 **完整報告(一般人可讀,含 QA 與圖表)**:`reports/ai_premium_tw_report.html`

---

## 結論(2026-07-10,真實資料定案)

**一句話:訂單流向台灣,風險定價留在美國——台股不為「AI 消費曝險」支付溢酬。**

樣本:TWSE + TPEx 共 1,994 檔普通股 × 607 交易日(2024-01 ~ 2026-07),94 個排序週。
因子:真實 OpenRouter 週 token 量(Wayback 快照縫合,112 週,跨快照重疊差異 ≤0.04%)+ SOX 對 S&P500 殘差。

| 假說 | 判定 | 關鍵數字 |
|---|---|---|
| **H1** 台股對 AI 消費因子溢酬 = 0(複製論文 EM 發現) | ✅ **成立** | VW H−L = **−0.4 bps/週**(t=−0.02),95% CI **[−41, +40]** → 點估計精確為零,且**排除論文美股的 64.1 bps**。五分位無單調性、FM λ 不顯著、動能糾纏乾淨 |
| **H2** 台股對供給端(capex)因子有正溢酬 | ❌ **未獲支持,按事前證偽條件作廢** | H−L = +16.4 bps/週(t=0.68),CI [−31, +63]。因子為降級代理(缺 hyperscaler guidance 腿),保守解讀 |
| **H3** 溢酬由外資流中介(買超集中 + 隔夜跳空傳導) | ❌ **不成立,方向相反** | 買−賣差 −15.2 bps(t=−0.56);FM 控流量後 λ 87.8→102.1 無衰減;通道拆解:隔夜 −23.5 vs **盤中 +18.5** → 微弱訊號屬本地盤中,非 ADR 傳導 |
| 事件研究(論文 IA.16 日曆,17 個前沿發布) | 🟡 弱、不顯著、走盤中 | 五日 H−L +0.28%(t=1.26;論文美股 +1.9%, t=4.17),幾乎全來自盤中(+0.36%, boot p=0.074);非前沿安慰劑 total 乾淨。異常留檔:安慰劑隔夜 −0.32%(t=−3.44),無事前假說,不入結論 |

### 論文三個 ⚠️ 查核(M0,全文 + 圖檔逐名核對)

1. **IA.6 貝氏收縮**:✅ 收縮後 H−L = 48.2 bps/週(t=2.42);bootstrap CI [27.3, 101.9]。
2. **SaaS(Table IA.5)**:✅ 全樣本 loading 0.035(≈零)→ **最後一季 −1.353(t=−2.69)**——市場開始為應用層被取代風險定價。
3. **§3.4 個股排名**:✅ 正尾 #1 AppLovin、#2 Carvana、#6 Expedia、#8 NRG;負尾 #1 Moderna、#2 雅詩蘭黛、#7 AMD(負尾滿是半導體)。

分析師貼文的 12 條論文轉述經全文核對**全數屬實**(見 `reports/analyst_claims_review.md`)。

### 方法論產出(對後續研究可能比結論更有用)

- **檢定力分析**(~2,400 次模擬):107–130 週樣本對 20 bps 級溢酬偵測率 <10%、對 64 bps 僅 38% → 單獨的「不顯著」無資訊量,**所有結論以信賴區間表述**;H1 之所以有內容,是因為 CI 排除了美股量級。
- **OpenRouter 消費因子重建法**:rankings 頁 Next.js payload 內嵌尾隨一年週頻 token 圖,4 個錯開的 Wayback 快照即可縫合全樣本(`src/build_consumption_factor.py`)。
- **資料 quirk 留檔**:TWSE rwd API 限流時會回**錯誤日期**的資料(含 2017 年);以內嵌日期覆核 + 去重防護(`src/build_panel.py`)。
- FM 中介檢定的「衰減比率」在基準 λ≈0 時爆炸,已棄用,改報 λ 水準。

### 限制(寫死,不因結果調整)

兩年半樣本、AI 多頭時期、消費因子單腿(論文三腿)、未還原權息、市值用當期股數近似、
風險補償 vs 錯誤定價無法區分。所有結論為描述性,非投資建議。

---

## 假說(事前註冊,含證偽條件)

- **H1**:台股對 AI「消費因子」的 H−L 溢酬統計上為零(複製論文 EM 發現)
- **H2**:台股對 AI「資本支出因子」有顯著正溢酬(供給端曝險假說)
- **H3**:溢酬實現由外資流中介(集中於外資買超子樣本、隔夜跳空通道)

## 結構

```
FACTS.md                    # 事實帳本:每項聲明可溯源或旗標 ⚠️
data/
  model_releases_paper_ia16.csv  # 論文 Table IA.16 日曆(19 前沿 + 28 非前沿)
  model_releases.csv             # 擴充日曆(含 2025-08 後事件,部分二手來源)
  openrouter_weekly.csv          # 消費因子原料:112 週 token 序列
  us_indices_daily.csv           # SOX / SPX / TWII
src/
  fetch_twse.py fetch_tpex.py    # 官方 API 抓取(含限流與錯誤日期防護)
  build_panel.py                 # 原始 JSON → 面板(1,994 檔 × 607 日)
  build_consumption_factor.py    # Wayback 快照縫合 token 序列
  build_factors.py rolling_beta.py
  design1_event_study.py design2_horse_race.py design3_flow_mediation.py
  synthetic.py                   # 合成資料(檢定力分析用)
  utils/tz_map.py utils/overnight_split.py
run_experiments.py          # 合成驗證套件(E1/E2/E2P/E3)
run_real_experiments.py     # 真實資料 R1/R1b/R2/R3
reports/
  ai_premium_tw_report.html      # ⭐ 三方觀點完整報告(TLDR/QA 在前、統計在後)
  real_results.json              # 真實實驗原始輸出
  experiment_report.md           # 合成驗證與檢定力分析
  M0_report.md                   # 論文查核(兩輪)
  analyst_claims_review.md       # 分析師論點逐條查核
shadow/                     # 影子模式輸出(持續累積)
```

## 重跑

```bash
pip install pandas numpy scipy statsmodels pyarrow
python src/fetch_twse.py --pause 4 --start 2024-01-01   # 官方限流,勿低於 3s
python src/fetch_tpex.py --pause 4 --start 2024-01-01
python src/build_consumption_factor.py                  # 需可達 web.archive.org
python src/build_panel.py
python run_real_experiments.py                          # → reports/real_results.json
python run_experiments.py                               # 合成驗證(選跑)
```

## 後續(視訊號與需求)

樣本每年自然增長改善檢定力;產業中性版排序(台股半導體權重極高);消費因子補美元腿;
安慰劑隔夜負值之謎(非前沿發布多為中國實驗室/開源,對齊同日宏觀事件)。

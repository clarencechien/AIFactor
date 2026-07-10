# FACTS.md — ai_premium_tw 事實帳本

> 規則:每項事實聲明須可溯源(來源 + 取得日期)或旗標為 ⚠️ 未驗證。
> 引用任何 ⚠️ 項目前,須自行取得原始來源升級為 ✅。
> 最後更新:2026-07-10(第二輪:網路開放,論文全文 v1/v2 已下載複核,M0 三項全部定案)

---

## 0. 本執行環境的網路限制(影響所有資料取得的元事實)

**更新 2026-07-10(第二輪)**:使用者已把 Claude Code web 網路政策改為 full。實測 arxiv.org / openapi.twse.com.tw / www.tpex.org.tw / openrouter.ai / archive.org 全部 200。**下表為第一輪(受限政策)的歷史記錄,保留供溯源**;第二輪起真實資料管線可執行。

**2026-07-10 第一輪實測**,本 Claude Code 遠端環境的出站網路由 agent proxy 管制,實測結果:

| 網域 | 狀態 | 影響 |
|---|---|---|
| arxiv.org(含 pdf/html/export) | ❌ CONNECT 403(政策拒絕) | 論文全文/附錄不可直接下載 |
| openapi.twse.com.tw | ❌ 403 | 台股上市價量、三大法人資料不可抓 |
| www.tpex.org.tw | ❌ 403 | 上櫃資料不可抓 |
| openrouter.ai | ❌ 403 | 消費因子原始資料不可抓 |
| archive.org(Wayback) | ❌ 403 | 歷史快照回補不可行 |
| query1.finance.yahoo.com / stooq.com / api.finmindtrade.com / huggingface.co / semanticscholar.org | ❌ 403 | 備援行情源全數不可用 |
| api.github.com | ✅ 200 | 僅限本 session 授權 repo |
| pypi.org(經 proxy 強制轉送) | ✅ | Python 套件可安裝 |
| WebSearch(Anthropic 伺服器端) | ✅ | 可取得搜尋索引摘錄,深度以索引為限(摘要層可達,附錄表格不可達) |

**結論**:M0 的三個 ⚠️ 查核只能靠 WebSearch 索引摘錄部分完成;M1–M3 的真實資料管線在本環境無法執行,改為(a)交付可重跑的抓取程式 + (b)合成資料端到端驗證 + 檢定力分析。所有「實證結論」欄位標注 `PENDING_DATA`。

---

## 1. 論文已驗證事實(✅ = 有來源可溯)

### 1.1 上游已驗證(2026-07-10 交接文件對照正文,承接自 handoff §1.2)

| 結果 | 數值 | 來源 |
|---|---|---|
| VW H−L 價差 | 64.1 bps/週 (t=2.84) | 正文 Table 3 |
| FF5+Mom alpha | 55.9 bps (t=2.41) | 正文 Table 3 |
| 控科技股/半導體/AI ETF 後 | 49.5 / 45.4 / 63.4 bps | 正文 Table 5 |
| 閉源 vs 開源 | 53.4 (t=2.47) vs 32.3 (t=1.76) | 正文 |
| 已開發 vs 新興市場 | 17.9 (t=2.77) vs 5.0 (t=0.94, 不顯著) | 正文 |
| 前沿模型發布事件研究 | 五日 H−L +1.9% (t=4.17),調整後 +1.1% (t=2.20) | 正文 |
| Agentic token 佔比 | 2024 近零 → 樣本末約一半;單價同步下跌 | 正文 §5 |
| 高 beta 組動能糾纏 | Mom 低組 0.019 → 高組 0.140(顯著) | 正文 Table 2 |
| 作者自認限制 | 「當前價格」非長期溢酬;樣本偏開發者/精明用戶 | 正文導論 |

### 1.2 M0 驗證(2026-07-10 第二輪:論文 v1+v2 全文已下載,HTML 全文 + Figure 3/4 圖檔逐一核對)

| # | 聲明 | 判定 | 證據(arXiv 2606.30583**v2**,2026-07-03) |
|---|---|---|---|
| F-01 | IA.6 Panel A:circular moving-block bootstrap 下 H−L 超額報酬 95% 區間 **[27.3, 101.9] bps/週**,排除零;FF5/FF5+Mom alpha 同樣排除零 | ✅ | v2 全文 §IA.4(Table IA.6 說明) |
| F-02 | IA.6 Panel B:empirical-Bayes 收縮 beta(收縮向 formation 週橫斷面均值)排序後,VW 全樣本斷點 H−L = **48.2 bps/週 (t=2.42)** | ✅ **升級** | v2 全文原文:"The value-weighted, all-stock-breakpoint H−L spread is 48.2 basis points per week (t=2.42)"。分析師「64→48」與「約 25% 來自噪音」(64.1→48.2 = −24.8%)**均成立** |
| F-03 | §3.4:AppLovin 為 S&P 500 最高正 AI 曝險(Figure 3 Panel A 第 1 名) | ✅ | v2 正文 + Figure 3 圖檔 |
| F-04 | §3.4:正尾含 Expedia(#6)、NRG Energy(#8);另有 Lumentum(#3)、Expand Energy、Baker Hughes、GE Vernova、Cummins 等 | ✅ | Figure 3 圖檔逐名核對 |
| F-05 | §3.4:Moderna 為最負 AI 曝險(Figure 4 Panel B 第 1 名) | ✅ | v2 正文 + Figure 4 圖檔 |
| F-06 | §3.4:Estée Lauder 負尾**第 2 名**;負尾大量半導體:ON Semi #3、Skyworks #4、Monolithic Power #6、**AMD #7**、Microchip #15、NXP #21、Qualcomm #28、TI #38 | ✅ | Figure 4 圖檔逐名核對 |
| F-07 | §3.4:Carvana 在正尾 | ✅ **升級** | **Figure 3 Panel A 第 2 名(CVNA)**。注意:名字只在圖檔內,HTML/PDF 文字搜尋不到——第一輪搜不到的原因 |
| F-08 | §3.4:AMD 被點名在負尾 | ✅ **升級** | v2 正文:"The negative tail includes Estee Lauder, as well as technology and semiconductor firms such as AMD and ON Semiconductor" |
| F-09 | SaaS:上市 SaaS 組合(SaaSDB 名單×CRSP)對 AI 因子 loading 全樣本 **0.035 (t=0.27)** ≈ 零;**最後一個日曆季 −1.353 (t=−2.69)**(每 1σ AI 衝擊的週報酬 %) | ✅ **升級** | v2 **Table IA.5**(非 IA.6)。分析師聲明完全成立 |
| F-10 | v2(2026-07-03)vs v1(2026-06-29)差異 | ✅ | 主要:新增 §3.3.4 事件研究小節標題、新增「排除發布週」穩健性論述(Table 8)、§4 改名加 Occupations、加 Pastor-Veronesi 引用;數字未見變動 |
| F-11 | 論文含職業/任務/技能層級 AI 曝險對應(§4 + Figure IA.6:109 個 SOC 職業組排名) | ✅ | v2 全文;interaction/communication +0.36σ、routine manual −0.41 等 |

### 1.2b 第二輪新增的論文事實(handoff 未記錄,對台股設計有用)

| # | 事實 | 出處 |
|---|---|---|
| N-01 | 論文事件日曆 = **19 前沿 + 28 非前沿**事件,全表在 Table IA.16,已轉存 `data/model_releases_paper_ia16.csv`。前沿日曆止於 2025-08-07 GPT-5;DeepSeek-R1 拆成 1/20 發布與 1/27 市場認知**兩個事件** | Table IA.16 |
| N-02 | 事件研究(§3.3.4):前沿發布 H−L CAR 約 **+3%**(−5 到 +10 日窗,含發布前 pre-drift,+5 日後平台);非前沿約 +1.5% 且無 pre-drift | 正文 §3.3.4, Figure 2 |
| N-03 | **排除前沿發布週後溢酬仍在**:39.5 bps/週 (t=1.96);再排除非前沿發布週 45.6 bps (t=1.77) → 溢酬非純新聞日現象,亦部分回應「事後驚喜」疑慮 | Table 8 |
| N-04 | Salient 分解完整數字:閉源 53.4 (2.47) vs 開源 32.3 (1.76);付費/核心 66.8 (2.37) vs 新用戶 21.9 (0.86);老用戶 59.3 (2.13) vs 29.3 (1.21);長 prompt 54.1 (2.40) vs 短 33.0 (1.79) | 正文 §3.3.3 |
| N-05 | 中國 A 股(Table IA.14):基線因子與中國專屬因子(中國大陸 OpenRouter 消費建構)排序,H−L **一致為負且不顯著**(VW/EW 皆然)→ 分析師「中國甚至是負的」成立(負但不顯著) | Table IA.14 |
| N-06 | Agentic 佔比精確值:樣本末最後完整週 **52.2%**;tool-call 與 cache-read 各升至總 token 的 2/5–1/2;agentic 子因子點估 +0.3~0.5%/週但不精確(「早期證據」) | 正文 §5 |
| N-07 | 產業曝險(Figure IA.5):FF10 中 retail 與 consumer durables 最正;**nondurables 與 health 唯二為負**;高科技產業整體只有中度曝險(半導體/AI 基建強正被其他科技股負曝險抵消) | Appendix IA.5 |
| N-08 | 國際樣本:Compustat Global,MSCI DM/EM 分組,美元市值/價格濾網,本幣報酬;AI ETF 籃 = BOTZ/AIQ/IRBO/ROBO/ARTY/WTAI/CHAT 等權 | 正文 §2.2 |
| N-09 | 職業/技能:AI 曝險正在 nonroutine interactive(interaction/communication 0.36, t=4.21),負在 nonroutine analytical/math(−0.15, t=−3.41)與 routine manual(−0.41);正尾職業:安裝維修/程式/說服/教學/系統整合;負尾:科學/醫療/操作控制 | 正文 §4 |
| N-10 | 因子建構細節:PC1 權重 0.665/0.559/0.496、解釋 56.5%(handoff 既有);另有 salient 子因子(模型層/用戶強度/任期/prompt 長度/內容類別/agentic)可各自建因子 | 正文 §2 |

### 1.3 M0 判定總結(對 handoff §1.3 三個 ⚠️)— **三項全部定案**

1. **貝氏收縮 64→48**:✅ **完全成立**。IA.6 Panel B = 48.2 bps (t=2.42);Panel A block bootstrap CI [27.3, 101.9]。
2. **SaaS loading 最後一季轉負**:✅ **完全成立**(在 Table IA.5,非 IA.6):全樣本 0.035 (t=0.27) → 最後一季 −1.353 (t=−2.69)。
3. **§3.4 個股排名**:✅ **完全成立**:正尾 AppLovin #1、Carvana #2、Expedia #6、NRG #8;負尾 Moderna #1、雅詩蘭黛 #2、AMD #7。分析師貼文此三點的轉述全部準確。

---

## 2. 台股專案自建資料的事實狀態

| 項目 | 狀態 | 備註 |
|---|---|---|
| `data/model_releases_paper_ia16.csv`(19 前沿 + 28 非前沿) | ✅ 論文轉存 | 逐字轉自 v2 Table IA.16;Design 1 主規格用此 |
| `data/model_releases.csv`(38 事件,knowledge-base 版) | ⚠️ 保留為擴充日曆 | 與論文日曆重疊處日期偏差 ≤1 天(如 Claude 3.5 Sonnet 我方 06-20 vs 論文 06-21);含論文日曆沒有的 2025-08 後事件(Gemini 3、Opus 4.5、GPT-5.1),作延伸樣本穩健性用,URL 仍未逐一回連 |
| 台股價量/法人資料(TWSE+TPEx) | 🔄 抓取中 | 2026-07-10 網路開放後啟動,2024-01-02 起日頻,officially sourced。TWSE 對 2.5s 間隔觸發 307 限流,以 4s 間隔補洞 |
| OpenRouter 週頻 token 序列 | ✅ **已建成** | `data/openrouter_weekly.csv`:112 週(2024-03-04 ~ 2026-04-20),4 個 Wayback 快照的內嵌年度圖縫合。品質:51 個重疊週跨快照相對差中位數 0.00%、最大 0.04%;總成長 1179x 與論文「11.4B→15.6T(1368x,起點早兩月)」相容。**限制**:(a) 2024-01~02 缺頭(當時頁面版式只有請求數圖);(b) 2026-05 起頁面改版純 client-side,序列止於 2026-04(= 論文樣本終點);(c) 只有 token 單腿,無美元/用戶腿 |
| 台股交易日曆 2024–2026 | ⚠️ 近似 | 實際交易日以抓到的 TWSE 資料日期為準(自我修正);tz_map 假日表僅作事件映射輔助 |
| Hyperscaler capex guidance 逐季數字 | ❌ 未建 | M3 需要;capex 因子先用 SOX 殘差單腿 |

## 3. 實驗結論的事實狀態(2026-07-10)

| 假說 | 真實資料結論 | 管線驗證結論(合成資料,詳 reports/experiment_report.md) |
|---|---|---|
| H1 消費因子在台股溢酬=0 | PENDING_DATA | ⚠️ **檢定力不足是硬結論**:130 週下,EM 量級(≈20 bps)power <10%、論文 DM 量級(64 bps)power 38%(降級因子 29%)。H1 已建議改寫為區間估計;「不顯著」不得解讀為支持 H1 |
| H2 capex 因子有正溢酬 | PENDING_DATA | 賽馬程式驗證通過(size 正確);同樣受 power 天花板限制,H2 證據應主要依賴 Design 1 事件研究 |
| H3 外資流中介 | PENDING_DATA | 雙重排序方向可回收(中介情境下溢酬正確集中於買超格);FM 衰減比率指標不穩定已棄用;正式版改 5×2 排序 |
| Design 1 事件研究管線 | PENDING_DATA | ✅ 驗證通過:虛無無假陽性(boot p=0.88)、注入可回收、隔夜/盤中拆解正確辨識傳導比例(78/22 對注入 80/20)、安慰劑乾淨 |
| beta 估計噪音衰減 | — | 64 bps 注入平均回收 33.6 bps(衰減 ~48%,corr(β̂,β)≈0.6 校準下);與論文 IA.6 收縮方向一致、比其隱含的 25% 更悲觀 |

**鐵律重申**:合成資料驗證的是「程式與檢定的正確性」,不是任何市場事實。任何對外溝通不得把管線驗證數字當成台股實證結果。

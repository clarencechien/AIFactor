# FACTS.md — ai_premium_tw 事實帳本

> 規則:每項事實聲明須可溯源(來源 + 取得日期)或旗標為 ⚠️ 未驗證。
> 引用任何 ⚠️ 項目前,須自行取得原始來源升級為 ✅。
> 最後更新:2026-07-10(M0 完成)

---

## 0. 本執行環境的網路限制(影響所有資料取得的元事實)

**2026-07-10 實測**,本 Claude Code 遠端環境的出站網路由 agent proxy 管制,實測結果:

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

### 1.2 M0 本次新驗證(2026-07-10,WebSearch 對 arXiv 索引之摘錄;無法直接開啟全文)

| # | 聲明 | 判定 | 證據 |
|---|---|---|---|
| F-01 | 附錄 IA.6:以 empirical-Bayes 收縮後的 AI beta 排序,溢酬**仍為正**;同表含 block-bootstrap 推論下結果亦成立 | ✅(方向) | WebSearch 摘錄原文:"Online Appendix Table IA.6 shows that the result remains positive under block-bootstrap inference and when sorting on empirical-Bayes-shrunk AI betas" |
| F-02 | IA.6 收縮後溢酬具體數字 = **48 bps**(即 64→48) | ⚠️ 未驗證 | 索引不含附錄表格數字。48 bps 之說僅見於分析師貼文,**不得引用為論文事實** |
| F-03 | §3.4:AppLovin 為 S&P 500 中估計 AI 曝險**最高**者 | ✅ | WebSearch 摘錄:"AppLovin … has the highest estimated positive AI exposure among current S&P 500 firms" |
| F-04 | §3.4:正尾包含數位平台/旅遊(Expedia)與電力(NRG Energy) | ✅ | WebSearch 摘錄:"The positive tail includes digital-platform and travel firms such as Expedia, and power firms such as NRG Energy" |
| F-05 | §3.4:Moderna 為估計 AI 曝險**最負**者 | ✅ | WebSearch 摘錄:"Moderna … has the most negative estimated AI exposure" |
| F-06 | §3.4:Estée Lauder 在負尾;負尾**含半導體公司** | ✅ | WebSearch 摘錄:"Estée Lauder is in the negative tail of AI beta exposure, along with semiconductor firms" |
| F-07 | §3.4:Carvana 在正尾名單 | ⚠️ 未驗證 | 多次定向搜尋未命中;不得引用 |
| F-08 | §3.4:AMD 被點名在負尾 | ⚠️ 未驗證 | 「半導體公司在負尾」已證(F-06),但 AMD 未被索引點名;分析師貼文點名 AMD,引用時應寫「負尾含半導體公司(F-06);AMD 之說未經核對」 |
| F-09 | 附錄:上市 SaaS 組合對 AI 因子 loading 全樣本近零、最後一季轉顯著負 | ⚠️ 未驗證 | 附錄不可達,索引無此內容。此為分析師貼文最有投資含義的聲明,**目前唯一來源是貼文本身** |
| F-10 | 論文已出 **v2**(arxiv.org/html/2606.30583v2 出現於搜尋結果);handoff 引用 v1 | ✅(存在) | v1/v2 差異未知 ⚠️;數字引用時應標注版本 |
| F-11 | 論文含職業/任務層級的 AI 曝險對應(occupation-level and task-level impacts, mapping market-priced AI risk to workers and skills) | ✅ | WebSearch 摘錄(handoff 未提及此節,對台股勞動曝險延伸可能有用) |

### 1.3 M0 判定總結(對 handoff §1.3 三個 ⚠️)

1. **貝氏收縮 64→48**:升級為「**方向 ✅ / 數字 ⚠️**」。IA.6 確認收縮後仍正,且同表含 block bootstrap;「48」這個數字核對不到。
2. **SaaS loading 最後一季轉負**:**維持 ⚠️**。本環境到不了附錄;此聲明目前只能溯源到分析師貼文。
3. **§3.4 個股排名**:**大幅升級**。最正 AppLovin ✅、正尾 Expedia/NRG ✅、最負 Moderna ✅、負尾雅詩蘭黛+半導體 ✅;Carvana ⚠️、AMD 點名 ⚠️。

**升級路徑(網路開放後 10 分鐘可完成)**:`curl -L https://arxiv.org/pdf/2606.30583v2 -o paper.pdf && pdftotext paper.pdf`,搜 "IA.6"、"SaaS"、"Carvana"、"Advanced Micro"。

---

## 2. 台股專案自建資料的事實狀態

| 項目 | 狀態 | 備註 |
|---|---|---|
| `data/model_releases.csv`(38 事件,2024-01~2026-01) | ⚠️ 知識庫建構 | 日期/名稱來自模型知識(截止 2026-01),每列附官方 source_url 但**未逐一回連驗證**(網路擋);2026-02~04 有缺口旗標 |
| 台股價量/法人資料 | ❌ PENDING_DATA | 抓取程式已交付(src/fetch_twse.py, fetch_tpex.py),本環境不可執行 |
| OpenRouter 週頻 token 序列 | ❌ PENDING_DATA | src/fetch_openrouter_wayback.py 已交付 |
| 台股交易日曆 2024–2026 | ⚠️ 近似 | utils/tz_map.py 內嵌國定假日表(知識庫),需以 TWSE 官方行事曆覆核 |
| Hyperscaler capex guidance 逐季數字 | ❌ 未建 | M3 才需要;需財報電話會逐字稿 |

## 3. 實驗結論的事實狀態(2026-07-10)

| 假說 | 真實資料結論 | 管線驗證結論(合成資料,詳 reports/experiment_report.md) |
|---|---|---|
| H1 消費因子在台股溢酬=0 | PENDING_DATA | ⚠️ **檢定力不足是硬結論**:130 週下,EM 量級(≈20 bps)power <10%、論文 DM 量級(64 bps)power 38%(降級因子 29%)。H1 已建議改寫為區間估計;「不顯著」不得解讀為支持 H1 |
| H2 capex 因子有正溢酬 | PENDING_DATA | 賽馬程式驗證通過(size 正確);同樣受 power 天花板限制,H2 證據應主要依賴 Design 1 事件研究 |
| H3 外資流中介 | PENDING_DATA | 雙重排序方向可回收(中介情境下溢酬正確集中於買超格);FM 衰減比率指標不穩定已棄用;正式版改 5×2 排序 |
| Design 1 事件研究管線 | PENDING_DATA | ✅ 驗證通過:虛無無假陽性(boot p=0.88)、注入可回收、隔夜/盤中拆解正確辨識傳導比例(78/22 對注入 80/20)、安慰劑乾淨 |
| beta 估計噪音衰減 | — | 64 bps 注入平均回收 33.6 bps(衰減 ~48%,corr(β̂,β)≈0.6 校準下);與論文 IA.6 收縮方向一致、比其隱含的 25% 更悲觀 |

**鐵律重申**:合成資料驗證的是「程式與檢定的正確性」,不是任何市場事實。任何對外溝通不得把管線驗證數字當成台股實證結果。

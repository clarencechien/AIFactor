# M0 報告 — 論文 ⚠️ 項目查核(2026-07-10)

## 執行摘要

- 本環境網路政策封鎖 arxiv.org(含 PDF/HTML/export 鏡像、HuggingFace、alphaXiv、Semantic Scholar),**論文全文與附錄無法直接下載**。查核改以 WebSearch(Anthropic 伺服器端,可達)對 arXiv 索引做定向抽取,共 7 次查詢。
- 三個 ⚠️ 的判定:**§3.4 個股排名大幅升級 ✅**、**IA.6 方向升級 ✅ 但數字維持 ⚠️**、**SaaS 表維持 ⚠️**。
- 發現論文已有 **v2**(handoff 引 v1),差異未知。
- 詳細證據與逐條判定見 `FACTS.md` §1.2–1.3。

## 三個 ⚠️ 的實際查核內容

### 1. 附錄 IA.6 貝氏收縮
索引可及的原文片段:

> "Online Appendix Table IA.6 shows that the result remains positive under block-bootstrap inference and when sorting on empirical-Bayes-shrunk AI betas."

- 可確認:IA.6 存在、內容是 **empirical-Bayes 收縮 beta 排序 + block-bootstrap 推論**,兩者下溢酬**仍為正**。
- 不可確認:分析師貼文說的「64→48 bps、25% 訊號來自噪音」——具體數字在附錄表格內,索引抓不到。**「48 bps」目前唯一來源是分析師貼文,引用須註明。**

### 2. SaaS loading 表
定向搜尋(SaaS/software-as-a-service + loading + negative + subsample)全部未命中論文內容。**無法驗證**「全樣本近零、最後一季轉顯著負」。此聲明現階段只能溯源到分析師貼文,已在 FACTS.md 記為 F-09 ⚠️。

### 3. §3.4 個股 AI 曝險排名
索引可及的原文片段拼出以下已驗證事實:

| 聲明 | 判定 |
|---|---|
| AppLovin = S&P 500 最高正 AI 曝險 | ✅ |
| 正尾含數位平台/旅遊(Expedia)、電力(NRG Energy) | ✅ |
| Moderna = 最負 AI 曝險 | ✅ |
| 負尾含 Estée Lauder 與半導體公司 | ✅ |
| Carvana 在正尾 | ⚠️ 未命中 |
| AMD 被點名在負尾 | ⚠️ 未點名(僅「半導體公司」被確認) |

## 網路開放後的補完清單(10 分鐘)

```bash
curl -L https://arxiv.org/pdf/2606.30583v2 -o paper.pdf
pdftotext -layout paper.pdf paper.txt
grep -n -A20 "IA.6" paper.txt        # 收縮後 bps 數字
grep -n -B2 -A10 "SaaS\|software-as-a-service" paper.txt
grep -n -B2 -A30 "AppLovin" paper.txt  # §3.4 完整表 + Carvana/AMD
diff <(curl -sL https://arxiv.org/abs/2606.30583v1) <(curl -sL https://arxiv.org/abs/2606.30583v2)  # v1/v2 差異
```

---

# 第二輪補完(2026-07-10,網路開放後)

使用者將 Claude Code web 網路政策改為 full,論文 v1/v2 全文(HTML)與 Figure 3/4 圖檔已下載複核。**三個 ⚠️ 全部定案為 ✅**:

| 項目 | 定案 | 實際內容 |
|---|---|---|
| IA.6 貝氏收縮 | ✅ | Panel B:收縮 beta 排序 H−L = **48.2 bps/週 (t=2.42)**(64.1→48.2 = −24.8%)。Panel A:block bootstrap 95% CI **[27.3, 101.9] bps**,排除零 |
| SaaS loading | ✅(在 **Table IA.5**) | 全樣本 **0.035 (t=0.27)** ≈ 零;最後一個日曆季 **−1.353 (t=−2.69)**(每 1σ AI 衝擊,%/週)。SaaS 名單 = SaaSDB 上市公司 × CRSP |
| §3.4 排名 | ✅(Figure 3/4 圖檔逐名核對) | 正尾:**#1 AppLovin、#2 Carvana**、#3 Lumentum、#6 Expedia、#8 NRG;負尾:**#1 Moderna、#2 雅詩蘭黛**、#3 ON Semi、#4 Skyworks、**#7 AMD**(負尾滿是半導體:Microchip #15、NXP #21、Qualcomm #28、TI #38) |

方法論教訓:第一輪 Carvana 搜不到的原因是**名單只存在於圖檔內**,全文文字搜尋(HTML 與 PDF)都不會命中——「搜尋不到」不等於「不存在」。

v1→v2 差異:新增 §3.3.4 事件研究小節與 Table 8「排除發布週」穩健性(排除前沿發布週後 H−L 仍 39.5 bps, t=1.96),§4 改名含 Occupations,無數字變動。

額外收穫:論文事件日曆 Table IA.16(19 前沿 + 28 非前沿)已轉存 `data/model_releases_paper_ia16.csv`,Design 1 改用論文日曆為主規格。

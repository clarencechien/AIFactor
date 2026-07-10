# ai_premium_tw — 台股 AI 溢酬驗證專案

複製並延伸 Borri, Liu & Tsyvinski《AI Premium》(arXiv:2606.30583)方法到台股。
定位:**市場定價結構的描述性研究,不是交易系統,不產生下單清單。**

## 假說

- **H1**:台股對 AI「消費因子」的 H−L 溢酬統計上為零(複製論文 EM 發現)
- **H2**:台股對 AI「資本支出因子」有顯著正溢酬(供給端曝險假說)
- **H3**:溢酬實現由外資流中介(集中於外資買超子樣本、隔夜跳空通道)

證偽條件寫死於 handoff 文件,不因結果調整。

## 目前狀態(2026-07-10)

- **M0 完成**:論文三個 ⚠️ 查核見 `FACTS.md` §1.2–1.3 與 `reports/M0_report.md`
- **M1–M3 管線完成並以合成資料驗證**:本執行環境網路政策封鎖所有行情/論文資料源
  (詳 `FACTS.md` §0),真實資料結論全部 `PENDING_DATA`
- 實驗結果:`reports/experiment_report.md`(檢定力分析為本階段最重要產出)
- 分析師貼文論點查核:`reports/analyst_claims_review.md`

## 結構

```
FACTS.md                    # 事實帳本:每項聲明可溯源或旗標 ⚠️
data/model_releases.csv     # 38 個模型發布事件(2024-01~2026-01,kb_unverified)
src/
  fetch_twse.py fetch_tpex.py fetch_openrouter_wayback.py   # 真實資料抓取(需開放網路)
  build_factors.py          # 消費因子(降級單腿)+ capex 因子
  rolling_beta.py           # 13 週滾動 AI beta(min 9 週,無前視,向量化)
  design1_event_study.py    # 事件研究 + 隔夜/盤中拆解 + 安慰劑
  design2_horse_race.py     # 雙因子賽馬 + FM + 動能糾纏
  design3_flow_mediation.py # 外資流雙重排序 + 中介 FM + 路徑分解
  synthetic.py              # 合成資料產生器(管線驗證/檢定力專用)
  utils/tz_map.py           # 美國發布日 → 台股 T+1(假日表為近似,需覆核)
  utils/overnight_split.py  # 隔夜/盤中報酬拆解
run_experiments.py          # 全實驗執行器
reports/                    # M0 報告、實驗報告、分析師論點查核
shadow/                     # 影子模式輸出(取得真實資料後啟用)
```

## 網路開放後的重啟順序

1. `reports/M0_report.md` 末段的補完清單(10 分鐘,升級 FACTS ⚠️)
2. `python src/fetch_twse.py --start 2024-01-01` / `fetch_tpex.py`(各約半天,含限速)
3. 核對 `data/model_releases.csv` 的 source_url 與 2026-02~04 缺口
4. `python src/fetch_openrouter_wayback.py`(M3 才需要)
5. 以真實資料重跑 `run_experiments.py` 的 Design 1 → 3 → 2 順序(handoff §6)

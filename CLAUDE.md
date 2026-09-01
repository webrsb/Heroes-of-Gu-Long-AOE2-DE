# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 這是什麼專案

把 AoC 1.21z 社群 RPG 劇情檔「古龍921 新負血劍譜5」（5232 觸發）遷移到 AoE2 DE。
不是一般軟體專案：產物是 `.aoe2scenario` 劇情檔，工具是 Python 腳本，
「測試」指的是使用者親自進遊戲跑最小重現檔並回報結果。
所有文件與溝通使用繁體中文。

## 鐵律（違反會毀掉工作成果）

1. **使用者說「開始修」之前，絕不修改本體劇情檔。** 驗證、稽核、產測試檔都可以，動本體不行。
2. **絕不覆寫任何來源檔。** 修復一律另存新檔（後綴遞進，如 `..._attackfix` → `..._attackfix_boss`），每一步保留前一版。
3. **絕不從 DE 編輯器存檔** —— 編輯器存檔會把負值/溢位值正規化，破壞刻意寫入的數值。所有寫入都走 AoE2ScenarioParser。
4. **測試走 單人 → 劇情**，不用編輯器測試模式。
5. **每個測試檔必須帶陽性對照組**（positive control）——「沒反應」才能區分是機制失效還是測試檔本身壞掉。
6. 只顧 DE 相容性，不用管 AoC（使用者已確認 DE-only）。

## 檔案佈局

**F:\aoe2de 整個目錄就是 git repo**（2026-08-29 由 src/ 內移到最外層）。工作檔都在 `src/`：

- `src/origin/` — 乾淨基底，**絕不覆寫**
  - `古龍921_新負血劍譜5.aoe2scenario` — utf8 轉檔後的主要遷移標的
  - `古龍921_無法無天.aoe2scenario` — 較新的分支版本（超集：+267 觸發、八仙地圖等）
- `src/新負血劍譜/` — 新負血劍譜5 的全部工作檔：
  - `古龍921_DE遷移記錄.md` — **施工權威**。專屬 ref 編號、修法定案、歷史教訓。**第七部分＝施工計畫**
  - `verify/` — 驗證證據索引（`00_INDEX.md` + 38 篇實測記錄），追查「規格怎麼驗出來的」才回頭翻
  - `audit.py`、`audit_buildings.py` — 唯讀稽核；`fix_attack.py` — 攻擊力修復（另存 `_attackfix` 後綴）
  - `attack_fix_report.tsv` — 473 效果修復明細
  - `scan_aok_tricks.py`、`make_verify_docs.py`、`backfill_verify_results.py`、`update_rules.py`、`update_rules2.py` — 已完成任務的一次性腳本，僅留檔備查
  - 施工產物（`..._attackfix.aoe2scenario` 等）放這一層
- `src/無法無天/` — 無法無天分支的工作檔（尚未開工，空）
- `src/AoC_to_DE_migration_guide.md` — 通用 AoC→DE 參考：引擎數值模型、攻擊力重編碼公式、
  技巧存活表、稽核與測試方法論。單一事實只存這裡，遷移記錄以指針引用。遷移**其他**地圖從這份開始
- `F:\aoe2de\aoe_t\AocScenarioTranslator.exe`（在 src 外層，純工具）— Big5 `.scx` → utf8 轉碼（遷移舊圖的第一步）
- `src/compare_two.py` — 兩個劇情檔差異比較
- 遊戲部署路徑：`C:\Users\Ricky\Games\Age of Empires 2 DE\76561198023399153\resources\_common\scenario\`
  （把 `.aoe2scenario` 複製進去，遊戲內 單人→劇情 就看得到）

## 常用指令

```
python src/新負血劍譜/audit.py <scenario.aoe2scenario>       # 唯讀稽核，輸出對帳報表
python src/新負血劍譜/audit_buildings.py <scenario>          # 建築物血量盤點（含區域目標解析）
python src/新負血劍譜/fix_attack.py [--dry-run]              # 修 473 個攻擊力效果
```

需要 `pip install AoE2ScenarioParser`（目前 0.8.4）。腳本內建的預設路徑是 src 改組前的舊路徑，
已失效——**一律用參數傳入實際路徑**。

寫檔前務必設定 `trigger_manager.legacy_execution_order = True`，否則 DE 會重排觸發執行順序。

**合併管線的靜態關卡（2026-08-31 起）**：`src/合併/build.py` 末端有兩道，任一失敗即中止、不出檔：
- `s90 終檢`：全檔通用不變量（攻擊力編碼／trigger_id 超界／dangling ref／觸發數對帳／空效果殼／
  **字型缺字**）。缺字那條：DE 的 CJK 走預烘點陣字圖集（只有 5510 個漢字）、清單外**不 fallback
  直接開天窗**，所以玩家看得到的文字用了覆蓋表外的字即中止，要回頭補
  `params.glyph_fixes` 的換字裁決（施作 `s85_glyph`，裁決表產生器 `tools/gen_glyph_fixes.py`，
  報告 `reports/字型缺字裁決.md`）。覆蓋表優先讀遊戲目錄，讀不到退回版控快照
  `analysis/de_font_coverage.txt`（遊戲更新後 `python -m analysis.font_check --snapshot` 重產）。
  **新寫對白時**：罕用字會被這道擋下來，別繞過它——改用覆蓋表內的字，或補裁決。
- `s91 結構不變量`：**本次施工的結構契約**。`merge_spec.yaml` 每個 `kind: trigger_add` 都必須宣告
  `key: seat|class|global`（座位鍵／職業鍵-shared／全域），s91 拿實際變體數對帳（seat 5、其餘 0）；
  另檢查「帶座位的觸發啟停邊必須指同座位那支」、「同 tick 攔截順序（id 較小才攔得住零條件目標）」、
  「傳送／任務目的格不得落在傳送來源區內」，以及各功能的特徵斷言（`analysis/ferry_check.py`）。
  報告項（不擋建置）寫在 `logs/91_結構不變量.tsv`：我方新增格子落在原作玩家區域條件內（A）、
  基底既有的攔截形狀（O）、Change HP 超 int16（H）、座位覆蓋不齊（S）。
  新增功能時「S新增」那類要自己看——座位沒補齊是最常見的漏。

## 架構重點（跨檔案才看得懂的部分）

- **AoE2ScenarioParser 讀不了 AoC `.scx`**。流程必是：Big5 `.scx` → AocScenarioTranslator 轉 utf8 →
  DE 遊戲內轉檔成 `.aoe2scenario` → parser 才接手。轉檔後若聊天訊息數 == 0 代表 Big5 文字全滅，檔案作廢。
- **效果目標解析有三種模式**：`selected_object_ids`、區域+玩家+object_list 過濾、什麼都不填（全圖）。
  任何稽核腳本三種都要解析，只掃 `selected_object_ids` 會漏掉兩百多個效果（歷史教訓，見 `audit_buildings.py` 的 `targets()`）。
- **資源即貨幣**：石頭＝經驗值、黃金＝銀兩、木材＝技能點。經驗/銀兩的唯一給予途徑是
  「玩家對 Gaia 負進貢」×473 處（DE 實測有效）。
- 引擎數值模型（int16 最大血量 mod 65536、攻擊力 class×65536+amount 重編碼、雙0血解除夾血、
  `-1` 哨兵逐效果而異…）全部在 `src/AoC_to_DE_migration_guide.md` §2–§4，改數值前先讀。

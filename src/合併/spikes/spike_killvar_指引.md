# SPIKE擊殺變數 —— 以 DE 變數重建 Kill Ratio（2026-08-30）

前情：`spike_killratio` 證實 `Modify Resource` 對屬性 44 無效（唯讀），死亡扣 KR 無法補償。
本 spike 改用**屬性 20（純擊殺數，不受死亡影響）＋變數**重建「擊殺增量、可歸零」語意：

| 法 | 條件 | 領獎後 |
|---|---|---|
| A 比較變數 | `V_K > V_BASE_A`（V_K 每 tick ← 屬性20） | `V_BASE_A ← 屬性20` |
| B 差值 | `V_DIFF ≥ 1`（V_DIFF 每 tick ← 屬性20 − V_BASE_B） | `V_BASE_B ← 屬性20` |

已部署 `SPIKE擊殺變數.aoe2scenario`。操作同前：騎士殺不還手民兵；t40 己方村民被殺。

## 判讀

| 觀察 | 結論 |
|---|---|
| 每殺 1 隻恰出 [RA] 1 行 | A 法可用（`Compare Variables`＋`Modify Variable by Resource` 皆有效） |
| 每殺 1 隻恰出 [RB] 1 行 | B 法可用（`Variable Value`＋`Modify Variable by Variable` 有效） |
| 某法刷屏 | 該法的 base 寫回無效 |
| 某法從未出現（[P1] 有） | 該法條件/變數讀取無效 |
| [D] 後擊殺仍各出 1 行 | **死亡不影響**——回歸修法成立 |

兩法皆可時取 A（效果較少）。

## 結果

（待填）

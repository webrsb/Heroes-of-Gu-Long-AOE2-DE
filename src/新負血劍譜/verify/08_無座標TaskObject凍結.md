# 08 — `Task Object` 不給座標＝凍結，在 DE 還有效嗎  【P0】

**狀態**：✅ **已測・有效** —— 本體寫法在 DE 照常凍結，59 處不必改
（測的是 `ZZ_test08b`；初版 `ZZ_test08` 有缺陷已作廢，見下）

> **初版 `ZZ_test08` 作廢。** 它靠「侵略姿態 + 8 格外誘餌」誘使騎士移動，
> 但騎士視野只有 4 格，看不到 8 格外的誘餌 —— 陽性對照組 B 也不會動，
> 三條都會顯示「仍在原地」，測不出任何東西。
> `ZZ_test08b` 改用**確定性移動命令**：第 5／25 秒對三隻騎士各下一次
> 「Task Object 到 (8, y)」，22 格外的明確命令，與視野無關。
> 誘餌一併移到 3 格外（視野內）當次要觀察。
>
> **判讀前必看：B 必須跑掉，否則測試無效。**

重現檔 `ZZ_test08b_無座標TaskObject凍結`（約 40 秒）

## 問題

AoKH FAQ 的凍結技巧：

> *"Freeze Trade Carts: Use looping trigger with Task Object effect on trade
> cart, but do not place a Location."*
> *"Freeze Kings Method 1: Use Task Object effect without placing Location.
> King becomes completely immobile."*

本體 **59 處**符合此寫法，**全部在循環觸發器裡**：

```
1軍 ~ 6軍        1木2 ~ 6木2        1南僧 ~ 6南僧        怪改
```

`Task Object` 共 571 個，其中 59 個 `location_x = location_y = -1`。

作者用它固定 NPC 位置 —— 軍隊列陣、僧侶站位。
**若 DE 忽略無座標的指派，這些單位會全部開始亂跑，場面全毀。**

## 測試設計

三條並排，P2 騎士都在 `x=30`，P1 誘餌在 `x=22`（8 格外），騎士為**侵略姿態**
（有理由衝過去）：

| lane | 手法 |
|---|---|
| **A** | 循環觸發器 + 無座標 `Task Object`（**完全照本體寫法**） |
| B | 完全不處理（對照，**應該衝向誘餌**） |
| C | `Freeze Object`（DE 正規做法，對照） |

用 `objects_in_area` 檢查 15 秒／35 秒時是否還在原地 3×3 框內。

## 判讀

| 觀察 | 結論 | 動作 |
|---|---|---|
| A 兩次都「仍在原地」 | 寫法在 DE 仍有效 | **不必改** |
| A 出現「已離開原地」 | **DE 已忽略無座標指派** | **59 處全需改寫成 `Freeze Object`** |
| B 沒有離開原地 | 測試無效（騎士根本不想動） | 需重新設計誘餌距離／姿態 |
| C 沒有留在原地 | `Freeze Object` 也不管用 | 需另尋替代 |

## 結果

**2026-08-29 實測（`ZZ_test08b`）：**

| 車道 | 手法 | 15s / 35s | 判定 |
|---|---|---|---|
| **A** | 循環 + 無座標 `Task Object`（本體寫法） | **仍在原地** | ✅ 凍結成立 |
| **B** | 完全不處理（陽性對照） | 已離開原地 | ✅ 測試有效 |
| **C** | `Freeze Object`（DE 正規做法） | **已離開原地** | ❌ **擋不住命令** |

### 結論一：本體寫法有效

B 跑掉 → 移動命令確實有下達、測試成立；A 兩次都在原地 →
**DE 完整保留「Task Object 不給座標 = 凍結」的語意。本體 59 處不必改。**

機制上也說得通：A 的凍結不是靠「凍結」旗標，而是**循環觸發器每個 tick
重下一次無座標指派**，任何外來命令下一幀就被覆蓋掉。

### 結論二：`Freeze Object` 擋不住 `Task Object`（意外發現）

C 被 `Freeze Object` 凍結後，第 5 秒的 `Task Object` 命令照樣讓它走掉。
`Freeze Object` 只封鎖**玩家操作與單位自身 AI**，
**不封鎖觸發器的 `Task Object` 效果**。

→ 這反而證明本體那套寫法比 DE 的正規 Freeze **更牢固**。
→ **不要**把本體的 59 處「改良」成 `Freeze Object`，那是降級。
→ 日後若需要真正定住單位，正解是循環無座標 `Task Object`，不是 `Freeze Object`。

規則書：§2.8a ①

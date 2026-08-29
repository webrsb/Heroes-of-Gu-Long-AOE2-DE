# -*- coding: utf-8 -*-
"""
update_rules2.py —— 把 AoKH FAQ 反向盤點的結果寫進規則書與 verify 文件
"""
import io
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

RULES = r"F:\aoe2de\古龍921_DE遷移記錄.md"
VDIR = r"F:\aoe2de\verify"
NL = chr(10)

# ======================================================================
# 1. 規則書：新增第二部分之八
# ======================================================================
SECTION = '''
---

## 第二部分之八：AoC 技巧清單反向盤點（2026-08-29）

> 來源：[AoK Heaven — Scenario Design FAQ](https://aok.heavengames.com/cgi-bin/forums/display.cgi?action=st&fn=4&tn=37500)
> （論壇 4 / 主題 37500，AoC 時代的技巧問答總表）
>
> 做法：把 FAQ 列出的每一項技巧當成檢查清單，用 `scan_aok_tricks.py`
> 反向掃描本體，確認「哪些真的在用」而不是憑猜測。
> 這比逐條讀觸發器可靠 —— 技巧的**特徵值**（魔數、無座標、負值）都可程式化辨識。

### 2.8a 🔴 本體確實在用、且有 DE 風險的四項

| FAQ 技巧 | 本體用量 | 風險 | 驗證檔 |
|---|---|---|---|
| **`Task Object` 不給座標 = 凍結** | **59 處，全部在循環觸發器**：`1軍`~`6軍`、`1木2`~`6木2`、`1南僧`~`6南僧`、`怪改` | 🔴 **高** | `ZZ_test08` |
| **玩家向 Gaia 進貢負資源** | **473 處**，`sp=1~6` → `tp=0`，資源為石頭與黃金 | 🔴 **最高** | `ZZ_test09` |
| **`Kill Ratio`（屬性 44）當擊殺計數** | **268 處** | 🟡 中 | `ZZ_test10` |
| **建立後立刻擊殺做爆炸** | `Furious the Monkey Boy`(860) 建立 15、`Hawk`(96) 建立 12 | 🟢 低 | — |

**① 無座標 `Task Object`**

> FAQ：*"Freeze Trade Carts: Use looping trigger with Task Object effect on
> trade cart, but do not place a Location."*
> *"Freeze Kings Method 1: Use Task Object effect without placing Location.
> King becomes completely immobile."*

作者用它固定 NPC 位置（軍隊列陣、僧侶站位）。
**若 DE 忽略無座標的指派，這 59 處的單位會全部開始亂跑**，場面全毀。
替代寫法是 DE 的 `Freeze Object`（`ZZ_test08` 的 C 條就是對照）。

**② 負進貢 —— 本次風險最高的一項**

> FAQ：*"Give Resources Without GAIA tributed to message: Have player tribute
> negative resources to Gaia instead of Gaia tributing positive to player."*

`quantity` 為負、`source_player = 玩家`、`target_player = 0 (Gaia)`
→ 玩家**獲得**資源，且不會跳出「GAIA tributed to」提示。

**這是本戰役經驗值（石頭）與銀兩（黃金）的唯一給予途徑。**
DE 若把負進貢夾成 0 或直接拒絕，**整個成長系統歸零** —— 而且不會報錯，
只是玩家永遠拿不到獎勵。473 處，改寫成本極高。

**③ `Kill Ratio`**

> FAQ：*"Reward Players for Each Kill: Condition Accumulate Attribute
> (1 Kill Ratio) + Tribute + Create Object + Remove Object.
> Trigger looping: Yes. Resets kill ratio after each reward."*

`Kill Ratio = 擊殺數 − 損失數`。要驗的除了條件本身，還有
**FAQ 的「建立後移除物件」重置法在 DE 是否仍能讓計數歸零**。

### 2.8b ✅ 確認**未使用**的技巧（不必測，也不必擔心）

| FAQ 技巧 | 掃描結果 |
|---|---|
| `Unload` 用在陸上單位 → 滑行 | **0** |
| `Patrol` 取代 `Task Object` → 隊形行走 | **0** |
| 英雄式自動回血（`16777216 − MaxHP` 魔數） | **0**（與 §2.6 一致） |
| `Object Selected` 條件（告示牌、旅店對話） | **0** |
| `AI Signal` 條件 / `AI Script Goal` / `Acknowledge AI Signal` | 各 **0** |
| 駐紮技巧（`garrisoned_in_id`、`Create Garrisoned Object`） | 各 **0** |
| `Place Foundation`（窗透光夜景） | **0** |
| 目標清單技巧（不可能條件 + 遞減 String 編號） | **0**（顯示旗標全 0，見 §5.6d） |
| 高程 10 / 16（需外部工具） | 最高只到 **6** |

### 2.8c 🔑 「不用負號」的溢位寫法 —— 這解釋了 `修1` 的 bug

> FAQ **Invincible Units Without Minus Sign**（70 血冠軍步兵）：
> ```
> Effect1: Change object HP 65466      (65536 − 70)
> Effect2: Damage object 4294967226    (4294967296 − 70)
> Effect3: Change object HP 70
> Effect4: Damage object 70
> ```

**AoC 編輯器無法輸入負號**（FAQ 另有一節專講：只能從訊息框或觸發器名稱複製貼上），
所以社群的標準變通寫法是：

```
想要 -N（最大血量，int16 欄位）  ->  填 65536 − N
想要 -N（當前血量，int32 欄位）  ->  填 4294967296 − N
```

**這正是本規則書 §1.2 那些 `65536 − A` 寫法的來源**，
也是為什麼 `operation` 必須是 ADD 才有意義（§1.2c）。

**關鍵限制：`4294967296 − N` 只在 N ≤ 2147483648 時有效。**
超過就會落回正數區間，公式**靜默失效**。

本體有兩個實例，一成一敗：

| 位置 | 作者填入（推算） | DE 讀到 | 結果 |
|---|---|---|---|
| `[4951] 馬` eff[24] | `4294967296 − 1,100,000,000 = 3,194,967,296` | **−1,100,000,000** | ✅ 成功（在範圍內） |
| `[5230] 修1` eff[19] | 想要 **−3,000,000,000** → 填 `1,294,967,296` | **+1,294,967,296** | ❌ **公式失效**，變成正傷害 |

→ **作者公式套對了，是目標值超出 int32 下限（−2147483648）導致的。**
→ **AoC 也是同樣的 int32 欄位 → 原作者 bug，不是 DE 迴歸。**

### 2.8d ⚠️ `修1` 的嚴重度下修（更正 §4.3）

`[5230] 修1` 的完整脈絡：

```
條件：PLAYER_DEFEATED  source_player = 1      ← P1 被擊敗才觸發
looping = True
效果：7 個 Change Diplomacy → 3 個 Remove Object（P1）
      → Change Object HP 95536（= 65536 + 30000，回繞為 +30000）
      → Change Object Attack 31073
      → Damage Object 1294967296   ← 就是這個
      → Change Object HP −7000、Attack 2000、Attack 30000
```

這是一個**落敗後的收尾／重置**觸發器（`修` 前綴的一族還有 `修端慕草1~6`）。
那個回繞 bug 在**玩家已經落敗之後**的路徑上執行，**實務上打不到人**。

→ 先前 §4.3 寫「會全圖秒殺 P1 所有東西」機制上正確，但**嚴重度標高了**，已下修。

### 2.8e 📌 更正：`−1,100,000,000` 不在魔王身上

`[4951] 馬` 共 42 個效果，其中兩組容易混淆：

```
eff[ 6]  DAMAGE  sp=7  qty=-6,000,000        sel=[38862]  ← 亡魂之堡（§1.2m 正確）
eff[23]  CHG_HP  sp=0  qty=-33               sel=[42868]
eff[24]  DAMAGE  sp=0  qty=-1,100,000,000    sel=[42868]  ← 另一個 Gaia 物件
```

**魔王仍是 −6,000,000**，§1.2m 無誤。
`−11 億`是掛在 **Gaia 的 42868** 上的另一組爆血（先 `−33` 壓最大血量、再灌 11 億），
是本檔案中**規模最大的爆血**，也是 §2.8c 那個公式最成功的一次應用。

同一觸發器另有兩處**無過濾**（全圖）的爆血，已計入 §4.5b：

```
eff[ 9]  DAMAGE  sp=7  qty=-2,005,880   sel=[]   ← P7 全圖
eff[20]  CHG_HP  sp=8  qty=-290         sel=[]   ← P8 全圖
eff[21]  DAMAGE  sp=8  qty=-105,100     sel=[]   ← P8 全圖
```

### 2.8f 🟡 `Change View` 全部貼地圖邊緣

> FAQ：*"Change View Crash: Changing view over large distances or near map
> edge crashes game. Use multiple Change View effects over distance;
> avoid map edges."*

本體 **20 個 `Change View` 效果，全部**座標貼邊（≤3 或 ≥236，地圖 240）：

```
[4636] 2p   (0,0)      [4637] 2p2  (239,239)   [4638] 2p3  (239,0)
[4641] 3p   (0,0)      [4642] 3p2  (239,239)   [4643] 3p3  (239,0)
[4646] 4p   (0,0)      [4647] 4p2  (239,239)   [4648] 4p3  (239,0)
[4639] 2p4  (1,237)    [4644] 3p4  (1,235)     [4649] 4p4  (0,235)
```

命名（`2p` / `3p` / `4p`）看起來是**多人遊戲的玩家起始視角設定**。
**這是 AoC 時代就存在的當機風險，不是 DE 造成的**，但 DE 行為需確認。
`(0,0)` 與 `(239,239)` 是地圖的正對角，同時觸及「長距離」與「貼邊」兩個條件。

### 2.8g 🟡 未知物件 ID 是 **45 個**，不只 817

```
37 94 95 163 164 165 166 169 171 172 176 177 196 197 200 208
424 426 428 430 432 436 573 629 640 644 648 650 652 680 686
698 700 704 706 707 731 781 783 817 840 842 845 847 852
```

AoE2ScenarioParser 的資料集只收錄 1355 個物件、**本身不完整**，
所以多數可能有效 —— 但 `07b` / `07c` 只驗了 817，**涵蓋率 1/45**。

FAQ 提到 AoC 有一批 beta / eye-candy 單位（`TWAL`、`Port`、`Camel Scout`、
`POREX`、`OREMN`），**DE 多已移除**，所以這 45 個必須逐個確認。
`ZZ_test07d` 每秒生成一個、**生成前先報 ID**，當掉時最後一行就是兇手。

其他值得記的物件用量：

| ID | 用量 | 推測 |
|---|---|---|
| 837 | 已放置 42、觸發器建立 **165** | `Map Revealer`（FAQ 的視野／夜景技巧） |
| 816 | 建立 92 / 擊殺移除 19，`source_player = 0` | Gaia 物件，`1轅`~`6轅` 用它做效果 |
| 720 | 建立 138 | — |
| 860 | 建立 15 / 擊殺 3 | `Furious the Monkey Boy` —— FAQ 的爆炸技巧 |
| 96 | 建立 12 / 擊殺移除 22 | `Hawk` —— FAQ 的爆炸技巧 |

'''

# ======================================================================
# 2. verify 文件
# ======================================================================
DOCS = {

'08_無座標TaskObject凍結.md': '''# 08 — `Task Object` 不給座標＝凍結，在 DE 還有效嗎  【P0】

**狀態**：🔲 **待測** —— 重現檔 `ZZ_test08_無座標TaskObject凍結`（約 40 秒）

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

（待填）

規則書：§2.8a ①
''',

'09_負進貢給資源.md': '''# 09 — 玩家向 Gaia 進貢負資源，在 DE 還有效嗎  【P0・風險最高】

**狀態**：🔲 **待測** —— 重現檔 `ZZ_test09_負進貢給資源`（約 30 秒）

## 問題

AoKH FAQ：

> *"Give Resources Without GAIA tributed to message: Have player tribute
> negative resources to Gaia instead of Gaia tributing positive to player."*

`quantity` 為負、`source_player = 玩家`、`target_player = 0 (Gaia)`
→ 玩家**獲得**資源，而且不會跳出「GAIA tributed to」提示訊息。

本體 **473 處**，全部是 `sp = 1~6` → `tp = 0`，資源為**石頭**與**黃金**：

```
[3]  1打民團    石頭 -2   黃金 -2
[27] 1打山賊    石頭 -2   黃金 -5
...
```

依作者的資源用法：**石頭 = 經驗值、黃金 = 銀兩、木材 = 技能點**。

## 為何這是風險最高的一項

**這是本戰役經驗值與銀兩的唯一給予途徑。**

DE 若把負進貢夾成 0 或直接拒絕執行：

- **整個成長系統歸零** —— 打怪不再給經驗、不再給銀兩
- **不會報任何錯** —— 只是玩家永遠拿不到獎勵，靜默失效
- 473 處要改寫，成本極高（且需逐一確認正負號語意）

## 測試設計

P1 四種資源起始**全部歸零**，逐步施加：

| 秒 | 動作 |
|---|---|
| 3 | P1 → Gaia 石頭 **−50** |
| 6 | P1 → Gaia 石頭 **−50**（第二次，測累加） |
| 9 | P1 → Gaia 黃金 **−200** |
| 12 | P1 → Gaia 黃金 **−5**（本體常見的小額） |
| 15 | P1 → Gaia 食物 **−30** |
| 18 | **對照**：Gaia → P1 木材 **+77**（傳統做法，會有提示） |

用 `Accumulate Attribute` 門檻回報，也可直接看畫面上方的資源數字。

## 判讀

| 觀察 | 結論 | 動作 |
|---|---|---|
| 回報「石頭 >= 50」與「>= 100」 | 負進貢有效且可累加 | **不必改** |
| 完全沒回報、資源一直是 0 | **DE 已封殺此寫法** | **473 處全需改寫** |
| 只有木材 +77 到手 | 只剩傳統做法可用 | 同上，且會多出進貢提示訊息 |
| 小額 −5 沒生效但 −200 有 | 有下限或四捨五入 | 需逐一檢查小額用例 |

順便觀察：**負進貢時畫面上有沒有出現進貢提示訊息**
（FAQ 用這招正是為了消除提示；若 DE 現在會顯示，體感會被大量提示轟炸）。

## 結果

（待填）

規則書：§2.8a ②
''',

'10_KillRatio計數.md': '''# 10 — `Kill Ratio` 當擊殺計數，在 DE 還有效嗎  【P1】

**狀態**：🔲 **待測** —— 重現檔 `ZZ_test10_KillRatio計數`（約 40 秒）

## 問題

AoKH FAQ 的每殺一隻給獎勵：

> ```
> Condition0: Accumulate Attribute (1 Kill Ratio: Player 1)
> Effect0: Tribute (10 Gold: GAIA -> Player 1)
> Effect1: Create Object - any unit at hidden location
> Effect2: Remove Object - unit just created
> Trigger looping: Yes. Resets kill ratio after each reward.
> ```

本體 **268 處**使用 `Kill Ratio`（屬性 44）。
`Kill Ratio = 擊殺數 − 損失數`。

`Accumulate Attribute` 條件的屬性分布：

| 屬性 | 數量 | 意義 |
|---|---|---|
| 2 | 620 | 石頭（經驗值） |
| **44** | **268** | **Kill Ratio** |
| 1 | 216 | 木材（技能點） |
| 3 | 107 | 黃金（銀兩） |
| 0 | 6 | 食物 |
| 43 | 1 | Razings |

## 三個要驗的問題

| # | 問題 |
|---|---|
| Q1 | 條件在 DE 是否仍成立？ |
| Q2 | 是否會隨擊殺數累加（>=1、>=2、>=3 依序成立）？ |
| Q3 | FAQ 的「建立+移除物件」重置法在 DE 還需要／還有效嗎？ |

## 測試設計

P1 騎士自動去殺 5 個 P2 村民（已設原地防守，不會逃）。

- 五個非循環觸發器，門檻 `Kill Ratio >= 1~5`，各自回報
- 一個**循環**觸發器完全照 FAQ 寫法：`Kill Ratio >= 1` → 黃金 +10
  → 建立綿羊 → 移除綿羊
- 用黃金累積量反推重置是否有效（10 / 30 / 50 三個門檻）

## 判讀

| 觀察 | 結論 |
|---|---|
| 依序出現「Kill Ratio 已達 1..5」 | 條件正常且會累加 |
| 完全不出現 | **268 處全部失效** |
| 黃金累加到 30 以上 | FAQ 的重置寫法在 DE 仍有效 |
| 黃金停在 10 | 重置無效（計數不歸零，只給一次獎） |

⚠️ 本檔的黃金是用**負進貢**給的，所以同時是 **09 的交叉驗證** ——
若 09 失效，本檔的黃金門檻也不會回報，判讀時要先確認 09 的結果。

## 結果

（待填）

規則書：§2.8a ③
''',
}

# 07 文件追加 07d 說明
DOC07_APPEND = '''
---

## 追加：未知 ID 其實有 **45 個**（2026-08-29）

**狀態**：🔲 **待測** —— 重現檔 `ZZ_test07d_未知ID全驗`（約 55 秒）

`scan_aok_tricks.py` 全面掃描後發現，本體用到的 **209 種物件**中，
有 **45 個**不在 AoE2ScenarioParser 的資料集內，不只 817：

```
37 94 95 163 164 165 166 169 171 172 176 177 196 197 200 208
424 426 428 430 432 436 573 629 640 644 648 650 652 680 686
698 700 704 706 707 731 781 783 817 840 842 845 847 852
```

→ **`07b` / `07c` 只驗了 817，涵蓋率 1/45。**

資料集只收錄 1355 個物件、本身不完整，所以多數可能有效，
但 AoKH FAQ 提到 AoC 有一批 beta / eye-candy 單位
（`TWAL`、`Port`、`Camel Scout`、`POREX`、`OREMN`），**DE 多已移除**，
因此必須逐個確認。

### `07d` 的設計要點

**每個 ID 生成前先發一則聊天訊息報出 ID** ——
若某個 ID 讓遊戲當掉，聊天欄最後一行就是兇手。

- 每秒生成一個，排成 5 列（45 秒）
- 第 50 秒用 `own_objects` 逐個驗證 P1 是否真的擁有

| 觀察 | 結論 |
|---|---|
| 出現「[有效] ID xxx」 | 該 ID 在 DE 可用 |
| 只有「[生成]」沒有「[有效]」 | 該 ID 無效，需替換 |
| 遊戲當掉 | 最後一行的 ID 就是兇手 |

也請看一下地圖上這些東西長什麼樣（有無隱形／錯圖）。

### 順帶記錄的物件用量

| ID | 用量 | 推測 |
|---|---|---|
| 837 | 已放置 42、觸發器建立 **165** | `Map Revealer` |
| 816 | 建立 92 / 擊殺移除 19（`sp=0` Gaia） | `1轅`~`6轅` 用它做效果 |
| 720 | 建立 138 | — |
| 860 | 建立 15 / 擊殺 3 | `Furious the Monkey Boy`（FAQ 的爆炸技巧） |
| 96 | 建立 12 / 擊殺移除 22 | `Hawk`（FAQ 的爆炸技巧） |

規則書：§2.8g
'''


def main():
    n = 0
    s = io.open(RULES, encoding='utf-8').read()

    if '第二部分之八' in s:
        print("  skip 規則書（已有第二部分之八）")
    else:
        anchor = NL + '## 第三部分：DE 轉檔造成的資料變形'
        assert anchor in s
        s = s.replace(anchor, SECTION + anchor.lstrip(NL), 1)
        n += 1
        print("  ok  規則書新增 §2.8（反向盤點）")

    # 修1 嚴重度下修
    old = '''  - 作者想寫 **−30 億**（全圖回血），但超出 int32 範圍（min −2147483648）回繞成
    **正 12.9 億傷害**，會全圖秒殺 P1 所有東西'''
    new = '''  - 作者想寫 **−30 億**（全圖回血），但超出 int32 範圍（min −2147483648）回繞成
    **正 12.9 億傷害**，機制上會全圖秒殺 P1 所有東西
  - ⚠️ **嚴重度已下修**：該觸發器的條件是 `PLAYER_DEFEATED sp=1`，
    即**玩家已落敗之後**才執行，實務上打不到人。詳見 **2.8d**
  - 作者的公式其實套對了（`4294967296 − N`，見 **2.8c**），
    是目標值 −30 億超出 int32 下限導致公式靜默失效'''
    if old in s:
        s = s.replace(old, new, 1)
        n += 1
        print("  ok  §4.3 修1 嚴重度下修")
    else:
        print("  skip §4.3（已下修或格式不符）")

    s = s.replace(
        '*最後更新：2026-08-29（新增 4.5 條件型別盤點、4.5a/4.5b 明細、修1 回繞 bug、',
        '*最後更新：2026-08-29（新增 2.8 AoC 技巧清單反向盤點、'
        '4.5 條件型別盤點、4.5a/4.5b 明細、修1 回繞 bug、')

    io.open(RULES, 'w', encoding='utf-8', newline=NL).write(s)

    # verify 文件
    for name, body in DOCS.items():
        p = os.path.join(VDIR, name)
        if os.path.exists(p):
            print(f"  skip {name}")
            continue
        io.open(p, 'w', encoding='utf-8', newline=NL).write(body)
        print(f"  new  {name}")
        n += 1

    p07 = os.path.join(VDIR, '07_未知物件與科技ID.md')
    s7 = io.open(p07, encoding='utf-8').read()
    if '45 個' in s7:
        print("  skip 07 文件（已追加）")
    else:
        s7 = s7.rstrip() + NL * 2 + DOC07_APPEND.lstrip(NL)
        s7 = s7.replace(
            '**狀態**：🔲 **待測** —— 重現檔 `ZZ_test07b_未知ID` + '
            '`ZZ_test07c_817實體`（各 20 秒）',
            '**狀態**：🔲 **待測** —— 重現檔 `ZZ_test07b_未知ID`、'
            '`ZZ_test07c_817實體`（各 20 秒）、`ZZ_test07d_未知ID全驗`（55 秒）')
        io.open(p07, 'w', encoding='utf-8', newline=NL).write(s7)
        print("  ok  07 文件追加 07d")
        n += 1

    print(f"{NL}共 {n} 處更新")


if __name__ == '__main__':
    main()

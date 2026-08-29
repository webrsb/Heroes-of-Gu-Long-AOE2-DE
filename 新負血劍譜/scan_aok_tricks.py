# -*- coding: utf-8 -*-
"""
scan_aok_tricks.py —— 依 AoKH「Scenario Design FAQ」反向檢查本體用了哪些特殊技巧

來源：https://aok.heavengames.com/cgi-bin/forums/display.cgi?action=st&fn=4&tn=37500
      （AoK Heaven 論壇 4 / 主題 37500，AoC 時代的技巧問答總表）

只掃**靜態可檢測**的項目。地圖層面的技巧（隱形懸崖、可行走建築、無岸水域…）
無法從觸發器與單位資料判定，另列於報告末尾。

執行：python scan_aok_tricks.py
"""
import collections
import sys

sys.stdout.reconfigure(encoding='utf-8')

from AoE2ScenarioParser.scenarios.aoe2_de_scenario import AoE2DEScenario

SRC = (r"F:\aoe2de\src"
       r"\- 古龍 ９２１ 新負血劍譜５ -utf8_attackfix.aoe2scenario")

# ---- 效果 ID ----
TRIBUTE, AI_GOAL, CREATE, TASK, KILL, REMOVE = 5, 10, 11, 12, 14, 15
CHANGE_VIEW, UNLOAD, CHOWN, PATROL = 16, 17, 18, 19
PLACE_FOUNDATION, STOP, HEAL = 25, 29, 34
CHANGE_HP, DAMAGE, ACK_AI, GARRISON = 27, 24, 50, 49
# ---- 條件 ID ----
C_OBJ_SELECTED, C_AI_SIGNAL, C_ACCUM = 11, 12, 8
# ---- 屬性 ----
A_KILL_RATIO = 44

# 作弊偵測常用的單位（AoC 秘技單位）
CHEAT_UNITS = {748: 'Cobra Car', 860: 'Furious the Monkey Boy',
               96: 'Hawk', 65: 'Deer', 1103: 'Fire Galley?'}
# 爆炸常用單位
BOOM_UNITS = {118: 'Petard?', 860: 'Furious the Monkey Boy',
              96: 'Hawk', 860: 'Furious', 1010: 'Macaw?'}
REVEALER = 837          # Map Revealer

INT32_MIN = -2147483648
POW31 = 2147483648
HERO_REGEN = 16777216   # 英雄式回血的魔數


def main():
    sc = AoE2DEScenario.from_file(SRC)
    tm, um, mm = sc.trigger_manager, sc.unit_manager, sc.map_manager
    tri = tm.triggers
    ec = collections.Counter()
    for t in tri:
        for e in t.effects:
            ec[e.effect_type] += 1

    def hdr(n, title):
        print()
        print("=" * 74)
        print(f"{n}  {title}")
        print("=" * 74)

    print(f"標的：{SRC}")
    print(f"觸發器 {len(tri)}　效果 {sum(ec.values())}　"
          f"條件 {sum(len(t.conditions) for t in tri)}")

    # ------------------------------------------------------------------
    hdr('01', '「不用負號」的溢位寫法（Damage / ChangeHP 的極端值）')
    print("FAQ：Damage object 4294967226 (=4294967296-70) 在 int32 讀為 -70。")
    print("     Zombie Gaia units 用 Damage Object 2147483648。")
    print("     這是 AoC 編輯器無法輸入負號的變通寫法。\n")
    rows = []
    for i, t in enumerate(tri):
        for e in t.effects:
            if e.effect_type not in (DAMAGE, CHANGE_HP):
                continue
            q = e.quantity
            if q is None:
                continue
            if q == INT32_MIN or q == POW31 or abs(q) >= POW31 // 2:
                rows.append((i, t.name, 'DAMAGE' if e.effect_type == DAMAGE
                             else 'CHG_HP', q))
    print(f"符合（|值| >= 2^30）：{len(rows)} 處")
    for r in sorted(rows, key=lambda x: -abs(x[3]))[:20]:
        q = r[3]
        note = ''
        if q == INT32_MIN:
            note = '= -2^31（FAQ 的 zombie Gaia 寫法）'
        elif q > 0:
            note = f'正值！int32 不回繞 -> 實際造成 {q:,} 傷害'
        print(f"  [{r[0]}] {r[1][:14]!r:18} {r[2]:7} {q:>14,}  {note}")

    # ------------------------------------------------------------------
    hdr('02', '英雄式自動回血（16777216 魔數）')
    print("FAQ：Damage Object -1 / -(16777216-MaxHP) / +(16777216-MaxHP)")
    print("     利用 float32 的 ULP：在 2^24 附近 +1 會被吃掉，形成緩慢回血。\n")
    hits = []
    for i, t in enumerate(tri):
        for e in t.effects:
            if e.effect_type != DAMAGE or e.quantity is None:
                continue
            if abs(abs(e.quantity) - HERO_REGEN) < 5000:
                hits.append((i, t.name, e.quantity))
    print(f"符合（|值| 落在 16777216 ± 5000）：{len(hits)} 處")
    for h in hits[:20]:
        print(f"  [{h[0]}] {h[1][:20]!r:24} qty={h[2]:,}")
    if not hits:
        print("  -> 本戰役**未使用**此技巧（與規則書 §2.6 一致）")

    # ------------------------------------------------------------------
    hdr('03', '滑行單位：對陸上單位用 Unload')
    print("FAQ：Unload 效果本為船隻卸載而設，用在陸上單位會造成滑行。")
    print("     DE 風險：DE 對 Unload 的目標合法性檢查較嚴。\n")
    print(f"UNLOAD 效果使用數：{ec[UNLOAD]}")
    if ec[UNLOAD]:
        for i, t in enumerate(tri):
            for e in t.effects:
                if e.effect_type == UNLOAD:
                    print(f"  [{i}] {t.name[:20]!r} sp={e.source_player} "
                          f"loc=({e.location_x},{e.location_y}) "
                          f"sel={e.selected_object_ids}")
    else:
        print("  -> **未使用**")

    # ------------------------------------------------------------------
    hdr('04', '凍結單位：Task Object 不給座標')
    print("FAQ：Task Object 效果不設 Location，單位會完全不動")
    print("     （用來凍結商隊、國王）。DE 風險：DE 可能忽略無座標的指派。\n")
    noloc = []
    for i, t in enumerate(tri):
        for e in t.effects:
            if e.effect_type != TASK:
                continue
            if (e.location_x in (-1, None)) and (e.location_y in (-1, None)):
                noloc.append((i, t.name, bool(t.looping)))
    print(f"TASK_OBJECT 總數 {ec[TASK]}，其中**無座標** {len(noloc)} 處")
    for r in noloc[:20]:
        print(f"  [{r[0]}] {r[1][:24]!r:28} looping={r[2]}")
    if not noloc:
        print("  -> **未使用**凍結寫法")

    # ------------------------------------------------------------------
    hdr('05', '隊形行走：Patrol 取代 Task Object')
    print(f"PATROL 效果使用數：{ec[PATROL]}")
    print("  -> **未使用**" if not ec[PATROL] else "")

    # ------------------------------------------------------------------
    hdr('06', '無提示給資源：玩家向 Gaia 進貢負資源')
    print("FAQ：Gaia 給玩家正資源會出現「GAIA tributed to」提示；")
    print("     改成玩家向 Gaia 進貢**負**資源就沒有提示。\n")
    negtrib = []
    for i, t in enumerate(tri):
        for e in t.effects:
            if e.effect_type != TRIBUTE or e.quantity is None:
                continue
            if e.quantity < 0:
                negtrib.append((i, t.name, e.quantity, e.source_player,
                                e.target_player, e.tribute_list))
    print(f"TRIBUTE 總數 {ec[TRIBUTE]}，其中**負值** {len(negtrib)} 處")
    for r in negtrib[:15]:
        print(f"  [{r[0]}] {r[1][:16]!r:20} qty={r[2]:>8} "
              f"sp={r[3]} tp={r[4]} res={r[5]}")
    if not negtrib:
        print("  -> 未使用負進貢")

    # ------------------------------------------------------------------
    hdr('07', '擊殺計數：Accumulate Attribute + Kill Ratio')
    print("FAQ：用 Kill Ratio 條件配合建立/移除物件來重置計數，實現每殺一隻給獎勵。\n")
    kr = []
    accum_attrs = collections.Counter()
    for i, t in enumerate(tri):
        for c in t.conditions:
            if c.condition_type != C_ACCUM:
                continue
            accum_attrs[c.attribute] += 1
            if c.attribute == A_KILL_RATIO:
                kr.append((i, t.name, c.quantity, c.source_player))
    print(f"ACCUMULATE_ATTRIBUTE 條件的屬性分布（前 12）：")
    for a, n in accum_attrs.most_common(12):
        print(f"    屬性 {a:>4} : {n}")
    print(f"\nKill Ratio（屬性 44）使用數：{len(kr)}")
    for r in kr[:10]:
        print(f"  [{r[0]}] {r[1][:20]!r:24} qty={r[2]} sp={r[3]}")
    if not kr:
        print("  -> **未使用** Kill Ratio")

    # ------------------------------------------------------------------
    hdr('08', '爆炸效果：建立後立刻擊殺（爆破手／猴子／老鷹／投射物）')
    created = collections.Counter()
    killed_types = collections.Counter()
    for t in tri:
        for e in t.effects:
            if e.effect_type == CREATE and e.object_list_unit_id not in (-1, None):
                created[e.object_list_unit_id] += 1
            if e.effect_type in (KILL, REMOVE) and \
                    e.object_list_unit_id not in (-1, None):
                killed_types[e.object_list_unit_id] += 1
    both = {k: (created[k], killed_types[k]) for k in created
            if k in killed_types}
    print(f"CREATE_OBJECT {ec[CREATE]} 個，涉及 {len(created)} 種物件")
    print(f"KILL/REMOVE 指定型別的 {len(killed_types)} 種")
    print(f"**同一型別既建立又擊殺／移除**：{len(both)} 種")
    for k, (a, b) in sorted(both.items(), key=lambda x: -x[1][0])[:15]:
        print(f"    物件 {k:>5} : 建立 {a:>3} / 擊殺移除 {b:>3}")

    # ------------------------------------------------------------------
    hdr('09', '秘技單位／beta 單位／未知 ID')
    print("FAQ：作弊偵測用 Own Objects > Hawk / Deer / Furious / Cobra Car；")
    print("     beta 單位（TWAL / Port / Camel Scout / POREX / OREMN）在 DE 多已移除。\n")
    from AoE2ScenarioParser.datasets.units import UnitInfo
    from AoE2ScenarioParser.datasets.buildings import BuildingInfo
    from AoE2ScenarioParser.datasets.other import OtherInfo
    known = set()
    for ds in (UnitInfo, BuildingInfo, OtherInfo):
        for m in ds:
            known.add(m.ID)
    placed = collections.Counter()
    for pnum, plist in enumerate(um.units):
        for u in plist:
            placed[u.unit_const] += 1
    used = set(placed) | set(created) | set(killed_types)
    for t in tri:
        for c in t.conditions:
            if c.object_list not in (-1, None):
                used.add(c.object_list)
    unknown = sorted(u for u in used if u not in known)
    print(f"本體用到的物件 ID：{len(used)} 種，**不在 parser 資料集內**：{unknown}")
    for u in unknown:
        print(f"    ID {u}: 已放置 {placed.get(u, 0)} 個、"
              f"觸發器建立 {created.get(u, 0)} 處")
    print(f"\nMap Revealer（{REVEALER}）已放置：{placed.get(REVEALER, 0)} 個")
    for uid, name in CHEAT_UNITS.items():
        n = placed.get(uid, 0) + created.get(uid, 0)
        if n:
            print(f"    秘技單位候選 {uid} ({name}): {n}")

    # ------------------------------------------------------------------
    hdr('10', '目標清單技巧：不可能條件 + String 編號')
    print("FAQ：Display As Objective + 不可能成立的條件 + 遞減的 String 編號")
    print("     可在目標下方做出「物品清單」。DE 的 description_order 對應此欄位。\n")
    disp = [(i, t) for i, t in enumerate(tri)
            if t.display_on_screen or t.display_as_objective]
    print(f"有顯示旗標的觸發器：{len(disp)} 個")
    orders = collections.Counter(t.description_order for t in tri)
    nz = {k: v for k, v in orders.items() if k not in (0, None)}
    print(f"description_order 非 0 的觸發器：{len(nz)} 種值 {nz}")
    if not disp:
        print("  -> **未使用**此技巧（作者全靠 Send Chat 與 Display Instructions）")

    # ------------------------------------------------------------------
    hdr('11', '已棄用條件：Object Selected / AI Signal')
    print("FAQ 用 Object Selected 做告示牌、旅店對話；AI Signal 做難度分支。")
    cc = collections.Counter()
    for t in tri:
        for c in t.conditions:
            cc[c.condition_type] += 1
    print(f"  Object Selected (11) : {cc[C_OBJ_SELECTED]}   "
          f"（DE 已棄用）")
    print(f"  AI Signal (12)       : {cc[C_AI_SIGNAL]}")
    print(f"  AI_SCRIPT_GOAL 效果  : {ec[AI_GOAL]}")
    print(f"  ACKNOWLEDGE_AI_SIGNAL: {ec[ACK_AI]}   （DE 已棄用）")

    # ------------------------------------------------------------------
    hdr('12', 'Change View：長距離／近地圖邊緣會當掉')
    print("FAQ：跨大距離或靠近地圖邊緣的 Change View 會讓遊戲當掉，")
    print("     須拆成多段。DE 已較穩定，但值得盤點。\n")
    edge = []
    for i, t in enumerate(tri):
        for e in t.effects:
            if e.effect_type != CHANGE_VIEW:
                continue
            x, y = e.location_x, e.location_y
            if x is None or x < 0:
                continue
            if x <= 3 or y <= 3 or x >= mm.map_size - 4 or y >= mm.map_size - 4:
                edge.append((i, t.name, x, y))
    print(f"CHANGE_VIEW 效果：{ec[CHANGE_VIEW]} 個，"
          f"其中座標貼邊（≤3 或 ≥{mm.map_size - 4}）：{len(edge)}")
    for r in edge[:12]:
        print(f"  [{r[0]}] {r[1][:20]!r:24} ({r[2]},{r[3]})")

    # ------------------------------------------------------------------
    hdr('13', 'Gaia（P0）物件的建立／移除')
    print("FAQ：對 Gaia 的 Other 分頁單位做建立/移除，效果一旦重新開啟就會歸零；")
    print("     Gaia 的動物、英雄、建築則正常。\n")
    gaia = [(i, t.name, e.effect_type, e.object_list_unit_id)
            for i, t in enumerate(tri) for e in t.effects
            if e.effect_type in (CREATE, REMOVE, KILL) and e.source_player == 0]
    print(f"source_player = 0（Gaia）的 建立/移除/擊殺 效果：{len(gaia)} 處")
    for r in gaia[:15]:
        nm = {CREATE: 'CREATE', REMOVE: 'REMOVE', KILL: 'KILL'}[r[2]]
        print(f"  [{r[0]}] {r[1][:20]!r:24} {nm:7} obj={r[3]}")

    # ------------------------------------------------------------------
    hdr('14', '駐紮技巧：garrison / Create Garrisoned Object')
    ing = sum(1 for plist in um.units for u in plist
              if u.garrisoned_in_id not in (-1, None))
    print(f"  garrisoned_in_id 非 -1 的單位：{ing}")
    print(f"  CREATE_GARRISONED_OBJECT 效果：{ec[GARRISON]}")
    print(f"  PLACE_FOUNDATION 效果：{ec[PLACE_FOUNDATION]}"
          f"　（FAQ 的「窗透光」夜景技巧會用到）")
    print(f"  STOP_OBJECT 效果：{ec[STOP]}")
    print(f"  HEAL_OBJECT 效果：{ec[HEAL]}")

    # ------------------------------------------------------------------
    hdr('15', '地圖層面（靜態無法判定，僅列出可觀察的數字）')
    print(f"  地圖大小：{mm.map_size}"
          f"　（FAQ 的標準尺寸 72/96/120/144/200/255；240 是自訂）")
    elev = collections.Counter()
    for tile in mm.terrain:
        elev[tile.elevation] += 1
    print(f"  高程分布：{dict(sorted(elev.items()))}")
    print("    -> FAQ 的高程 10 / 16 技巧需要外部工具，"
          "本體高程若 ≤ 7 即未使用")
    print("  以下技巧**無法靜態檢測**，須進遊戲確認：")
    for s in ("隱形懸崖 / 可行走懸崖（FAQ 自述：存檔重載後就失效）",
              "可行走建築（同上，存檔即失效）",
              "可行走水域（橋樑中段建後移除）",
              "無岸水域、高處可航行水域、瀑布",
              "隱形農田",
              "牆角無旗標"):
        print(f"    - {s}")


if __name__ == '__main__':
    main()

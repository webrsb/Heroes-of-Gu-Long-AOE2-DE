# -*- coding: utf-8 -*-
"""
古龍921 — AoC→DE 升級稽核腳本（唯讀，不修改任何檔案）

依據 古龍921_DE遷移記錄.md 的公式，重跑一次對帳並輸出報表。
用法:
    python audit.py [scenario.aoe2scenario]

需要: pip install AoE2ScenarioParser
"""
import sys, os
from collections import Counter, defaultdict

sys.stdout.reconfigure(encoding='utf-8')

from AoE2ScenarioParser.scenarios.aoe2_de_scenario import AoE2DEScenario
from AoE2ScenarioParser.datasets.effects import EffectId
from AoE2ScenarioParser.datasets.conditions import ConditionId

DEFAULT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "src", "- 古龍 ９２１ 新負血劍譜５ -utf8.aoe2scenario")
SRC = sys.argv[1] if len(sys.argv) > 1 else DEFAULT


# ---------------------------------------------------------------- 規則 1.1/1.2
def as_int16(v):
    """規則 1.2：最大血量 / 攻擊力欄位為 int16，寫入時 mod 65536 回繞。"""
    v &= 0xFFFF
    return v - 65536 if v >= 32768 else v


# ---------------------------------------------------------------- 規則 3.3
def aoc_from_de(de_raw):
    """DE 打包值 → AoC 原始存檔值（撤銷轉檔器的 x256 重新切分）。"""
    sign = -1 if de_raw < 0 else 1
    v = abs(de_raw)
    return sign * ((v >> 16) * 256 + (v & 0xFFFF))


def semantic_attack(de_raw):
    """DE 打包值 → 作者真正想要的攻擊力數值。"""
    return as_int16(aoc_from_de(de_raw))


def ename(e):
    try:
        return EffectId(e.effect_type).name
    except ValueError:
        return f"eff{e.effect_type}"


def cname(c):
    try:
        return ConditionId(c.condition_type).name
    except ValueError:
        return f"cond{c.condition_type}"


def main():
    print(f"稽核對象: {SRC}\n")
    sc = AoE2DEScenario.from_file(SRC)
    tm, pm, um, om = (sc.trigger_manager, sc.player_manager,
                      sc.unit_manager, sc.option_manager)

    print("=" * 78)
    print("§0  基本盤點")
    print("=" * 78)
    n_eff = sum(len(t.effects) for t in tm.triggers)
    n_con = sum(len(t.conditions) for t in tm.triggers)
    print(f"  觸發器 {len(tm.triggers)} / 效果 {n_eff} / 條件 {n_con}")
    print(f"  legacy_execution_order = {om.legacy_execution_order}"
          f"   {'✅ 正確' if om.legacy_execution_order else '🔴 應為 True'}")

    # ---------------------------------------------------------- §1 攻擊力
    print("\n" + "=" * 78)
    print("§1  攻擊力被轉檔切分（規則 3.2 / 3.5）")
    print("=" * 78)
    safe, broken = 0, []
    for t in tm.triggers:
        for i, e in enumerate(t.effects):
            if e.effect_type != EffectId.CHANGE_OBJECT_ATTACK:
                continue
            raw = e.quantity
            if raw is None:
                continue
            aac = e.armour_attack_class
            if aac == 0:
                safe += 1
            else:
                broken.append((t.trigger_id, t.name, i, raw, aac,
                               e.armour_attack_quantity,
                               aoc_from_de(raw), semantic_attack(raw),
                               bool(t.enabled)))
    print(f"  總數 {safe + len(broken)}")
    print(f"  ✅ class=0（正確編碼，DE 會實際套用）: {safe}")
    print(f"  🔴 需修復（class≠0，DE 完全無作用）: {len(broken)}")
    pos = sum(1 for b in broken if b[4] > 0)
    print(f"       其中 class>0 (AoC 值 ≥256): {pos}")
    print(f"       其中 class<0 (AoC 負值)  : {len(broken) - pos}")

    out = os.path.join(os.path.dirname(os.path.abspath(SRC)) or '.',
                       "audit_attack_fixlist.tsv")
    # utf-8-sig：加 BOM，讓 Excel 在中文 Windows 上直接開啟不亂碼
    with open(out, "w", encoding="utf-8-sig") as f:
        f.write("trigger_id\ttrigger_name\teffect_index\tde_raw\t"
                "de_class\tde_amount\taoc_value\tshould_be\tenabled\n")
        for b in broken:
            f.write("\t".join(str(x) for x in b) + "\n")
    print(f"  → 明細已寫出: {out}")

    print("\n  代表性樣本（依應有值排序）:")
    print(f"    {'觸發器':<22}{'DE現值':>11}{'DE誤讀':>16}{'應有值':>9}")
    for b in sorted(broken, key=lambda r: -r[7])[:10]:
        print(f"    [{b[0]}] {b[1][:14]:<16}{b[3]:>11}"
              f"{'cls %d,+%d' % (b[4], b[5]):>16}{b[7]:>9}")
    for b in sorted(broken, key=lambda r: r[7])[:6]:
        print(f"    [{b[0]}] {b[1][:14]:<16}{b[3]:>11}"
              f"{'cls %d,+%d' % (b[4], b[5]):>16}{b[7]:>9}")

    # ---------------------------------------------------------- §2 負血
    print("\n" + "=" * 78)
    print("§2  負血 / 血量回繞（規則 2.1 / 3.1）")
    print("=" * 78)
    neg_hp, wrap_ok, plain = [], [], 0
    for t in tm.triggers:
        for i, e in enumerate(t.effects):
            if e.effect_type != EffectId.CHANGE_OBJECT_HP or e.quantity is None:
                continue
            q = e.quantity
            if q > 32767:
                s = as_int16(q)
                (neg_hp if s < 0 else wrap_ok).append(
                    (t.trigger_id, t.name, i, q, s, bool(t.enabled)))
            else:
                plain += 1
    print(f"  未回繞（0..32767 或負值）: {plain}  ✅")
    print(f"  回繞後為正值: {len(wrap_ok)}  ✅（例: 95536 → 30000）")
    for r in wrap_ok:
        print(f"      [{r[0]}] {r[1]} effect[{r[2]}] {r[3]} → {r[4]}")
    print(f"  回繞後為負血: {len(neg_hp)}  🟡 需實機測試（規則 5.1）")
    for r in neg_hp:
        print(f"      [{r[0]}] {r[1]} effect[{r[2]}] {r[3]} → 最大血量 {r[4]}"
              f"  enabled={r[5]}")

    # ---------------------------------------------------------- §3 棄用項
    print("\n" + "=" * 78)
    print("§3  UGC 指南列出的已棄用項目（規則 4.1 / 4.2）")
    print("=" * 78)
    DEP_E = {'USE_ADVANCED_BUTTONS': '1.36 已失效',
             'ACKNOWLEDGE_AI_SIGNAL': '1.40 會造成連線不同步',
             'SET_OBJECT_COST': '1.54 已棄用'}
    DEP_C = {'OBJECT_SELECTED': '1.36 會造成連線不同步',
             'OBJECT_VISIBLE': '1.36 單機也不穩定',
             'OBJECT_NOT_VISIBLE': '1.36 單機也不穩定'}
    he, hc = defaultdict(list), defaultdict(list)
    for t in tm.triggers:
        for i, e in enumerate(t.effects):
            if ename(e) in DEP_E:
                he[ename(e)].append((t.trigger_id, t.name))
        for i, c in enumerate(t.conditions):
            if cname(c) in DEP_C:
                hc[cname(c)].append((t.trigger_id, t.name, bool(t.enabled)))
    for k, note in DEP_E.items():
        n = len(he[k])
        print(f"  效果 {k}: {n}  {'✅' if n == 0 else '🔴'}  ({note})")
    for k, note in DEP_C.items():
        rows = hc[k]
        print(f"  條件 {k}: {len(rows)}  {'✅' if not rows else '🟡'}  ({note})")
        for tid, nm, enb in rows:
            print(f"      [{tid}] {nm}  enabled={enb}")

    # ---------------------------------------------------------- §4 全圖生效
    print("\n" + "=" * 78)
    print("§4  無過濾破壞性效果 = 全地圖生效（規則 4.2 第 4 項）")
    print("=" * 78)
    DESTRUCTIVE = {'REMOVE_OBJECT', 'KILL_OBJECT', 'DAMAGE_OBJECT',
                   'CHANGE_OBJECT_HP', 'CHANGE_OWNERSHIP',
                   'CHANGE_OBJECT_ATTACK', 'CHANGE_OBJECT_ARMOR',
                   'TASK_OBJECT', 'FREEZE_OBJECT', 'TELEPORT_OBJECT'}
    hits = []
    for t in tm.triggers:
        for i, e in enumerate(t.effects):
            if ename(e) not in DESTRUCTIVE:
                continue
            sel = e.selected_object_ids or []
            olu = getattr(e, 'object_list_unit_id', None)
            grp = getattr(e, 'object_group', None)
            typ = getattr(e, 'object_type', None)
            area = all(getattr(e, f, -1) not in (None, -1)
                       for f in ('area_x1', 'area_y1', 'area_x2', 'area_y2'))
            if not (sel or (olu is not None and olu >= 0)
                    or (grp is not None and grp >= 0)
                    or (typ is not None and typ >= 0) or area):
                hits.append((t.trigger_id, t.name, i, ename(e),
                             e.source_player, e.quantity, bool(t.enabled)))
    live = [h for h in hits if h[6]]
    print(f"  合計 {len(hits)}，其中啟用中 {len(live)} 🟢 需逐個判斷是否刻意")
    for h in live:
        print(f"      [{h[0]}] {h[1]!r} effect[{h[2]}] {h[3]} "
              f"P{h[4]} qty={h[5]}")

    # ---------------------------------------------------------- §5 完整性
    print("\n" + "=" * 78)
    print("§5  參照完整性（規則 4.1）")
    print("=" * 78)
    tids = {t.trigger_id for t in tm.triggers}
    refs = {u.reference_id for p in pm.players
            for u in (um.get_player_units(p.player_id) or [])}
    dang_t = dang_u = n_t = n_u = 0
    for t in tm.triggers:
        for e in t.effects:
            if e.effect_type in (EffectId.ACTIVATE_TRIGGER,
                                 EffectId.DEACTIVATE_TRIGGER):
                n_t += 1
                if e.trigger_id not in tids:
                    dang_t += 1
            for r in (e.selected_object_ids or []):
                n_u += 1
                if r not in refs:
                    dang_u += 1
    print(f"  觸發器參照 {n_t}，斷鏈 {dang_t}  {'✅' if not dang_t else '🔴'}")
    print(f"  單位參照 {n_u}，失效 {dang_u}  {'✅' if not dang_u else '🔴'}")

    # ---------------------------------------------------------- §6 訊息
    print("\n" + "=" * 78)
    print("§6  Send Chat 重複訊息被 DE 吞掉（規則 4.2 第 5 項）")
    print("=" * 78)
    msgs, loop = Counter(), 0
    for t in tm.triggers:
        for e in t.effects:
            if e.effect_type == EffectId.SEND_CHAT:
                m = (e.message or '').strip()
                if m:
                    msgs[m] += 1
                if t.looping:
                    loop += 1
    dup = sum(1 for c in msgs.values() if c > 1)
    print(f"  相異字串 {len(msgs)}，重複使用 {dup}，位於循環觸發器 {loop}")
    print("  🟢 體感退化，非功能損壞")

    print("\n" + "=" * 78)
    print("稽核完成。規則依據見 古龍921_DE遷移記錄.md")
    print("=" * 78)


if __name__ == '__main__':
    main()

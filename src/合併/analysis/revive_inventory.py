# -*- coding: utf-8 -*-
"""復活接線盤點（spec §六、plan T6）：對觸發全表做五類分類。

分類定義：
- families[cid]：恰好碰一個職業（本體 ref 或玩家欄）的觸發（排除 retired）
- eff_list_appendable：效果 sel 含本體 ref 且型別 ∈ {26改名,24傷害,27改血,28改攻}（全表收集）
- eff_list_command：同上但型別 ∈ {29停止,22凍結,15移除,12任務}（不自動追加，逐支裁決）
- cond_ref：條件 unit_object/next_object 為本體 ref（死亡連動的 destroy 除外＝不做命展開）
- locref：效果 location_object_reference 為本體 ref
- addressed[cid]：家族觸發內 條件玩家欄∈1..6 ∨ 效果 tp∈1..6（不論 sel）∨（效果 sp∈1..6 ∧ sel 空）
- matrix[cid]：addressed 沿家族內 activate/deactivate 邊做前驅閉包（啟動者被拉入）
- shared[cid]：families − matrix − death_linked
- death_linked[cid]：條件含 destroy(本體ref) 的家族觸發（§七之二 狀態機處理）
- global_init：無條件（或僅 timer≤1）且玩家欄涵蓋六家全包 → 永不進矩陣
- const_filtered：非家族觸發以本體 const 過濾（條件 object_list／效果 object_list_unit_id）
- cross：碰 ≥2 職業且非六家全包（逐支裁決）
"""
from dataclasses import dataclass, field

APPENDABLE = {26, 24, 27, 28}
COMMAND = {29, 22, 15, 12}
ACTIVATION = {8, 9}


@dataclass
class Inventory:
    families: dict = field(default_factory=dict)
    eff_list_appendable: list = field(default_factory=list)
    eff_list_command: list = field(default_factory=list)
    cond_ref: list = field(default_factory=list)
    locref: list = field(default_factory=list)
    addressed: dict = field(default_factory=dict)
    matrix: dict = field(default_factory=dict)
    shared: dict = field(default_factory=dict)
    death_linked: dict = field(default_factory=dict)
    global_init: list = field(default_factory=list)
    const_filtered: list = field(default_factory=list)
    cross: list = field(default_factory=list)


def _touched_classes(t, ref2cid):
    """觸發碰到哪些職業：本體 ref（條件/效果/locref）＋ 1..6 玩家欄。"""
    cids = set()
    for c in t.conditions:
        for fld in ('unit_object', 'next_object'):
            v = getattr(c, fld, -1)
            if v in ref2cid:
                cids.add(ref2cid[v])
        sp = getattr(c, 'source_player', -1)
        if 1 <= (sp or -1) <= 6:
            cids.add(sp)
    for e in t.effects:
        for r in (getattr(e, 'selected_object_ids', None) or []):
            if r in ref2cid:
                cids.add(ref2cid[r])
        lor = getattr(e, 'location_object_reference', -1)
        if lor in ref2cid:
            cids.add(ref2cid[lor])
        for fld in ('source_player', 'target_player'):
            v = getattr(e, fld, -1)
            if 1 <= (v or -1) <= 6:
                cids.add(v)
    return cids


def _is_addressed(t):
    for c in t.conditions:
        sp = getattr(c, 'source_player', -1)
        if 1 <= (sp or -1) <= 6:
            return True
    for e in t.effects:
        tp = getattr(e, 'target_player', -1)
        if 1 <= (tp or -1) <= 6:
            return True
        sp = getattr(e, 'source_player', -1)
        if 1 <= (sp or -1) <= 6 and not (getattr(e, 'selected_object_ids', None) or []):
            return True
    return False


def _is_global_init(t):
    """無條件（或僅 timer≤1）且玩家欄涵蓋 1..6 全包 → 全域初始化。"""
    for c in t.conditions:
        if getattr(c, 'condition_type', None) == 10 and 0 <= (getattr(c, 'timer', -1) or -1) <= 1:
            continue
        return False
    touched = set()
    for e in t.effects:
        for fld in ('source_player', 'target_player'):
            v = getattr(e, fld, -1)
            if 1 <= (v or -1) <= 6:
                touched.add(v)
    return touched == {1, 2, 3, 4, 5, 6}


def build_inventory(tm, hero_refs, hero_consts, exclude=()) -> Inventory:
    inv = Inventory()
    excl = set(exclude)
    ref2cid = {r: c for c, r in hero_refs.items()}
    const2cid = {v: k for k, v in hero_consts.items()}
    triggers = [t for t in tm.triggers if t.trigger_id not in excl]

    # ---- 家族 / cross / global_init ----
    for t in triggers:
        cids = _touched_classes(t, ref2cid)
        if _is_global_init(t):
            inv.global_init.append(t.trigger_id)
            continue
        if len(cids) == 1:
            inv.families.setdefault(next(iter(cids)), set()).add(t.trigger_id)
        elif len(cids) >= 2 and cids != {1, 2, 3, 4, 5, 6}:
            inv.cross.append(t.trigger_id)

    family_all = {tid for s in inv.families.values() for tid in s}

    # ---- death_linked（先判，供 cond_ref 排除）----
    for cid, fam in inv.families.items():
        for t in triggers:
            if t.trigger_id not in fam:
                continue
            if any(getattr(c, 'condition_type', None) == 6
                   and getattr(c, 'unit_object', -1) == hero_refs[cid]
                   for c in t.conditions):
                inv.death_linked.setdefault(cid, set()).add(t.trigger_id)
    death_all = {tid for s in inv.death_linked.values() for tid in s}

    # ---- 全表收集：eff_list / cond_ref / locref ----
    for t in triggers:
        for ei, e in enumerate(t.effects):
            et = getattr(e, 'effect_type', None)
            sel = getattr(e, 'selected_object_ids', None) or []
            hits = [ref2cid[r] for r in sel if r in ref2cid]
            for cid in hits:
                if et in APPENDABLE:
                    inv.eff_list_appendable.append((t.trigger_id, ei, cid))
                elif et in COMMAND:
                    inv.eff_list_command.append((t.trigger_id, ei, cid, et))
            lor = getattr(e, 'location_object_reference', -1)
            if lor in ref2cid:
                inv.locref.append((t.trigger_id, ei, ref2cid[lor]))
        if t.trigger_id in death_all:
            continue                      # 死亡連動不做命展開
        for ci, c in enumerate(t.conditions):
            for fld in ('unit_object', 'next_object'):
                v = getattr(c, fld, -1)
                if v in ref2cid:
                    inv.cond_ref.append((t.trigger_id, ci, fld, ref2cid[v]))

    # ---- addressed / matrix 閉包 / shared ----
    by_id = {t.trigger_id: t for t in triggers}
    for cid, fam in inv.families.items():
        addressed = {tid for tid in fam if _is_addressed(by_id[tid])}
        inv.addressed[cid] = set(addressed)
        # 前驅閉包：家族內 X --activate/deactivate--> matrix 成員 ⇒ X 入 matrix
        matrix = set(addressed)
        changed = True
        while changed:
            changed = False
            for tid in fam - matrix:
                t = by_id[tid]
                for e in t.effects:
                    if getattr(e, 'effect_type', None) in ACTIVATION \
                            and getattr(e, 'trigger_id', -1) in matrix:
                        matrix.add(tid)
                        changed = True
                        break
        inv.matrix[cid] = matrix
        inv.shared[cid] = fam - matrix - inv.death_linked.get(cid, set())

    # ---- const_filtered（非家族）----
    for t in triggers:
        if t.trigger_id in family_all or t.trigger_id in inv.global_init:
            continue
        seen = set()
        for c in t.conditions:
            ol = getattr(c, 'object_list', -1)
            if ol in const2cid and ('cond', const2cid[ol]) not in seen:
                inv.const_filtered.append((t.trigger_id, 'cond', const2cid[ol]))
                seen.add(('cond', const2cid[ol]))
        for e in t.effects:
            ol = getattr(e, 'object_list_unit_id', -1)
            if ol in const2cid and ('effect', const2cid[ol]) not in seen:
                inv.const_filtered.append((t.trigger_id, 'effect', const2cid[ol]))
                seen.add(('effect', const2cid[ol]))
    return inv

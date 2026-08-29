# -*- coding: utf-8 -*-
"""s39 復活與選職業（spec §六/§七）——前半：接線改造引擎。

執行順序契約（T7）：
1. build_matrix 先跑（在原始觸發上複製 ×6 玩家位變體、玩家欄改寫、內部重指、全停用）
2. append_life_refs / expand_conditions / dup_locref 之後全表掃描（原觸發＋變體一體適用）

複製一律走 tm.copy_trigger(tid, append_after_source=False, add_suffix=False)（鐵律：
預設參數會全表重編 trigger_id）。OR 節點以「深拷貝 ref 條件＋重設為 type 29」製作，
維持 parser 物件類別以利序列化。
"""
import copy
from core.change import Change
from .base import Step, BuildError
from .revive_chains import build_chains, FLAG_CONST, REVEALER  # T9a 復活鏈

APPEND_TYPES = {26, 24, 27, 28}          # 改名/傷害/改血/改攻
PLAYERS = range(1, 7)
_COND_RESET = dict(unit_object=-1, next_object=-1, object_list=-1, source_player=-1,
                   timer=-1, quantity=-1, area_x1=-1, area_y1=-1, area_x2=-1, area_y2=-1)


def _all_ref2cid(life_refs):
    return {r: cid for cid, refs in life_refs.items() for r in refs}


def _primary_ref2cid(life_refs):
    return {refs[0]: cid for cid, refs in life_refs.items()}


def append_life_refs(tm, life_refs, skip_tids=frozenset()) -> list:
    """可追加型效果：sel 含任一命 ref → 補齊該職業全部命 ref＋玩家欄 -1。"""
    ref2cid = _all_ref2cid(life_refs)
    changes = []
    for t in tm.triggers:
        if t.trigger_id in skip_tids:
            continue
        for ei, e in enumerate(t.effects):
            if getattr(e, 'effect_type', None) not in APPEND_TYPES:
                continue
            sel = list(getattr(e, 'selected_object_ids', None) or [])
            cids = {ref2cid[r] for r in sel if r in ref2cid}
            if not cids:
                continue
            new_sel = list(sel)
            for cid in sorted(cids):
                for r in life_refs[cid]:
                    if r not in new_sel:
                        new_sel.append(r)
            old_sp = getattr(e, 'source_player', -1)
            e.selected_object_ids = new_sel
            e.source_player = -1
            if new_sel != sel or old_sp != -1:
                changes.append(Change('s39', 'eff_append', f'T{t.trigger_id}E{ei}',
                                      'sel+sp', f'{len(sel)}refs/sp{old_sp}',
                                      f'{len(new_sel)}refs/sp-1', '備身追加+中性化'))
    return changes


def _make_or(cond_template):
    node = copy.deepcopy(cond_template)
    node.condition_type = 29
    for k, v in _COND_RESET.items():
        if hasattr(node, k):
            setattr(node, k, v)
    return node


def expand_conditions(tm, life_refs, death_linked, use_or=True):
    """條件 ref 欄跨命展開。單一 ref 條件→移至尾端＋OR 副本；多 ref 條件→每命複製觸發。
    death_linked（含退役）一律跳過。回傳 (changes, dups={orig_tid: {L: copy_tid}})。"""
    prim = _primary_ref2cid(life_refs)
    changes, dups = [], {}
    for t in list(tm.triggers):
        if t.trigger_id in death_linked:
            continue
        entries = []
        for ci, c in enumerate(t.conditions):
            for fld in ('unit_object', 'next_object'):
                if getattr(c, fld, -1) in prim:
                    entries.append((ci, fld, prim[getattr(c, fld, -1)]))
        if not entries:
            continue
        if use_or and len(entries) == 1:
            ci, fld, cid = entries[0]
            c = t.conditions.pop(ci)
            t.conditions.append(c)
            for r in life_refs[cid][1:]:
                t.conditions.append(_make_or(c))
                dup = copy.deepcopy(c)
                setattr(dup, fld, r)
                t.conditions.append(dup)
            changes.append(Change('s39', 'cond_or', f'T{t.trigger_id}C{ci}', fld,
                                  str(life_refs[cid][0]), f'OR×{len(life_refs[cid])}', '跨命展開'))
        else:
            lives = {cid for _, _, cid in entries}
            if len(lives) > 1:
                raise BuildError(f'缺裁決：T{t.trigger_id} 條件同時綁多職業 ref {sorted(lives)}，'
                                 f'請入 cross 裁決後豁免或改接')
            cid = lives.pop()
            dups[t.trigger_id] = {}
            for L in range(2, len(life_refs[cid]) + 1):
                v = tm.copy_trigger(t.trigger_id, append_after_source=False, add_suffix=False)
                v.name = f'{t.name}◇命{L}'
                for ci, fld, _ in entries:
                    setattr(v.conditions[ci], fld, life_refs[cid][L - 1])
                dups[t.trigger_id][L] = v.trigger_id
                changes.append(Change('s39', 'trigger_add', f'T{t.trigger_id}→命{L}',
                                      'trigger', '', f'T{v.trigger_id}', '多ref條件每命複製'))
    return changes, dups


def dup_locref(tm, life_refs):
    """locref 效果逐命複製：原觸發=第1命拷貝（enabled 照舊），
    第 L 命副本 disabled 等復活鏈啟用。回傳 (changes, gates={(cid,L): [tid]})。"""
    prim = _primary_ref2cid(life_refs)
    changes, gates = [], {}
    for t in list(tm.triggers):
        locs = [(ei, prim[getattr(e, 'location_object_reference', -1)])
                for ei, e in enumerate(t.effects)
                if getattr(e, 'location_object_reference', -1) in prim]
        if not locs:
            continue
        cids = {cid for _, cid in locs}
        if len(cids) > 1:
            raise BuildError(f'缺裁決：T{t.trigger_id} locref 綁多職業 {sorted(cids)}')
        cid = cids.pop()
        gates.setdefault((cid, 1), []).append(t.trigger_id)
        for L in range(2, len(life_refs[cid]) + 1):
            v = tm.copy_trigger(t.trigger_id, append_after_source=False, add_suffix=False)
            v.name = f'{t.name}◇命{L}'
            v.enabled = 0
            for ei, _ in locs:
                v.effects[ei].location_object_reference = life_refs[cid][L - 1]
            gates.setdefault((cid, L), []).append(v.trigger_id)
            changes.append(Change('s39', 'trigger_add', f'T{t.trigger_id}→命{L}',
                                  'trigger', '', f'T{v.trigger_id}', 'locref 每命複製'))
    return changes, gates


def build_matrix(tm, matrix_sets):
    """玩家定址觸發 ×6 玩家位矩陣。回傳 (variant_map, enable_lists, changes)。
    - 玩家欄改寫：條件/效果中 值==class → slot（含 target_player）
    - 內部啟停重指：effect.trigger_id ∈ 同家族 matrix → 同 slot 變體
    - 全部（含原觸發）建置停用；enable_lists[(c,s)]＝原本 enabled 者的該 slot 變體"""
    variant_map, enable_lists, changes = {}, {}, []
    for cid, tids in sorted(matrix_sets.items()):
        ordered = sorted(tids)
        orig_enabled = {tid: bool(tm.triggers_by_id[tid].enabled) for tid in ordered}
        for slot in PLAYERS:
            for tid in ordered:
                if slot == cid:
                    variant_map[(tid, slot)] = tid
                    continue
                v = tm.copy_trigger(tid, append_after_source=False, add_suffix=False)
                v.name = f'{tm.triggers_by_id[tid].name}◇位{slot}'
                variant_map[(tid, slot)] = v.trigger_id
                changes.append(Change('s39', 'trigger_add', f'T{tid}→位{slot}',
                                      'trigger', '', f'T{v.trigger_id}', '矩陣變體'))
        for slot in PLAYERS:
            for tid in ordered:
                v = tm.triggers_by_id[variant_map[(tid, slot)]]
                if slot != cid:
                    for c in v.conditions:
                        if getattr(c, 'source_player', -1) == cid:
                            c.source_player = slot
                    for e in v.effects:
                        if getattr(e, 'source_player', -1) == cid:
                            e.source_player = slot
                        if getattr(e, 'target_player', -1) == cid:
                            e.target_player = slot
                        if getattr(e, 'effect_type', None) in (8, 9) \
                                and getattr(e, 'trigger_id', -1) in tids:
                            e.trigger_id = variant_map[(e.trigger_id, slot)]
                v.enabled = 0
            enable_lists[(cid, slot)] = [variant_map[(tid, slot)]
                                         for tid in ordered if orig_enabled[tid]]
    return variant_map, enable_lists, changes


class ReviveStep(Step):
    id = 's39'
    title = '復活與選職業'
    intro = '接線改造＋矩陣＋選角＋復活鏈（T9 完工前：無 revive 參數時跳過）。'

    def apply(self, ctx):
        if not ctx.spec.params.get('revive'):
            return []
        raise BuildError('缺裁決：params.revive 已存在但 s39 復活鏈尚未完工（plan T9）')


STEP = ReviveStep()

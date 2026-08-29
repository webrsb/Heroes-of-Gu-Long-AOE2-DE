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
from .base import trig_by_id, Step, BuildError
from .revive_chains import build_chains, FLAG_CONST, REVEALER  # T9a 復活鏈

APPEND_TYPES = {26, 24, 27, 28}          # 改名/傷害/改血/改攻
PLAYERS = range(1, 7)
_COND_RESET = dict(unit_object=-1, next_object=-1, object_list=-1, source_player=-1,
                   timer=-1, quantity=-1, area_x1=-1, area_y1=-1, area_x2=-1, area_y2=-1)


def _all_ref2cid(life_refs):
    return {r: cid for cid, refs in life_refs.items() for r in refs}


def _primary_ref2cid(life_refs):
    return {refs[0]: cid for cid, refs in life_refs.items()}


def append_life_refs(tm, life_refs, skip_tids=frozenset(), skip_effects=frozenset(),
                     skip_sel_refs=frozenset()) -> list:
    """可追加型效果：sel 含任一命 ref → 補齊該職業全部命 ref＋玩家欄 -1。
    skip_effects={(tid, ei)}：逐效果排除；skip_sel_refs：sel 含這些 ref（馬騎池效果）
    即跳過——內容判定、複製免疫（spec §七之三.5）。"""
    ref2cid = _all_ref2cid(life_refs)
    changes = []
    for t in tm.triggers:
        if t.trigger_id in skip_tids:
            continue
        for ei, e in enumerate(t.effects):
            if (t.trigger_id, ei) in skip_effects:
                continue
            if skip_sel_refs and skip_sel_refs.intersection(
                    getattr(e, 'selected_object_ids', None) or []):
                continue
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
        orig_enabled = {tid: bool(trig_by_id(tm, tid).enabled) for tid in ordered}
        for slot in PLAYERS:
            for tid in ordered:
                if slot == cid:
                    variant_map[(tid, slot)] = tid
                    continue
                v = tm.copy_trigger(tid, append_after_source=False, add_suffix=False)
                v.name = f'{trig_by_id(tm, tid).name}◇位{slot}'
                variant_map[(tid, slot)] = v.trigger_id
                changes.append(Change('s39', 'trigger_add', f'T{tid}→位{slot}',
                                      'trigger', '', f'T{v.trigger_id}', '矩陣變體'))
        for slot in PLAYERS:
            for tid in ordered:
                v = trig_by_id(tm, variant_map[(tid, slot)])
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


def run_revive(ctx):
    """s39 總裝（plan T9b-iii）：矩陣→flag_swap換裝→連動變體→跨集重指→效果拆分→
    池盤點→ref追加→OR展開→locref→復活鏈→上馬改造→補池→轉生旗→退役斷邊→踢人整備。"""
    from analysis.revive_inventory import build_inventory
    from .revive_chains import build_chains
    from .dl_variants import build_death_linked, convert_flag_swap_conditions
    from .revive_mount import (rebuild_mount, split_effects, inventory_pools,
                               build_pool_grants)
    from .revive_retire import (retire_and_cut, build_rebirth_flag_triggers,
                                repoint_cross, build_kick_cleanup)

    params = ctx.spec.params['revive']
    rv0 = ctx.notes.get('revive')
    if not rv0:
        raise BuildError('缺裁決：s38 未產出 ctx.notes[revive]（步驟順序異常）')
    tm = ctx.base.trigger_manager
    rspec = rv0['spec']
    life_refs = rv0['life_refs']
    hero_consts = rv0['hero_consts']
    slots = (1, 2, 3, 4, 5, 6)
    changes = []

    # ---- mount / cells 組態 ----
    mount_refs = {int(k): int(v) for k, v in params['mount_refs'].items()}
    by_ref = {u.reference_id: u for p in range(9) for u in ctx.base.unit_manager.units[p]}
    cells = params['cells']
    mount = {}
    for cid in range(1, 7):
        row = 239 - (cid - 1)
        mu = by_ref.get(mount_refs[cid])
        if mu is None:
            raise BuildError(f'缺裁決：職業{cid} 預置馬騎 ref{mount_refs[cid]} 不存在')
        mount[cid] = dict(mount_ref=mount_refs[cid], mount_const=mu.unit_const,
                          flag_cell=(221, row),
                          rebirth_cell=(int(cells['rebirth_x']), row),
                          final_cell=(int(cells['final_x']), row),
                          pool_cells=[(int(x), row) for x in cells['pool_xs']])

    retired_all = set(rspec.retired) | {int(x) for x in (params.get('retired_extra') or [])}
    rulings = ctx.spec.params.get('death_linked_rulings')
    if rulings is None:
        raise BuildError('缺裁決：params.death_linked_rulings 不存在')

    # ---- 盤點＋矩陣（flag_swap 併入矩陣集）----
    inv = build_inventory(tm, rspec.hero_refs, hero_consts, exclude=sorted(retired_all))
    ref2cid = {r: c for c, r in rspec.hero_refs.items()}
    matrix_sets = {cid: set(inv.matrix.get(cid, set())) for cid in range(1, 7)}
    for r in rulings:
        if r['category'] != 'flag_swap':
            continue
        t = trig_by_id(tm, r['tid'])
        cids = {ref2cid[c.unit_object] for c in t.conditions
                if getattr(c, 'condition_type', None) == 6
                and getattr(c, 'unit_object', -1) in ref2cid}
        if len(cids) != 1:
            raise BuildError(f'缺裁決：flag_swap T{r["tid"]} 職業判定異常 {cids}')
        matrix_sets[cids.pop()].add(r['tid'])
    x3 = {int(k): int(v) for k, v in params['mount_x3'].items()}
    for cid, tid in x3.items():
        if tid not in matrix_sets[cid]:
            raise BuildError(f'缺裁決：X馬3 T{tid}（職業{cid}）不在矩陣集——定址分類異常，請查盤點')
    # ---- 池處理（矩陣前：完成旗效果隨變體複製、盤點不通膨）----
    mount_ref2cid = {v: k for k, v in mount_refs.items()}
    pools = inventory_pools(tm, mount_ref2cid)
    changes += build_pool_grants(tm, pools, life_refs, mount)

    vm, el, ch = build_matrix(tm, matrix_sets)
    changes += ch
    changes += convert_flag_swap_conditions(tm, rulings, vm, rspec.hero_refs, mount, slots)

    # ---- 連動變體＋跨集重指＋效果拆分 ----
    dl = build_death_linked(tm, rulings, rspec.hero_refs, mount, slots)
    changes += dl.changes
    changes += repoint_cross(tm, vm, dl.variant_map)
    anti_lists = {}
    changes += split_effects(tm, params.get('effect_splits') or [], el, anti_lists, slots)

    # ---- ref 追加（sel 含馬騎 ref 的池效果依內容跳過）→ OR 展開 → locref ----
    changes += append_life_refs(tm, life_refs,
                                skip_sel_refs=set(mount_refs.values()))
    x3_all = set(x3.values()) | {vm[(t, s)] for c, t in x3.items() for s in slots}
    excl = ({r['tid'] for r in rulings} | retired_all | x3_all
            | {v for k, v in dl.variant_map.items()})
    ech, dups = expand_conditions(tm, life_refs, death_linked=excl, use_or=True)
    changes += ech
    el_index = {tid: key for key, lst in el.items() for tid in lst}
    for orig, m in dups.items():
        if orig in el_index:
            el[el_index[orig]] += list(m.values())
    lch, gates = dup_locref(tm, life_refs)
    changes += lch

    # ---- 掛勾（連動 + locref 逐命閘）----
    hooks = {}
    for key, hk in dl.hooks.items():
        hooks[key] = dict(hk)
    for cid in range(1, 7):
        for s in slots:
            hk = hooks.setdefault((cid, s), {})
            act_L, deact_L = {}, {}
            for L in range(1, rspec.lives):
                act_L[L] = list(gates.get((cid, L + 1), []))
                deact_L[L] = list(gates.get((cid, L), []))
            hk['timer_activate_L'] = act_L
            hk['timer_deactivate_L'] = deact_L

    # ---- 復活鏈 → 上馬改造 → 補池 ----
    chains = build_chains(tm, dict(
        spec=rspec, life_refs=life_refs, containers=rv0['containers'],
        class_names=rv0['class_names'], invuln_tids=rv0['invuln_tids'],
        base_hp={int(k): int(v) for k, v in params['base_hp'].items()},
        enable_lists=el, anti_lists=anti_lists, mount=mount,
        classes=tuple(range(1, 7)), slots=slots, dl_hooks=hooks))
    changes += chains.changes
    mo = rebuild_mount(tm, x3_variants={(cid, s): vm[(x3[cid], s)]
                                        for cid in range(1, 7) for s in slots},
                       life_refs=life_refs, mount=mount, watch=chains.watch,
                       final=chains.final, horse=chains.horse,
                       retired=retired_all, lives=rspec.lives)
    changes += mo.changes

    # ---- 轉生旗＋退役斷邊＋踢人整備 ----
    fmap, fch = build_rebirth_flag_triggers(tm, mount)
    changes += fch
    repoint = {1804 + cid: fmap[cid] for cid in range(1, 7)}
    changes += retire_and_cut(tm, retired_all, repoint)
    kf = params.get('kick_fences')
    if kf is None:
        raise BuildError('缺裁決：revive.kick_fences 未提供（明確跳過請填 {}）')
    if kf:
        changes += build_kick_cleanup(
            tm, dict(watch=chains.watch, timer=chains.timer, final=chains.final,
                     horse=chains.horse, select=chains.select),
            {int(k): int(v) for k, v in kf.items()})

    ctx.notes['revive_out'] = dict(enable_lists=el, anti_lists=anti_lists,
                                   variant_count=len(vm), pools=len(pools),
                                   chains=dict(watch=chains.watch, timer=chains.timer,
                                               final=chains.final, horse=chains.horse,
                                               select=chains.select))
    return changes


class ReviveStep(Step):
    id = 's39'
    title = '復活與選職業'
    intro = '接線改造＋矩陣＋選角＋復活鏈＋連動狀態機＋上馬改造（無 revive 參數時跳過）。'

    def apply(self, ctx):
        if not ctx.spec.params.get('revive'):
            return []
        return run_revive(ctx)

    def test_guide(self, changes):
        n_add = sum(1 for c in changes if c.kind == 'trigger_add')
        return (f'復活與選職業：新增觸發 {n_add} 支。\n'
                '單人驗收（spec §九）：點展示英雄選角（互斥）→ 死亡10秒重生 → 第2命找職業NPC升級 →'
                '打坐跨命 → 連動（召寵陪葬/修端木護送失敗/哥8命盡才發）→ 騎馬全流程'
                '（上馬不燒命、預存池、馬死重生仍馬形態）→ 命盡訊息 → 未選職業鎖定 → 存讀檔迴圈。\n'
                '陽性對照：原有任一技能照常運作。\n'
                '警告：步行箭俠勿踩叛變格(31-33,14-16)——沒收無解（原作設計）。')


STEP = ReviveStep()

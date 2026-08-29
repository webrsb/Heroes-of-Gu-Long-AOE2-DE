# -*- coding: utf-8 -*-
"""T9b-ii：上馬改造（spec §七之三 v4）＋怪改效果拆分（§六.6）＋補池哨兵（§七之三.5 v2）。

上馬改造：X馬3 的矩陣變體 → 逐命拷貝：
- BRING 條件改綁第 L 命 ref、加「無騎馬旗」反相條件（伯樂流程一次性）
- REMOVE 效果改第 L 命；追加 REPLACE 剩餘備身→馬騎 const、建永久騎馬旗、
  停用 watch(C,S,L)（終命停 final）、啟動馬騎監視(C,S,L)
- 指向退役觸發（X死2）的 activate 效果原地轉 None
- 原變體退役；入邊重指到扇出觸發（啟動全部 L 拷貝——各拷貝以 BRING 地理互斥自選）
"""
import re
from types import SimpleNamespace as NS
from core.change import Change
from .base import BuildError
from .revive_chains import FLAG_CONST


def rebuild_mount(tm, x3_variants, life_refs, mount, watch, final, horse, retired, lives):
    """x3_variants={(cid,slot): tid}（矩陣後）；回傳 NS(copies, fanout, changes)。"""
    out = NS(copies={}, fanout={}, changes=[])
    for (cid, slot), vtid in sorted(x3_variants.items()):
        base = tm.triggers_by_id[vtid]
        m = mount[cid]
        for L in range(1, lives + 1):
            c = tm.copy_trigger(vtid, append_after_source=False, add_suffix=False)
            c.name = f'{base.name}◇命{L}'
            c.enabled = 0
            for cond in c.conditions:
                if getattr(cond, 'unit_object', -1) == life_refs[cid][0]:
                    cond.unit_object = life_refs[cid][L - 1]
            fc = c.new_condition.objects_in_area(
                quantity=1, source_player=0, object_list=FLAG_CONST,
                area_x1=m['flag_cell'][0], area_y1=m['flag_cell'][1],
                area_x2=m['flag_cell'][0], area_y2=m['flag_cell'][1])
            fc.inverted = 1
            for e in c.effects:
                et = getattr(e, 'effect_type', None)
                if et == 15 and life_refs[cid][0] in (getattr(e, 'selected_object_ids', None) or []):
                    e.selected_object_ids = [life_refs[cid][L - 1]]
                if et in (8, 9) and getattr(e, 'trigger_id', -1) in retired:
                    e.effect_type = 0
            spares = life_refs[cid][L:]
            if spares:
                c.new_effect.replace_object(selected_object_ids=list(spares),
                                            object_list_unit_id_2=m['mount_const'],
                                            source_player=0, target_player=0)
            c.new_effect.create_object(source_player=0, object_list_unit_id=FLAG_CONST,
                                       location_x=m['flag_cell'][0],
                                       location_y=m['flag_cell'][1])
            c.new_effect.deactivate_trigger(
                trigger_id=watch[(cid, slot, L)] if L < lives else final[(cid, slot)])
            c.new_effect.activate_trigger(trigger_id=horse[(cid, slot, L)])
            out.copies[(cid, slot, L)] = c.trigger_id
            out.changes.append(Change('s39', 'trigger_add', f'{c.name}', 'trigger', '',
                                      f'T{c.trigger_id}', '上馬逐命拷貝'))
        fan = tm.add_trigger(f'{base.name}◇扇出', enabled=False, looping=False)
        for L in range(1, lives + 1):
            fan.new_effect.activate_trigger(trigger_id=out.copies[(cid, slot, L)])
        out.fanout[(cid, slot)] = fan.trigger_id
        out.changes.append(Change('s39', 'trigger_add', f'{base.name}◇扇出', 'trigger', '',
                                  f'T{fan.trigger_id}', '上馬扇出'))
        # 入邊重指到扇出；原變體退役
        for t in tm.triggers:
            for e in t.effects:
                if getattr(e, 'effect_type', None) in (8, 9) \
                        and getattr(e, 'trigger_id', -1) == vtid \
                        and t.trigger_id != fan.trigger_id:
                    e.trigger_id = fan.trigger_id
        base.enabled = 0
        base.name = f'退役_{base.name}'
    return out


def split_effects(tm, splits, enable_lists, anti_lists=None, slots=(1, 2, 3, 4, 5, 6)):
    """效果拆分（spec §六.6，雙模式）：整支複製＋除靶外全中和（泛型、任何效果型別）。
    gate=follow（預設）：變體停用、入 enable_lists（配對時啟動）。
    gate=anti：變體常駐、入 anti_lists（配對時由選角停用該位那支）。
    三重防呆：sp 與效果型別不符 → BuildError。"""
    changes = []
    anti_lists = anti_lists if anti_lists is not None else {}
    for sp_ in splits:
        t = tm.triggers_by_id.get(sp_['tid'])
        ei = sp_['effect_index']
        e = t.effects[ei] if t and ei < len(t.effects) else None
        if e is None or getattr(e, 'source_player', -1) != sp_['expect_sp'] \
                or getattr(e, 'effect_type', None) != sp_['expect_type']:
            raise BuildError(f'缺裁決：effect_split T{sp_["tid"]}E{ei} '
                             f'欄位與裁決不符（sp={getattr(e, "source_player", None)} '
                             f'type={getattr(e, "effect_type", None)}），請重查')
        cid = sp_['class_id']
        gate = sp_.get('gate', 'follow')
        for s in slots:
            v = tm.copy_trigger(sp_['tid'], append_after_source=False, add_suffix=False)
            v.name = f'{t.name}◇拆{cid}位{s}'
            v.looping = t.looping
            v.enabled = 1 if gate == 'anti' else 0
            for j, ve in enumerate(v.effects):
                if j != ei:
                    ve.effect_type = 0
                else:
                    ve.source_player = s
            if gate == 'anti':
                anti_lists.setdefault((cid, s), []).append(v.trigger_id)
            else:
                enable_lists.setdefault((cid, s), []).append(v.trigger_id)
            changes.append(Change('s39', 'trigger_add', f'{t.name}拆{cid}位{s}', 'trigger',
                                  '', f'T{v.trigger_id}',
                                  f'{sp_.get("reason", "效果拆分")}({gate})'))
        e.effect_type = 0
        changes.append(Change('s39', 'eff_neutralize', f'T{sp_["tid"]}E{ei}', 'effect_type',
                              str(sp_['expect_type']), '0', '拆分後本體抽除'))
        for j in (sp_.get('neutralize_also') or []):
            t.effects[j].effect_type = 0
            changes.append(Change('s39', 'eff_neutralize', f'T{sp_["tid"]}E{j}',
                                  'effect_type', '', '0', '拆分伴隨抽除（同組防呆）'))
    return changes


def inventory_pools(tm, mount_ref2cid):
    """自動盤點池任務：灌血效果（24 負量）sel 命中預置馬騎 ref。"""
    pools = []
    for t in tm.triggers:
        for ei, e in enumerate(t.effects):
            if getattr(e, 'effect_type', None) != 24:
                continue
            q = getattr(e, 'quantity', None)
            if q is None or q >= 0:
                continue
            hit = [mount_ref2cid[r] for r in (getattr(e, 'selected_object_ids', None) or [])
                   if r in mount_ref2cid]
            if hit:
                pools.append(dict(tid=t.trigger_id, ei=ei, cid=hit[0], qty=q,
                                  name=t.name or '(無名)'))
    return pools


def build_pool_grants(tm, pools, life_refs, mount):
    """補池哨兵（乙案 v2）：池任務觸發加完成旗效果；per (C,Q) 常駐哨兵
    [騎馬旗∧任務旗] → 灌全部備身。pool_cells 不夠配 → BuildError。"""
    changes = []
    used = {}
    for p in pools:
        cid = p['cid']
        m = mount[cid]
        idx = used.get(cid, 0)
        cells = m.get('pool_cells') or []
        if idx >= len(cells):
            raise BuildError(f'缺裁決：職業{cid} 池任務數 {idx + 1} 超過 pool_cells 配額 '
                             f'{len(cells)}，請在 merge_spec revive.cells 擴充')
        cell = cells[idx]
        used[cid] = idx + 1
        qt = tm.triggers_by_id[p['tid']]
        qt.new_effect.create_object(source_player=0, object_list_unit_id=FLAG_CONST,
                                    location_x=cell[0], location_y=cell[1])
        s = tm.add_trigger(f'補池{cid}Q{idx}', enabled=True, looping=False)
        for c in (m['flag_cell'], cell):
            s.new_condition.objects_in_area(quantity=1, source_player=0,
                                            object_list=FLAG_CONST,
                                            area_x1=c[0], area_y1=c[1],
                                            area_x2=c[0], area_y2=c[1])
        s.new_effect.damage_object(source_player=-1, quantity=p['qty'],
                                   selected_object_ids=list(life_refs[cid][1:]))
        changes.append(Change('s39', 'trigger_add', f'補池{cid}Q{idx}', 'trigger', '',
                              f'T{s.trigger_id}',
                              f'{p["name"]} 池 {p["qty"]} 兩旗齊立灌全備身'))
    return changes

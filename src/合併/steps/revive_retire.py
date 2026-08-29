# -*- coding: utf-8 -*-
"""T9b-iii：退役斷邊、轉生旗建立、跨集重指、踢人清理（spec §七之二.d／§六.5／裁決①）。

斷邊規則：指向退役觸發的 **activate 邊必須重指**（activate 會蓋過停用、令退役觸發復活）
——無映射即 BuildError；deactivate 邊放行（對停用觸發無害空指）。"""
from types import SimpleNamespace as NS
from core.change import Change
from .base import BuildError
from .revive_chains import FLAG_CONST


def retire_and_cut(tm, retired, repoint):
    """retired: tids → enabled=0＋退役_前綴；全表掃活化邊。repoint: {retired_tid: new_tid}。"""
    retired = set(retired)
    changes = []
    for tid in sorted(retired):
        t = tm.triggers_by_id.get(tid)
        if t is None:
            raise BuildError(f'缺裁決：退役目標 T{tid} 不存在，基底版本可能已變')
        t.enabled = 0
        if not (t.name or '').startswith('退役_'):
            t.name = f'退役_{t.name}'
        changes.append(Change('s39', 'trigger_field', f'T{tid}', 'enabled/name',
                              '原', '退役_', '退役'))
    orphans = []
    for t in tm.triggers:
        if t.trigger_id in retired or (t.name or '').startswith('退役_'):
            continue          # 退役來源的殘邊無害（無人再啟動它們）
        for i, e in enumerate(t.effects):
            if getattr(e, 'effect_type', None) == 8 \
                    and getattr(e, 'trigger_id', -1) in retired:
                tgt = e.trigger_id
                if tgt in repoint:
                    e.trigger_id = repoint[tgt]
                    changes.append(Change('s39', 'edge_repoint',
                                          f'T{t.trigger_id}E{i}', 'activate',
                                          f'T{tgt}', f'T{repoint[tgt]}', '退役斷邊重指'))
                else:
                    orphans.append(f'T{t.trigger_id}「{t.name or "(無名)"}」E{i}→T{tgt}')
    if orphans:
        raise BuildError('缺裁決：以下活化邊指向退役觸發且無重指映射——\n' + '\n'.join(orphans))
    return changes


def build_rebirth_flag_triggers(tm, mount, classes=(1, 2, 3, 4, 5, 6)):
    """轉生旗建立觸發（裁決①）：per 職業、停用、由 X51 的活化邊重指驅動；
    點火即建轉生旗（訊息組據此切換俠名世代）。"""
    fmap, changes = {}, []
    for cid in classes:
        t = tm.add_trigger(f'轉生旗{cid}', enabled=False, looping=False)
        cell = mount[cid]['rebirth_cell']
        t.new_effect.create_object(source_player=0, object_list_unit_id=FLAG_CONST,
                                   location_x=cell[0], location_y=cell[1])
        fmap[cid] = t.trigger_id
        changes.append(Change('s39', 'trigger_add', f'轉生旗{cid}', 'trigger', '',
                              f'T{t.trigger_id}', 'X51 世代切換改旗標'))
    return fmap, changes


def repoint_cross(tm, variant_map, dl_variant_map):
    """跨集重指：矩陣變體（含 slot==class 原觸發）的啟停邊若指向連動原觸發，
    改指同位的連動變體。"""
    dl_by_tid = {}
    for (tid, slot), vtid in dl_variant_map.items():
        dl_by_tid.setdefault(tid, {})[slot] = vtid
    changes = []
    for (tid, slot), vtid in variant_map.items():
        t = tm.triggers_by_id[vtid]
        for i, e in enumerate(t.effects):
            if getattr(e, 'effect_type', None) in (8, 9):
                tgt = getattr(e, 'trigger_id', -1)
                if tgt in dl_by_tid:
                    if slot not in dl_by_tid[tgt]:
                        raise BuildError(f'缺裁決：T{vtid} 啟停邊指向連動 T{tgt}，'
                                         f'但無位{slot}變體')
                    e.trigger_id = dl_by_tid[tgt][slot]
                    changes.append(Change('s39', 'edge_repoint', f'T{vtid}E{i}',
                                          'cross', f'T{tgt}',
                                          f'T{dl_by_tid[tgt][slot]}', '跨集重指'))
    return changes


def build_kick_cleanup(tm, chains, fences):
    """踢人柵欄整備：per 位清理觸發（停用該位全部鏈路），柵欄觸發追加啟動之。
    chains: dict(watch/timer/final/horse/select 各 {key: tid})。"""
    changes = []
    for slot, fence_tid in sorted(fences.items()):
        fence = tm.triggers_by_id.get(fence_tid)
        if fence is None:
            raise BuildError(f'缺裁決：kick_fences 位{slot} 指向不存在的 T{fence_tid}')
        cl = tm.add_trigger(f'踢除清理位{slot}', enabled=False, looping=False)
        tids = []
        for kind in ('watch', 'timer', 'horse'):
            tids += [v for k, v in chains.get(kind, {}).items() if k[1] == slot]
        for kind in ('final', 'select'):
            tids += [v for k, v in chains.get(kind, {}).items() if k[1] == slot]
        for x in sorted(set(tids)):
            cl.new_effect.deactivate_trigger(trigger_id=x)
        fence.new_effect.activate_trigger(trigger_id=cl.trigger_id)
        changes.append(Change('s39', 'trigger_add', f'踢除清理位{slot}', 'trigger', '',
                              f'T{cl.trigger_id}', f'柵欄T{fence_tid}整備'))
    return changes

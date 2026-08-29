# -*- coding: utf-8 -*-
"""T9b-i：死亡連動變體建造器（spec §七之二＋merge_spec death_linked_rulings）。

原則：條件/效果只做**原地轉換**、不做清單增刪（避開 parser 內部序列風險）：
- 「移除 destroy 條件」＝轉 timer(0)（恆真）
- 「c_flag 讀命盡旗」＝destroy 轉 objects_in_area(final_cell, const720)
- 「剝除空 REMOVE」＝effect_type 轉 0（None）
- flag_swap＝destroy 轉 objects_in_area(flag_cell)（矩陣複製後的後處理）
"""
import re
from types import SimpleNamespace as NS
from core.change import Change
from .base import trig_by_id, BuildError
from .revive_chains import FLAG_CONST

_STRIP_RE = re.compile(r'剝除E(\d+)空REMOVE')


def _rewrite_players(t, cid, slot):
    if slot == cid:
        return
    for c in t.conditions:
        if getattr(c, 'source_player', -1) == cid:
            c.source_player = slot
    for e in t.effects:
        if getattr(e, 'source_player', -1) == cid:
            e.source_player = slot
        if getattr(e, 'target_player', -1) == cid:
            e.target_player = slot


def _to_timer0(cond):
    cond.condition_type = 10
    cond.timer = 0
    cond.unit_object = -1


def _to_flag_read(cond, cell):
    cond.condition_type = 5
    cond.unit_object = -1
    cond.object_list = FLAG_CONST
    cond.source_player = 0
    cond.quantity = 1
    cond.area_x1, cond.area_y1 = cell
    cond.area_x2, cond.area_y2 = cell


def _class_of(name):
    m = re.match(r'(\d)', name or '')
    if m:
        return int(m.group(1))
    return None


def build_death_linked(tm, rulings, hero_refs, mount, slots=(1, 2, 3, 4, 5, 6)):
    """a/b/c_flag 三類：per slot 變體＋原觸發退役停用。
    回傳 NS(variant_map={(tid,slot):tid}, hooks={(cid,slot):{'watch_activate':[],
    'timer_deactivate':[]}}, changes=[])。flag_swap 不在此處理（走矩陣＋後處理）。"""
    ref2cid = {r: c for c, r in hero_refs.items()}
    out = NS(variant_map={}, hooks={}, changes=[])
    for r in rulings:
        cat = r['category']
        if cat in ('d', 'flag_swap'):
            continue
        tid = r['tid']
        t = trig_by_id(tm, tid)
        if t is None or (t.name or '') != r.get('name', ''):
            raise BuildError(f'缺裁決：連動 T{tid} 名稱「{getattr(t, "name", None)}」'
                             f'≠ 裁決表「{r.get("name")}」，基底版本可能已變，請重跑盤點')
        # 職業：由 destroy 條件的本體 ref 判定
        cids = {ref2cid[c.unit_object] for c in t.conditions
                if getattr(c, 'condition_type', None) == 6
                and getattr(c, 'unit_object', -1) in ref2cid}
        if len(cids) != 1:
            raise BuildError(f'缺裁決：連動 T{tid} 的 destroy 本體條件數異常（{cids}）')
        cid = cids.pop()
        strip = [int(x) for x in _STRIP_RE.findall(r.get('extras', '') or '')]
        for s in slots:
            v = tm.copy_trigger(tid, append_after_source=False, add_suffix=False)
            v.name = f'{t.name}◇位{s}'
            _rewrite_players(v, cid, s)
            for c in v.conditions:
                if getattr(c, 'condition_type', None) == 6 \
                        and getattr(c, 'unit_object', -1) == hero_refs[cid]:
                    if cat == 'c_flag':
                        _to_flag_read(c, mount[cid]['final_cell'])
                    else:
                        _to_timer0(c)
            for i in strip:
                v.effects[i].effect_type = 0
            if cat in ('a', 'b'):
                v.enabled = 0
                hk = out.hooks.setdefault((cid, s), {'watch_activate': [],
                                                     'timer_deactivate': []})
                hk['watch_activate'].append(v.trigger_id)
                hk['timer_deactivate'].append(v.trigger_id)
            out.variant_map[(tid, s)] = v.trigger_id
            out.changes.append(Change('s39', 'trigger_add', f'{t.name}→位{s}', 'trigger',
                                      '', f'T{v.trigger_id}', f'連動{cat}變體'))
        t.enabled = 0
        t.name = f'退役_{t.name}'
        out.changes.append(Change('s39', 'trigger_field', f'T{tid}', 'enabled/name',
                                  '原', '退役_', f'連動{cat}原觸發退役'))
    return out


def convert_flag_swap_conditions(tm, rulings, variant_map, hero_refs, mount,
                                 slots=(1, 2, 3, 4, 5, 6)):
    """flag_swap（騎馬閂鎖）：矩陣複製後，把全部變體（含 slot==class 原觸發）的
    destroy(本體) 條件原地轉騎馬旗讀取（職業列鍵定）。回傳 changes。"""
    ref2cid = {r: c for c, r in hero_refs.items()}
    changes = []
    for r in rulings:
        if r['category'] != 'flag_swap':
            continue
        tid = r['tid']
        base = trig_by_id(tm, tid)
        if base is None or (base.name or '').replace('退役_', '') != r.get('name', ''):
            raise BuildError(f'缺裁決：flag_swap T{tid} 名稱不符裁決表，請重跑盤點')
        for s in slots:
            vid = variant_map.get((tid, s))
            if vid is None:
                raise BuildError(f'缺裁決：flag_swap T{tid} 缺位{s}矩陣變體——'
                                 f'該觸發必須併入矩陣集')
            v = trig_by_id(tm, vid)
            done = False
            for c in v.conditions:
                if getattr(c, 'condition_type', None) == 6 \
                        and getattr(c, 'unit_object', -1) in ref2cid:
                    cell = mount[ref2cid[c.unit_object]]['flag_cell']
                    _to_flag_read(c, cell)
                    done = True
            if not done:
                raise BuildError(f'缺裁決：flag_swap T{tid} 位{s} 變體找不到 destroy 本體條件')
            changes.append(Change('s39', 'cond_swap', f'T{vid}', 'destroy→騎馬旗',
                                  'destroy(本體)', 'objects_in_area(旗)', 'flag_swap'))
    return changes

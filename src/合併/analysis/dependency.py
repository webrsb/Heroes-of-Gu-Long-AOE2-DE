# -*- coding: utf-8 -*-
"""群依賴度評估：決定 自動搬運 / 需手寫補丁，並列衝突。"""
from dataclasses import dataclass, field
from AoE2ScenarioParser.datasets.effects import EffectId

_ACT = {int(EffectId.ACTIVATE_TRIGGER), int(EffectId.DEACTIVATE_TRIGGER)}

def collect_object_refs(triggers):
    refs = set()
    for t in triggers:
        for e in t.effects:
            refs |= {r for r in (e.selected_object_ids or []) if r >= 0}
            loc = getattr(e, 'location_object_reference', None)
            if loc is not None and loc >= 0:
                refs.add(loc)
        for c in t.conditions:
            for f in ('unit_object', 'next_object'):
                v = getattr(c, f, None)
                if v is not None and v >= 0:
                    refs.add(v)
    return refs

def effect_target_refs(e, unit_idx):
    """解析單一效果的完整目標集合（三模式：指名 / 區域+玩家+類型 / 無過濾）。
    回傳 ref 集合。無任何過濾（全圖）回傳空集合並由呼叫方自行決定語意。"""
    if e.selected_object_ids:
        return {r for r in e.selected_object_ids if r in unit_idx}
    has_area = e.area_x1 is not None and e.area_x1 >= 0
    has_player = e.source_player not in (None, -1)
    has_type = getattr(e, 'object_list_unit_id', None) not in (None, -1)
    if not (has_area or has_player or has_type):
        return set()
    out = set()
    for r, (p, c, x, y) in unit_idx.items():
        if has_player and p != e.source_player:
            continue
        if has_type and c != e.object_list_unit_id:
            continue
        if has_area and not (e.area_x1 <= x <= e.area_x2 + 1 and e.area_y1 <= y <= e.area_y2 + 1):
            continue
        out.add(r)
    return out


def build_unit_index(scenario):
    idx = {}
    for p in range(9):
        for u in scenario.unit_manager.units[p]:
            idx[u.reference_id] = (p, u.unit_const, round(u.x, 2), round(u.y, 2))
    return idx

@dataclass
class GroupReport:
    label: str
    members: set
    refs_same: int = 0
    refs_a_only: list = field(default_factory=list)
    refs_collision: list = field(default_factory=list)
    area_effect_count: int = 0
    cross_out_edges: list = field(default_factory=list)  # (src_a_id, b_id|None)
    classification: str = 'auto'
    reasons: list = field(default_factory=list)

def assess_group(label, members, a_triggers_by_id, idx_a, idx_b, pairing) -> GroupReport:
    r = GroupReport(label, members)
    ts = [a_triggers_by_id[i] for i in sorted(members)]
    for ref in sorted(collect_object_refs(ts)):
        in_a, in_b = ref in idx_a, ref in idx_b
        if in_a and in_b and idx_a[ref] == idx_b[ref]:
            r.refs_same += 1
        elif in_a and not in_b:
            r.refs_a_only.append(ref)
        elif in_a and in_b:
            r.refs_collision.append(ref)
    for t in ts:
        for e in t.effects:
            if not (e.selected_object_ids or []) and e.area_x1 is not None and e.area_x1 >= 0:
                r.area_effect_count += 1
            if int(e.effect_type) in _ACT and e.trigger_id is not None \
                    and e.trigger_id >= 0 and e.trigger_id not in members:
                r.cross_out_edges.append((t.trigger_id, pairing.a2b.get(e.trigger_id)))
    if r.refs_collision:
        r.classification = 'patch'
        r.reasons.append(f'ref 衝突（兩版同 ref 不同物件）: {r.refs_collision}')
    if any(b is None for _, b in r.cross_out_edges):
        r.classification = 'patch'
        r.reasons.append('有啟動邊指向配對不到的基底觸發（掛點衝突）')
    if r.classification == 'auto':
        r.reasons.append('物件全數可解析、啟動邊全數可配對')
    return r

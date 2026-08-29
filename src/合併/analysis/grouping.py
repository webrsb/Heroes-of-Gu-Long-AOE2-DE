# -*- coding: utf-8 -*-
"""啟動關係分群：unmatched 觸發的連通分量 = 圈選單位。"""
import os
from AoE2ScenarioParser.datasets.effects import EffectId

_ACT = {int(EffectId.ACTIVATE_TRIGGER), int(EffectId.DEACTIVATE_TRIGGER)}

def activation_edges(triggers):
    edges = []
    for t in triggers:
        for e in t.effects:
            if int(e.effect_type) in _ACT and e.trigger_id is not None and e.trigger_id >= 0:
                edges.append((t.trigger_id, e.trigger_id))
    return edges

def group_ids(candidate_ids, edges):
    parent = {i: i for i in candidate_ids}
    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]; x = parent[x]
        return x
    for a, b in edges:
        if a in parent and b in parent:
            parent[find(a)] = find(b)
    comps = {}
    for i in candidate_ids:
        comps.setdefault(find(i), set()).add(i)
    return list(comps.values())

def group_label(triggers_by_id, members):
    names = [triggers_by_id[i].name for i in sorted(members) if triggers_by_id[i].name]
    if not names:
        return f'組_{min(members)}'
    prefix = os.path.commonprefix(names).strip()
    return prefix if prefix else f'組_{min(members)}'

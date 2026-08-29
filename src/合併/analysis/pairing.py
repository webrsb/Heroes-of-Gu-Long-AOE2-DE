# -*- coding: utf-8 -*-
"""兩版觸發配對：name → fingerprint → type_signature（fuzzy）。"""
from collections import defaultdict
from dataclasses import dataclass, field
from .fingerprint import fingerprint, type_signature

@dataclass
class PairTable:
    a2b: dict = field(default_factory=dict)
    b2a: dict = field(default_factory=dict)
    method: dict = field(default_factory=dict)   # a_id -> 'name'|'fp'|'fuzzy'
    unmatched_a: list = field(default_factory=list)
    unmatched_b: list = field(default_factory=list)

def _match_round(rest_a, rest_b, key_fn, tag, pt):
    ka = defaultdict(list); kb = defaultdict(list)
    for t in rest_a: ka[key_fn(t)].append(t)
    for t in rest_b: kb[key_fn(t)].append(t)
    for k, la in ka.items():
        lb = kb.get(k, [])
        if len(la) == 1 and len(lb) == 1:
            a, b = la[0], lb[0]
            pt.a2b[a.trigger_id] = b.trigger_id
            pt.b2a[b.trigger_id] = a.trigger_id
            pt.method[a.trigger_id] = tag
    return ([t for t in rest_a if t.trigger_id not in pt.a2b],
            [t for t in rest_b if t.trigger_id not in pt.b2a])

def _match_dup_names(rest_a, rest_b, pt):
    """同名且兩邊出現次數相等 → 按出現順序配對（兩版同宗，觸發順序穩定）。"""
    ka = defaultdict(list); kb = defaultdict(list)
    for t in rest_a: ka[t.name].append(t)
    for t in rest_b: kb[t.name].append(t)
    for name, la in ka.items():
        lb = kb.get(name, [])
        if la and len(la) == len(lb):
            for a, b in zip(la, lb):
                pt.a2b[a.trigger_id] = b.trigger_id
                pt.b2a[b.trigger_id] = a.trigger_id
                pt.method[a.trigger_id] = 'name-dup'
    return ([t for t in rest_a if t.trigger_id not in pt.a2b],
            [t for t in rest_b if t.trigger_id not in pt.b2a])

def pair_triggers(a_triggers, b_triggers) -> PairTable:
    pt = PairTable()
    ra, rb = list(a_triggers), list(b_triggers)
    ra, rb = _match_round(ra, rb, lambda t: t.name, 'name', pt)
    ra, rb = _match_round(ra, rb, fingerprint, 'fp', pt)
    ra, rb = _match_dup_names(ra, rb, pt)
    ra, rb = _match_round(ra, rb, type_signature, 'fuzzy', pt)
    pt.unmatched_a = [t.trigger_id for t in ra]
    pt.unmatched_b = [t.trigger_id for t in rb]
    return pt

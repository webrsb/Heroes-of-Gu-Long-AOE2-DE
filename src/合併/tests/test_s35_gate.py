# -*- coding: utf-8 -*-
"""T3: 城門特例（拆 const95 構件、置石門）＋換皮碰撞稽核。"""
import pytest
from types import SimpleNamespace as NS
from steps.s35_misc import apply_gate_fix, audit_const_collision
from steps.base import BuildError

ENTRY = dict(remove_const=95, expect_count=6, gate_const=88, player=8)


def U(ref, const, x, y):
    return NS(reference_id=ref, unit_const=const, x=x, y=y)


def make_um(units8):
    um = NS(units=[list(units8) if p == 8 else [] for p in range(9)],
            added=[], removed=[])
    um.add_unit = lambda **kw: (um.added.append(kw), NS(reference_id=99999, **kw))[1]
    um.remove_unit = lambda reference_id=None, unit=None: um.removed.append(
        reference_id if reference_id is not None else unit.reference_id)
    return um


def pieces():
    return [U(i, 95, 225.5, 11.5 if i < 3 else 14.5) for i in range(6)]


def test_gate_fix_removes_six_places_one_at_envelope_center():
    um = make_um(pieces())
    changes, gate_ref = apply_gate_fix(um, ENTRY)
    assert gate_ref == 99999
    assert sorted(um.removed) == [0, 1, 2, 3, 4, 5]
    assert len(um.added) == 1
    add = um.added[0]
    assert add['unit_const'] == 88 and add['player'] == 8
    assert add['x'] == 225.5 and add['y'] == 13.0     # 包絡中點
    kinds = [c.kind for c in changes]
    assert kinds.count('unit_remove') == 6 and kinds.count('unit_add') == 1


def test_gate_fix_wrong_count_raises():
    um = make_um(pieces()[:1])
    with pytest.raises(BuildError):
        apply_gate_fix(um, ENTRY)


def _cond(**kw):
    base = dict(condition_type=5, object_list=-1, area_x1=-1, area_y1=-1,
                area_x2=-1, area_y2=-1, source_player=-1)
    base.update(kw)
    return NS(**base)


def _eff(**kw):
    base = dict(effect_type=15, object_list_unit_id=-1, source_player=-1,
                area_x1=-1, area_y1=-1, area_x2=-1, area_y2=-1,
                selected_object_ids=[])
    base.update(kw)
    return NS(**base)


def _tm(trigs):
    return NS(triggers=trigs)


def test_collision_audit_flags_effect_side():
    # 效果以 olu=329 掃區域，且區域涵蓋換皮後的 329 單位座標 → 必告警
    t = NS(trigger_id=7, name='假船塢', conditions=[],
           effects=[_eff(object_list_unit_id=329, source_player=7,
                         area_x1=38, area_y1=34, area_x2=41, area_y2=37)])
    um = make_um([U(50, 329, 39.5, 35.5)])
    hits = audit_const_collision(_tm([t]), um, [329])
    assert len(hits) == 1 and 'T7' in hits[0]


def test_collision_audit_flags_condition_side():
    t = NS(trigger_id=9, name='假條件', effects=[],
           conditions=[_cond(object_list=74, source_player=8,
                             area_x1=190, area_y1=136, area_x2=195, area_y2=140)])
    um = make_um([U(51, 74, 192.5, 138.5)])
    hits = audit_const_collision(_tm([t]), um, [74])
    assert len(hits) == 1 and 'T9' in hits[0]


def test_collision_audit_ignores_disjoint_area():
    t = NS(trigger_id=11, name='他處', effects=[],
           conditions=[_cond(object_list=74, source_player=7,
                             area_x1=0, area_y1=0, area_x2=5, area_y2=5)])
    um = make_um([U(52, 74, 192.5, 138.5)])
    assert audit_const_collision(_tm([t]), um, [74]) == []


def test_collision_audit_no_area_means_global_hit():
    # 無區域（全圖）過濾同 const → 也要告警
    t = NS(trigger_id=13, name='全圖殺', effects=[_eff(object_list_unit_id=1811, source_player=8)],
           conditions=[])
    um = make_um([U(53, 1811, 75.5, 111.5)])
    hits = audit_const_collision(_tm([t]), um, [1811])
    assert len(hits) == 1

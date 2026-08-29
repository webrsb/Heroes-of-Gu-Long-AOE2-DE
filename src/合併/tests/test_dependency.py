import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from types import SimpleNamespace as NS
from analysis.dependency import collect_object_refs, assess_group
from analysis.pairing import PairTable
from AoE2ScenarioParser.datasets.effects import EffectId

def _eff(sel=(), loc=None, et=1, tid=-1, area=None):
    d = dict(effect_type=et, selected_object_ids=list(sel), location_object_reference=loc,
             trigger_id=tid, area_x1=None, area_y1=None, area_x2=None, area_y2=None)
    if area:
        d.update(area_x1=area[0], area_y1=area[1], area_x2=area[2], area_y2=area[3])
    return NS(**d)

def _t(tid, name, effs):
    return NS(trigger_id=tid, name=name, conditions=[], effects=effs)

def test_collect_refs():
    t = _t(0, 'x', [_eff(sel=[7, 8], loc=9)])
    assert collect_object_refs([t]) == {7, 8, 9}

def _assess(effs, idx_a, idx_b, pairing=None):
    ts = {0: _t(0, 'g1', effs)}
    return assess_group('g', {0}, ts, idx_a, idx_b, pairing or PairTable())

def test_auto_when_refs_identical():
    idx = {7: (0, 100, 1.0, 2.0)}
    r = _assess([_eff(sel=[7])], idx, dict(idx))
    assert r.classification == 'auto' and r.refs_same == 1

def test_patch_on_collision():
    r = _assess([_eff(sel=[7])], {7: (0, 100, 1.0, 2.0)}, {7: (1, 200, 3.0, 4.0)})
    assert r.classification == 'patch' and r.refs_collision == [7]

def test_patch_on_unmapped_cross_edge():
    e = _eff(et=int(EffectId.ACTIVATE_TRIGGER), tid=999)   # 999 在群外且 pairing 無對應
    r = _assess([e], {}, {})
    assert r.classification == 'patch' and (0, None) in r.cross_out_edges

def test_auto_with_mapped_cross_edge():
    pt = PairTable(a2b={999: 42})
    e = _eff(et=int(EffectId.ACTIVATE_TRIGGER), tid=999)
    r = _assess([e], {}, {}, pt)
    assert r.classification == 'auto' and (0, 42) in r.cross_out_edges

def test_area_effect_counted():
    r = _assess([_eff(area=(1, 1, 5, 5))], {}, {})
    assert r.area_effect_count == 1

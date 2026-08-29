import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from types import SimpleNamespace as NS
from analysis.fingerprint import fingerprint, type_signature

def _eff(**kw):
    d = dict(effect_type=1, quantity=None, tribute_list=None, object_list_unit_id=None,
             source_player=None, target_player=None, technology=None, operation=None,
             object_attributes=None, area_x1=None, area_y1=None, area_x2=None, area_y2=None,
             location_x=None, location_y=None, trigger_id=99, selected_object_ids=[7],
             message='嗨')
    d.update(kw); return NS(**d)

def _cond(**kw):
    d = dict(condition_type=3, quantity=None, attribute=None, unit_object=None,
             next_object=None, object_list=None, source_player=None, technology=None,
             timer=None, area_x1=None, area_y1=None, area_x2=None, area_y2=None,
             inverted=None, comparison=None)
    d.update(kw); return NS(**d)

def _trig(conds, effs):
    return NS(conditions=conds, effects=effs)

def test_rename_invariant_fields_ignored():
    a = _trig([_cond(quantity=5)], [_eff(quantity=100, trigger_id=1, message='A')])
    b = _trig([_cond(quantity=5)], [_eff(quantity=100, trigger_id=2, message='B')])
    assert fingerprint(a) == fingerprint(b)

def test_param_change_changes_fingerprint():
    a = _trig([], [_eff(quantity=100)])
    b = _trig([], [_eff(quantity=200)])
    assert fingerprint(a) != fingerprint(b)
    assert type_signature(a) == type_signature(b)

def test_order_matters():
    e1, e2 = _eff(effect_type=1), _eff(effect_type=2)
    assert fingerprint(_trig([], [e1, e2])) != fingerprint(_trig([], [e2, e1]))

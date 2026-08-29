import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pytest
from types import SimpleNamespace as NS
from steps.s90_audit import check_attack, check_trigger_refs, check_object_refs
from AoE2ScenarioParser.datasets.effects import EffectId

def _eff(**kw):
    d = dict(effect_type=1, quantity=0, trigger_id=-1, selected_object_ids=[],
             location_object_reference=None)
    d.update(kw); return NS(**d)

def _scn(effs, units=()):
    t = NS(trigger_id=0, name='t', conditions=[], effects=list(effs))
    um = NS(units=[[NS(reference_id=r, unit_const=1, x=0, y=0) for r in units]] + [[]] * 8)
    return NS(trigger_manager=NS(triggers=[t]), unit_manager=um)

def test_check_attack():
    ok = _scn([_eff(effect_type=int(EffectId.CHANGE_OBJECT_ATTACK), quantity=100)])
    bad = _scn([_eff(effect_type=int(EffectId.CHANGE_OBJECT_ATTACK), quantity=65536)])
    assert check_attack(ok) == [] and len(check_attack(bad)) == 1

def test_check_trigger_refs():
    ok = _scn([_eff(effect_type=int(EffectId.ACTIVATE_TRIGGER), trigger_id=0)])
    bad = _scn([_eff(effect_type=int(EffectId.ACTIVATE_TRIGGER), trigger_id=999)])
    assert check_trigger_refs(ok) == [] and len(check_trigger_refs(bad)) == 1

def test_check_object_refs_against_baseline():
    bad = _scn([_eff(selected_object_ids=[777])], units=(1, 2))
    assert check_object_refs(bad, baseline=set()) != []
    assert check_object_refs(bad, baseline={777}) == []   # origin 本來就 dangling 者豁免

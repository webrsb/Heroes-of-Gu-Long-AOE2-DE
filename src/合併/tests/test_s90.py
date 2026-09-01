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


def test_check_no_empty_effects():
    from steps.s90_audit import check_no_empty_effects
    ok = _scn([_eff(effect_type=3)])
    bad = _scn([_eff(effect_type=0), _eff(effect_type=3), _eff(effect_type=0)])
    assert check_no_empty_effects(ok) == []
    v = check_no_empty_effects(bad)
    assert len(v) == 1 and 'T0' in v[0] and '2' in v[0]


def test_glyph_gate_catches_chars_outside_the_de_atlas():
    """缺字閘門：玩家看得到的文字用了字圖集以外的字即中止建置（以前只有進遊戲才發現）。
    覆蓋表讀不到遊戲目錄時退回版控快照，所以這條在沒裝遊戲的機器上也成立。"""
    from types import SimpleNamespace as NS
    from steps.s90_audit import check_glyphs
    def scn(msg):
        return NS(message_manager=NS(hints=''),
                  player_manager=NS(players=[]),
                  trigger_manager=NS(triggers=[NS(trigger_id=5, name='1棧', short_description='',
                                                  description='', effects=[NS(message=msg)])]))
    bad = check_glyphs(scn('<ORANGE>本客棧不提供'))
    assert len(bad) == 1 and 'U+68E7' in bad[0] and 'glyph_fixes' in bad[0]
    assert check_glyphs(scn('<ORANGE>本客店不提供')) == []       # 換字後放行

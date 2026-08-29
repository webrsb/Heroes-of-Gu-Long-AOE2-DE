# -*- coding: utf-8 -*-
"""T4: s36 換皮屬性校正——整數屬性一條 SET；分數屬性 SET＋DIVIDE 相鄰兩條。"""
import pytest
from types import SimpleNamespace as NS
from steps.s36_attrfix import expand_attr_entries, apply_attr_fixes
from steps.base import BuildError

ENTRY_FIST = dict(unit_const=1811, players=[1, 2], reason='拳',
                  attrs={'hit_points': 75, 'attack_c4': 10, 'armor_c4': 0,
                         'movement_speed': [88, 100], 'attack_reload_time': [3, 2]})


def test_expand_integer_attr_single_set():
    rows = expand_attr_entries([dict(unit_const=329, players=[8], reason='',
                                     attrs={'hit_points': 110})])
    assert rows == [dict(unit_const=329, player=8, attribute=0, operation=1,
                         quantity=110, aaq=None, aac=None)]


def test_expand_attack_uses_armour_fields():
    rows = expand_attr_entries([dict(unit_const=74, players=[8], reason='',
                                     attrs={'attack_c4': 0})])
    r = rows[0]
    assert r['attribute'] == 9 and r['operation'] == 1
    assert r['quantity'] is None and r['aaq'] == 0 and r['aac'] == 4


def test_expand_fraction_set_then_divide_adjacent():
    rows = expand_attr_entries([dict(unit_const=1811, players=[3], reason='',
                                     attrs={'movement_speed': [88, 100]})])
    assert rows[0]['operation'] == 1 and rows[0]['quantity'] == 88 and rows[0]['attribute'] == 5
    assert rows[1]['operation'] == 5 and rows[1]['quantity'] == 100 and rows[1]['attribute'] == 5


def test_expand_counts():
    rows = expand_attr_entries([ENTRY_FIST])
    # 每玩家: hp(1)+attack(1)+armor(1)+speed(2)+reload(2)=7 → ×2 玩家=14
    assert len(rows) == 14


def test_expand_unknown_attr_raises():
    with pytest.raises(BuildError):
        expand_attr_entries([dict(unit_const=1, players=[1], reason='',
                                  attrs={'no_such_attr': 5})])


class FakeEffectFactory:
    def __init__(self):
        self.calls = []

    def modify_attribute(self, **kw):
        self.calls.append(kw)

    def send_chat(self, **kw):
        pass


def test_apply_builds_single_trigger_with_all_effects():
    made = {}

    def add_trigger(name, enabled=True, looping=False):
        t = NS(name=name, enabled=enabled, looping=looping,
               new_effect=FakeEffectFactory(),
               new_condition=NS(timer=lambda timer: None))
        made[name] = t
        return t

    tm = NS(add_trigger=add_trigger)
    changes = apply_attr_fixes(tm, [ENTRY_FIST])
    t = made['屬性校正']
    assert len(t.new_effect.calls) == 14
    assert all(c['object_list_unit_id'] == 1811 for c in t.new_effect.calls)
    assert len(changes) == 14


class FakeEffectFactory2(FakeEffectFactory):
    def change_object_hp(self, **kw):
        self.calls.append(('hp', kw))


def test_step_sets_gate_hp_per_ref():
    from steps.s36_attrfix import AttrFixStep
    made = {}

    def add_trigger(name, enabled=True, looping=False):
        t = NS(name=name, enabled=enabled, looping=looping,
               new_effect=FakeEffectFactory2(),
               new_condition=NS(timer=lambda timer: None))
        made[name] = t
        return t

    ctx = NS(base=NS(trigger_manager=NS(add_trigger=add_trigger)),
             spec=NS(params={'attr_fixes': [dict(unit_const=329, players=[8], reason='',
                                                 attrs={'hit_points': 110})],
                             'misc': {'gate_fix': {'hp': 2750}}}),
             notes={'gate_ref': 99999})
    changes = AttrFixStep().apply(ctx)
    hp_calls = [kw for tag, kw in [c for c in made['屬性校正'].new_effect.calls if isinstance(c, tuple)]
                if True]
    assert any(kw.get('selected_object_ids') == [99999] and kw.get('quantity') == 2750
               for kw in hp_calls)
    assert any(c.kind == 'gate_hp' for c in changes)

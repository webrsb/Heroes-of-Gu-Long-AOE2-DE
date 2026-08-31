# -*- coding: utf-8 -*-
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pytest
from types import SimpleNamespace as NS
from steps.s37_trigfix import apply_fix
from steps.base import BuildError


def _tm():
    t0 = NS(trigger_id=0, name='6馬召',
            conditions=[NS(condition_type=6, unit_object=8)],
            effects=[])
    t1 = NS(trigger_id=1, name='',
            conditions=[],
            effects=[NS(effect_type=27, selected_object_ids=[8, 99], source_player=6)])
    t2 = NS(trigger_id=2, name='4啞',
            conditions=[],
            effects=[NS(effect_type=3, selected_object_ids=[], source_player=5)])
    return NS(triggers=[t0, t1, t2])


def test_fix_condition_scalar():
    tm = _tm()
    c = apply_fix(tm, {'trigger_id': 0, 'name': '6馬召', 'kind': 'condition', 'index': 0,
                       'field': 'unit_object', 'old': 8, 'new': 45117, 'reason': 'r'})
    assert tm.triggers[0].conditions[0].unit_object == 45117
    assert c.field == 'unit_object' and c.old == '8' and c.new == '45117'


def test_fix_effect_list_replaces_only_old():
    tm = _tm()
    apply_fix(tm, {'trigger_id': 1, 'name': '', 'kind': 'effect', 'index': 0,
                   'field': 'selected_object_ids', 'old': 8, 'new': 45117, 'reason': 'r'})
    assert tm.triggers[1].effects[0].selected_object_ids == [45117, 99]


def test_fix_effect_player():
    tm = _tm()
    apply_fix(tm, {'trigger_id': 2, 'name': '4啞', 'kind': 'effect', 'index': 0,
                   'field': 'source_player', 'old': 5, 'new': 4, 'reason': 'r'})
    assert tm.triggers[2].effects[0].source_player == 4


def test_name_mismatch_raises():
    with pytest.raises(BuildError):
        apply_fix(_tm(), {'trigger_id': 0, 'name': '別支', 'kind': 'condition', 'index': 0,
                          'field': 'unit_object', 'old': 8, 'new': 45117, 'reason': 'r'})


def test_old_value_mismatch_raises():
    with pytest.raises(BuildError):
        apply_fix(_tm(), {'trigger_id': 0, 'name': '6馬召', 'kind': 'condition', 'index': 0,
                          'field': 'unit_object', 'old': 999, 'new': 45117, 'reason': 'r'})


def test_list_old_value_missing_raises():
    with pytest.raises(BuildError):
        apply_fix(_tm(), {'trigger_id': 1, 'name': '', 'kind': 'effect', 'index': 0,
                          'field': 'selected_object_ids', 'old': 777, 'new': 45117, 'reason': 'r'})


def test_list_old_replaces_whole_selection():
    tm = _tm()
    apply_fix(tm, {'trigger_id': 2, 'name': '4啞', 'kind': 'effect', 'index': 0,
                   'field': 'selected_object_ids', 'old': [], 'new': [502], 'reason': '空選取漏填ref'})
    assert tm.triggers[2].effects[0].selected_object_ids == [502]


def test_list_old_mismatch_raises():
    with pytest.raises(BuildError):
        apply_fix(_tm(), {'trigger_id': 1, 'name': '', 'kind': 'effect', 'index': 0,
                          'field': 'selected_object_ids', 'old': [], 'new': [502], 'reason': 'r'})


def test_effect_add_appends_deactivate_with_target_name_check():
    from tests.conftest import Recorder
    tm = _tm()
    tm.triggers[2].new_effect = Recorder()
    c = apply_fix(tm, {'trigger_id': 2, 'name': '4啞', 'kind': 'effect_add',
                       'effect': {'type': 'deactivate_trigger', 'trigger_id': 0, 'target_name': '6馬召'},
                       'reason': '放錯支補回'})
    assert tm.triggers[2].new_effect.calls == [('deactivate_trigger', {'trigger_id': 0})]
    assert c.kind == 'effect_add' and '6馬召' in c.new


def test_effect_add_target_name_mismatch_raises():
    from tests.conftest import Recorder
    tm = _tm()
    tm.triggers[2].new_effect = Recorder()
    with pytest.raises(BuildError):
        apply_fix(tm, {'trigger_id': 2, 'name': '4啞', 'kind': 'effect_add',
                       'effect': {'type': 'deactivate_trigger', 'trigger_id': 0, 'target_name': '別支'}, 'reason': 'r'})


def test_trigger_flag_looping():
    tm = _tm()
    tm.triggers[2].enabled, tm.triggers[2].looping = 1, 0
    c = apply_fix(tm, {'trigger_id': 2, 'name': '4啞', 'kind': 'trigger', 'field': 'looping',
                       'old': 0, 'new': 1, 'reason': '兄弟座位皆循環'})
    assert tm.triggers[2].looping == 1 and c.kind == 'trigger_flag'


def test_trigger_flag_old_mismatch_raises():
    tm = _tm()
    tm.triggers[2].enabled, tm.triggers[2].looping = 1, 1
    with pytest.raises(BuildError):
        apply_fix(tm, {'trigger_id': 2, 'name': '4啞', 'kind': 'trigger', 'field': 'looping',
                       'old': 0, 'new': 1, 'reason': 'r'})


def test_trigger_add_builds_conditions_and_effects(f):
    tm = f.tm([])
    c = apply_fix(tm, {'kind': 'trigger_add', 'name': '銀兩護欄5', 'enabled': 1, 'looping': 1,
                       'conditions': [{'type': 'accumulate_attribute', 'source_player': 5, 'quantity': 500000, 'attribute': 3}],
                       'effects': [{'type': 'tribute', 'source_player': 5, 'target_player': 0, 'quantity': 10000000, 'tribute_list': 3}],
                       'reason': '原作漏建'})
    t = tm.triggers[-1]
    assert t.name == '銀兩護欄5' and t.enabled == 1 and t.looping == 1
    assert t.new_condition.calls == [('accumulate_attribute', {'source_player': 5, 'quantity': 500000, 'attribute': 3})]
    assert t.new_effect.calls == [('tribute', {'source_player': 5, 'target_player': 0, 'quantity': 10000000, 'tribute_list': 3})]
    assert c.kind == 'trigger_add' and c.new.startswith(f'T{t.trigger_id}')


def test_trigger_add_effect_resolves_trigger_name(f):
    target = f.trig(name='1船入東')
    tm = f.tm([target])
    apply_fix(tm, {'kind': 'trigger_add', 'name': '1船窗止東', 'enabled': 0, 'looping': 0,
                   'conditions': [{'type': 'timer', 'timer': 180}],
                   'effects': [{'type': 'deactivate_trigger', 'trigger_name': '1船入東'}],
                   'reason': '售票窗'})
    t = tm.triggers[-1]
    assert t.new_effect.calls == [('deactivate_trigger', {'trigger_id': target.trigger_id})]


def test_effect_add_activate_by_trigger_name(f):
    target = f.trig(name='1船入東')
    buyer = f.trig(name='1船6')
    tm = f.tm([target, buyer])
    c = apply_fix(tm, {'trigger_id': buyer.trigger_id, 'name': '1船6', 'kind': 'effect_add',
                       'effect': {'type': 'activate_trigger', 'trigger_name': '1船入東'}, 'reason': 'r'})
    assert buyer.new_effect.calls == [('activate_trigger', {'trigger_id': target.trigger_id})]
    assert '1船入東' in c.new


def test_effect_add_send_chat(f):
    buyer = f.trig(name='1船6')
    tm = f.tm([buyer])
    c = apply_fix(tm, {'trigger_id': buyer.trigger_id, 'name': '1船6', 'kind': 'effect_add',
                       'effect': {'type': 'send_chat', 'source_player': 1, 'message': '<ORANGE>買票後三分鐘內踩旗'},
                       'reason': 'r'})
    assert buyer.new_effect.calls == [('send_chat', {'source_player': 1, 'message': '<ORANGE>買票後三分鐘內踩旗'})]
    assert c.kind == 'effect_add' and c.field == 'send_chat'


def test_effect_add_rejects_other_types(f):
    buyer = f.trig(name='1船6')
    with pytest.raises(BuildError):
        apply_fix(f.tm([buyer]), {'trigger_id': buyer.trigger_id, 'name': '1船6', 'kind': 'effect_add',
                                  'effect': {'type': 'teleport_object', 'source_player': 1}, 'reason': 'r'})


def test_trigger_add_effect_trigger_name_must_hit_exactly_one(f):
    a = f.trig(name='重名'); b = f.trig(name='重名')
    with pytest.raises(BuildError):
        apply_fix(f.tm([a, b]), {'kind': 'trigger_add', 'name': 'x', 'effects': [
            {'type': 'activate_trigger', 'trigger_name': '重名'}]})
    with pytest.raises(BuildError):
        apply_fix(f.tm([a]), {'kind': 'trigger_add', 'name': 'x', 'effects': [
            {'type': 'activate_trigger', 'trigger_name': '不存在'}]})


def test_effect_add_target_by_name_for_new_triggers(f):
    a = f.trig(name='1船血東')
    b = f.trig(name='1船費東')
    tm = f.tm([a, b])
    c = apply_fix(tm, {'kind': 'effect_add', 'target_name': '1船血東',
                       'effect': {'type': 'deactivate_trigger', 'trigger_name': '1船費東'},
                       'reason': '血不足拆掉扣費'})
    assert a.new_effect.calls == [('deactivate_trigger', {'trigger_id': b.trigger_id})]
    assert '1船費東' in c.new


def test_effect_add_target_name_must_hit_exactly_one(f):
    a = f.trig(name='重名'); b = f.trig(name='重名')
    with pytest.raises(BuildError):
        apply_fix(f.tm([a, b]), {'kind': 'effect_add', 'target_name': '重名',
                                 'effect': {'type': 'send_chat', 'source_player': 1, 'message': 'x'}})

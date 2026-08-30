# -*- coding: utf-8 -*-
"""s372 野怪獎勵補回：啟用修復、新獎勵/啟動器結構、出口追加停用（排除節流）、防呆。"""
import pytest
from steps.base import BuildError
from steps.s372_mobreward import apply_mob_rewards


def world(f):
    trigs = []
    for p in range(1, 7):
        trigs.append(f.trig(tid=100 + p, name=f'{p}升級', enabled=False,
                            conds=[f.cond_accumulate(sp=p, qty=1, attribute=44)]))
        trigs.append(f.trig(tid=200 + p, name=f'{p}青', enabled=False,
                            conds=[f.cond_accumulate(sp=p, qty=1, attribute=44), f.cond_timer(2)],
                            effects=[f.eff_tribute(sp=p, tp=0, quantity=-30)]))
        trigs.append(f.trig(tid=300 + p, name=f'{p}青死', looping=True,
                            conds=[f.cond_area(sp=p, area=(74, 61, 100, 67))],
                            effects=[f.eff_deactivate(200 + p)]))
        trigs.append(f.trig(tid=400 + p, name=f'{p}青3', looping=True,
                            conds=[f.cond_timer(6)], effects=[f.eff_deactivate(200 + p)]))
        trigs.append(f.trig(tid=500 + p, name=f'{p}獅頭人2', enabled=False, looping=True))
    return f.tm(trigs)


PARAMS = dict(
    enable_triggers=[{'trigger_id': 500 + p, 'name': f'{p}獅頭人2'} for p in range(1, 7)],
    upgrade={p: 100 + p for p in range(1, 7)},
    zones=[dict(key='狼', xp=16, silver=15, areas=[[77, 45, 103, 61]],
                quest_reward={p: 200 + p for p in range(1, 7)},
                quest_name_suffix='青', exclude_exit_suffix='青3')])


def test_enable_triggers(f):
    tm = world(f)
    apply_mob_rewards(tm, PARAMS)
    assert all(tm.triggers_by_id[500 + p].enabled == 1 for p in range(1, 7))


def test_reward_and_activator_structure(f):
    tm = world(f)
    apply_mob_rewards(tm, PARAMS)
    r = next(t for t in tm.triggers if t.name == '3狼獎')
    assert r.enabled == 0 and r.looping == 0
    conds = r.new_condition.calls
    assert conds[0] == ('accumulate_attribute', dict(quantity=1, attribute=44, source_player=3))
    assert conds[1][1]['timer'] == 2
    effs = {n: kw for n, kw in r.new_effect.calls}
    tribs = [kw for n, kw in r.new_effect.calls if n == 'tribute']
    assert [(kw['tribute_list'], kw['quantity'], kw['source_player'], kw['target_player']) for kw in tribs] \
        == [(2, -16, 3, 0), (3, -15, 3, 0)]
    assert effs['activate_trigger']['trigger_id'] == 103
    chats = [kw['message'] for n, kw in r.new_effect.calls if n == 'send_chat']
    assert '16' in chats[0] and '15' in chats[1]
    a = next(t for t in tm.triggers if t.name == '3狼獎2')
    assert a.enabled == 1 and a.looping == 1
    ac = a.new_condition.calls[0][1]
    assert (ac['source_player'], ac['area_x1'], ac['area_y1'], ac['area_x2'], ac['area_y2']) == (3, 77, 45, 103, 61)
    assert a.new_effect.calls[0][1]['trigger_id'] == r.trigger_id


def test_exits_get_deactivate_but_throttle_excluded(f):
    tm = world(f)
    apply_mob_rewards(tm, PARAMS)
    r = next(t for t in tm.triggers if t.name == '2狼獎')
    exit_t = tm.triggers_by_id[302]
    assert [kw['trigger_id'] for n, kw in exit_t.new_effect.calls if n == 'deactivate_trigger'] == [r.trigger_id]
    throttle = tm.triggers_by_id[402]
    assert throttle.new_effect.calls == []


def test_multi_area_makes_multiple_activators(f):
    tm = world(f)
    params = dict(PARAMS, zones=[dict(PARAMS['zones'][0], key='石',
                                      areas=[[188, 225, 210, 239], [227, 212, 239, 225]])])
    apply_mob_rewards(tm, params)
    names = {t.name for t in tm.triggers}
    assert {'1石獎', '1石獎2', '1石獎3'} <= names


def test_name_mismatch_raises(f):
    tm = world(f)
    bad = dict(PARAMS, enable_triggers=[{'trigger_id': 501, 'name': '不對'}])
    with pytest.raises(BuildError):
        apply_mob_rewards(tm, bad)


def test_already_enabled_raises(f):
    tm = world(f)
    tm.triggers_by_id[501].enabled = 1
    with pytest.raises(BuildError):
        apply_mob_rewards(tm, PARAMS)


def test_no_exit_raises(f):
    tm = world(f)
    for p in range(1, 7):
        tm.triggers_by_id[300 + p].effects = []
    with pytest.raises(BuildError):
        apply_mob_rewards(tm, PARAMS)

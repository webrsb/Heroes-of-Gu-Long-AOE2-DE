# -*- coding: utf-8 -*-
"""s375 擊殺獎勵變數化：KR 條件→比較變數、Joan 重置→基準遞增、計數迴圈、防呆。"""
import pytest
from steps.base import BuildError
from steps.s375_killvar import apply_killvar, var_slot_rewrite

PARAMS = dict(reset_tids=[7], kills_attr=20, v_kills_offset=0, v_base_offset=10)


def reset_trig(f, tid=7, sp=1):
    return f.trig(tid=tid, name=f'{sp}升級', enabled=False, conds=[f.cond_accumulate(sp=sp, qty=1, attribute=44)],
                  effects=[f.eff_create(sp=sp, olu=430, x=239, y=239),
                           f.eff_kill(sp=sp, area=(239, 239, 239, 239)),
                           f.eff_remove(sp=sp, area=(239, 239, 239, 239)),
                           f.eff_deactivate(tid)])


def test_kr_condition_converted_to_compare_variables(f):
    reward = f.trig(name='1打民團', conds=[f.cond_accumulate(sp=1, qty=1, attribute=44), f.cond_timer(2)],
                    effects=[f.eff_tribute(sp=1, tp=0, quantity=-2)])
    other = f.trig(conds=[f.cond_accumulate(sp=1, qty=100, attribute=2)])   # 石頭門檻不動
    tm = f.tm([reset_trig(f), reward, other])
    apply_killvar(tm, PARAMS)
    c = reward.conditions[0]
    assert c.condition_type == 78 and c.variable == 1 and c.variable2 == 11 and c.comparison == 2
    assert c.attribute == -1 and c.quantity == -1
    assert reward.conditions[1].condition_type == 10
    assert other.conditions[0].condition_type == 8 and other.conditions[0].attribute == 2
    assert {v.variable_id for v in tm.variables} == set(range(1, 7)) | set(range(11, 17))


def test_reset_trigger_rewritten_to_base_increment(f):
    r = reset_trig(f)
    tm = f.tm([r])
    apply_killvar(tm, PARAMS)
    assert [e.effect_type for e in r.effects[:3]] == [0, 0, 0]          # Joan 建/殺/移 全中和
    assert r.effects[3].effect_type == 9                                 # 自停保留
    cv = [kw for n, kw in r.new_effect.calls if n == 'change_variable']
    assert cv == [dict(quantity=1, operation=2, variable=11)]


def test_counter_loop_trigger(f):
    tm = f.tm([reset_trig(f)])
    apply_killvar(tm, PARAMS)
    loop = next(t for t in tm.triggers if t.name == '擊殺計數迴圈')
    assert loop.enabled == 1 and loop.looping == 1
    calls = [kw for n, kw in loop.new_effect.calls if n == 'modify_variable_by_resource']
    assert [(kw['source_player'], kw['variable']) for kw in calls] == [(s, s) for s in range(1, 7)]
    assert all(kw['tribute_list'] == 20 and kw['operation'] == 1 for kw in calls)


def test_nonstandard_kr_condition_raises(f):
    bad = f.trig(conds=[f.cond_accumulate(sp=1, qty=2, attribute=44)])
    with pytest.raises(BuildError):
        apply_killvar(f.tm([reset_trig(f), bad]), PARAMS)


def test_existing_variable_usage_raises(f):
    v = f.trig(conds=[f._cond(22, variable=3, quantity=1)])
    with pytest.raises(BuildError):
        apply_killvar(f.tm([reset_trig(f), v]), PARAMS)


def test_reset_pattern_mismatch_raises(f):
    notreset = f.trig(tid=7, conds=[f.cond_accumulate(sp=1, qty=1, attribute=44)],
                      effects=[f.eff_chat(sp=1)])
    with pytest.raises(BuildError):
        apply_killvar(f.tm([notreset]), PARAMS)


def test_var_slot_rewrite(f):
    c = f._cond(78, variable=2, variable2=12, comparison=2)
    assert var_slot_rewrite(c, 2, 5, (0, 10))
    assert (c.variable, c.variable2) == (5, 15)
    e = f._eff(56, variable=13)
    assert not var_slot_rewrite(e, 2, 5, (0, 10))          # 不是 cid 2 的變數不動
    assert e.variable == 13

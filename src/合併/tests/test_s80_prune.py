# -*- coding: utf-8 -*-
"""s80 清空殼：管線中和（effect_type=0）的效果在寫檔前真刪，display order 正確重排。

背景：s39/s375 為保住步驟內索引把效果就地中和成 type 0；殼寫進檔案後 DE 編輯器整支觸發紅字。
parser 的 remove_effect 刪除後只過濾 order 不重排（非恆等順序會錯位），故本步自己重排。"""
from steps.s80_prune import prune_empty_effects


def empty(f):
    return f._eff(0)


def test_removes_empty_effects_keeps_others_in_place(f):
    a, b, c = f.eff_chat(message='a'), f.eff_chat(message='b'), f.eff_chat(message='c')
    t = f.trig(effects=[a, empty(f), b, empty(f), empty(f), c])
    changes = prune_empty_effects(f.tm([t]))
    assert t.effects == [a, b, c]
    assert len(changes) == 1 and changes[0].kind == 'eff_prune'
    assert changes[0].target == 'T0' and changes[0].old == '6' and changes[0].new == '3'


def test_untouched_trigger_yields_no_change(f):
    a = f.eff_chat(message='a')
    t = f.trig(effects=[a])
    assert prune_empty_effects(f.tm([t])) == []
    assert t.effects == [a]


def test_remaps_non_identity_display_order(f):
    e0, e2, e3 = f.eff_chat(message='0'), f.eff_chat(message='2'), f.eff_chat(message='3')
    t = f.trig(effects=[e0, empty(f), e2, e3])
    t.effect_order = [2, 0, 1, 3]          # 顯示順序：e2, e0, 殼, e3
    prune_empty_effects(f.tm([t]))
    assert t.effects == [e0, e2, e3]
    assert t.effect_order == [1, 0, 2]     # 顯示順序仍是 e2, e0, e3


def test_identity_order_stays_identity(f):
    t = f.trig(effects=[empty(f), f.eff_chat(message='x'), empty(f), f.eff_chat(message='y')])
    t.effect_order = [0, 1, 2, 3]
    prune_empty_effects(f.tm([t]))
    assert [e.message for e in t.effects] == ['x', 'y'] and t.effect_order == [0, 1]


def test_all_effects_empty_leaves_trigger_with_none(f):
    t = f.trig(effects=[empty(f), empty(f)])
    t.effect_order = [1, 0]
    prune_empty_effects(f.tm([t]))
    assert t.effects == [] and t.effect_order == []

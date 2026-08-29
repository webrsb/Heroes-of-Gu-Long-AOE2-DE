# -*- coding: utf-8 -*-
"""T6: revive_inventory 五類盤點——家族/可追加/指令型/OR條件/locref/定址/閉包/
死亡連動/全域初始化/const過濾/退役排除/跨職業。"""
from analysis.revive_inventory import build_inventory

HERO_REFS = {1: 0, 2: 1, 3: 2, 4: 502, 5: 7, 6: 45117}
HERO_CONSTS = {1: 845, 2: 432, 3: 752, 4: 428, 5: 1811, 6: 765}


def inv_of(f, trigs, exclude=()):
    return build_inventory(f.tm(trigs), HERO_REFS, HERO_CONSTS, exclude=list(exclude))


def test_family_assignment_single_class(f):
    t = f.trig(effects=[f.eff_rename(sel=[0])])
    inv = inv_of(f, [t])
    assert t.trigger_id in inv.families[1]


def test_appendable_vs_command_split(f):
    t = f.trig(effects=[f.eff_rename(sel=[0]), f.eff_stop(sel=[0]), f.eff_hp(sel=[0])])
    inv = inv_of(f, [t])
    assert (t.trigger_id, 0, 1) in inv.eff_list_appendable
    assert (t.trigger_id, 2, 1) in inv.eff_list_appendable
    assert (t.trigger_id, 1, 1, 29) in inv.eff_list_command


def test_cond_ref_and_locref_collected(f):
    t = f.trig(conds=[f.cond_bring_area(45117)],
               effects=[f.eff_task(sel=[123], sp=6, locref=45117)])
    inv = inv_of(f, [t])
    assert (t.trigger_id, 0, 'unit_object', 6) in inv.cond_ref
    assert (t.trigger_id, 0, 6) in inv.locref


def test_addressed_rules(f):
    t_chat = f.trig(effects=[f.eff_chat(sp=1)])                       # sp∈1..6 且 sel 空
    t_own = f.trig(effects=[f.eff_ownership(sel=[29332], sp=8, tp=6)])  # tp∈1..6 不論 sel
    t_neutral = f.trig(effects=[f.eff_rename(sel=[0], sp=1)])         # sp 但 sel 非空 → 可中性化
    t_cond = f.trig(conds=[f.cond_accumulate(sp=2, qty=100)],
                    effects=[f.eff_rename(sel=[1])])                  # 條件玩家欄
    inv = inv_of(f, [t_chat, t_own, t_neutral, t_cond])
    assert t_chat.trigger_id in inv.addressed[1]
    assert t_own.trigger_id in inv.addressed[6]
    assert t_neutral.trigger_id not in inv.addressed.get(1, set())
    assert t_cond.trigger_id in inv.addressed[2]


def test_closure_pulls_activator_into_matrix(f):
    t0 = f.trig(effects=[f.eff_rename(sel=[0])])                      # 純ref → shared
    t1 = f.trig(effects=[f.eff_chat(sp=1), f.eff_rename(sel=[0])])    # addressed
    t2 = f.trig(effects=[f.eff_activate(t1.trigger_id), f.eff_rename(sel=[0])])
    inv = inv_of(f, [t0, t1, t2])
    assert t1.trigger_id in inv.matrix[1]
    assert t2.trigger_id in inv.matrix[1]     # 閉包（啟動者被拉入）
    assert t0.trigger_id in inv.shared[1]


def test_death_linked_detection_and_exclusion_from_expansion(f):
    td = f.trig(conds=[f.cond_destroy(0)], effects=[f.eff_task(sel=[123], sp=1)])
    inv = inv_of(f, [td])
    assert td.trigger_id in inv.death_linked[1]
    # 死亡連動的 destroy 條件不得進 cond_ref（§七之二：不做命展開）
    assert all(tid != td.trigger_id for tid, *_ in inv.cond_ref)


def test_global_init_forced_out_of_matrix(f):
    t = f.trig(conds=[], effects=[f.eff_task(sel=(), sp=p) for p in range(1, 7)])
    inv = inv_of(f, [t])
    assert t.trigger_id in inv.global_init
    assert all(t.trigger_id not in inv.matrix.get(c, set()) for c in range(1, 7))


def test_retired_excluded_everywhere(f):
    t = f.trig(conds=[f.cond_destroy(0)], effects=[f.eff_create(sp=1, olu=837)])
    inv = inv_of(f, [t], exclude=[t.trigger_id])
    assert t.trigger_id not in inv.death_linked.get(1, set())
    assert t.trigger_id not in inv.families.get(1, set())
    assert all(tid != t.trigger_id for tid, *_ in inv.eff_list_appendable)


def test_const_filtered_nonfamily(f):
    # 船塢型：非家族觸發（多職業或非 1..6 玩家欄）以本體 const 過濾
    t = f.trig(effects=[f.eff_remove(olu=765, sp=8, area=(57, 187, 73, 196))])
    inv = inv_of(f, [t])
    assert any(tid == t.trigger_id and cid == 6 for tid, where, cid in inv.const_filtered)
    t2 = f.trig(effects=[f.eff_remove(olu=765, sp=p2, area=(57, 187, 73, 196))
                         for p2 in (1, 2, 3)])                       # 多職業＝cross 亦非家族
    inv2 = inv_of(f, [t2])
    assert any(tid == t2.trigger_id for tid, where, cid in inv2.const_filtered)
    assert t2.trigger_id in inv2.cross


def test_const_filtered_skips_family_triggers(f):
    # 家族觸發（引用本體 ref）同時帶 const 過濾 → 不重複列入 const_filtered
    t = f.trig(conds=[f.cond_area(sp=8, object_list=845)],
               effects=[f.eff_rename(sel=[0])])
    inv = inv_of(f, [t])
    assert t.trigger_id in inv.families[1]
    assert all(tid != t.trigger_id for tid, *_ in inv.const_filtered)


def test_cross_detection(f):
    t = f.trig(effects=[f.eff_rename(sel=[0]), f.eff_rename(sel=[1])])   # 碰 2 職業
    t_all = f.trig(effects=[f.eff_rename(sel=[HERO_REFS[c]]) for c in range(1, 7)])
    inv = inv_of(f, [t, t_all])
    assert t.trigger_id in inv.cross
    assert t_all.trigger_id not in inv.cross    # 六家全包=世界觸發，不算 cross

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


def test_death_linked_not_in_matrix(f):
    # 連動觸發帶玩家欄（哥8型）→ addressed，但不得進 matrix（狀態機獨佔）
    td = f.trig(conds=[f.cond_destroy(0)], effects=[f.eff_ownership(sel=[29332], sp=8, tp=1)])
    inv = inv_of(f, [td])
    assert td.trigger_id in inv.death_linked[1]
    assert td.trigger_id not in inv.matrix.get(1, set())


def test_global_init_still_const_scanned(f):
    # 船塢型：全包世界觸發帶本體 const 過濾 → 仍須進 const_filtered
    t = f.trig(conds=[], effects=[f.eff_remove(olu=765, sp=p2, area=(57, 187, 73, 196))
                                  for p2 in range(1, 7)])
    inv = inv_of(f, [t])
    assert t.trigger_id in inv.global_init
    assert any(tid == t.trigger_id for tid, where, cid in inv.const_filtered)


def test_cross_detection(f):
    t = f.trig(effects=[f.eff_rename(sel=[0]), f.eff_rename(sel=[1])])   # 碰 2 職業
    t_all = f.trig(effects=[f.eff_rename(sel=[HERO_REFS[c]]) for c in range(1, 7)])
    inv = inv_of(f, [t, t_all])
    assert t.trigger_id in inv.cross
    assert t_all.trigger_id not in inv.cross    # 六家全包=世界觸發，不算 cross


def test_neutral_relay_adopted_into_family_and_matrix(f):
    """5教頭2 第二階型：只有計時器＋啟停邊、零玩家欄位的中繼，啟停目標全在單一職業家族 → 併入家族並進矩陣。"""
    t_addr = f.trig(conds=[f.cond_timer(14), f.cond_area(sp=5, qty=1)], effects=[f.eff_chat(sp=5)])
    relay = f.trig(conds=[f.cond_timer(14)], effects=[f.eff_activate(t_addr.trigger_id)])
    relay2 = f.trig(conds=[f.cond_timer(3)], effects=[f.eff_deactivate(relay.trigger_id)])   # 中繼串中繼
    inv = inv_of(f, [t_addr, relay, relay2])
    assert relay.trigger_id in inv.families[5] and relay.trigger_id in inv.matrix[5]
    assert relay2.trigger_id in inv.matrix[5]


def test_neutral_relay_to_two_classes_stays_cross(f):
    a = f.trig(effects=[f.eff_chat(sp=1)])
    b = f.trig(effects=[f.eff_chat(sp=2)])
    relay = f.trig(conds=[f.cond_timer(1)], effects=[f.eff_activate(a.trigger_id), f.eff_activate(b.trigger_id)])
    inv = inv_of(f, [a, b, relay])
    assert relay.trigger_id not in inv.families.get(1, set()) and relay.trigger_id not in inv.families.get(2, set())
    assert relay.trigger_id in inv.relay_cross


def test_neutral_relay_with_self_deactivate_adopted(f):
    """X木3 型：計時器→啟動 X木1、停用自己。自我邊不該擋住併入。"""
    t_addr = f.trig(conds=[f.cond_area(sp=1, qty=1)], effects=[f.eff_chat(sp=1)])
    relay = f.trig(tid=77, conds=[f.cond_timer(20)], effects=[f.eff_activate(t_addr.trigger_id), f.eff_deactivate(77)])
    inv = inv_of(f, [t_addr, relay])
    assert 77 in inv.families[1] and 77 in inv.matrix[1]

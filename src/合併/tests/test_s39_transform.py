# -*- coding: utf-8 -*-
"""T7: s39 接線改造引擎——矩陣複製/玩家欄改寫/內部重指/啟動表、
ref 追加（僅可追加型）、OR 展開（單條件；多條件退每命複製）、locref 逐命複製。
執行順序契約：build_matrix 先跑，append/expand/dup 全表掃描（含變體）。"""
from steps.s39_revive import (append_life_refs, expand_conditions, dup_locref, build_matrix)

LIFE = {1: [0, 900, 901], 2: [1, 910, 911], 6: [45117, 960, 961]}


# ---------- append_life_refs ----------

def test_append_only_appendable_types(f):
    e_ok = f.eff_rename(sel=[0], sp=1)
    e_cmd = f.eff_stop(sel=[0], sp=1)
    tm = f.tm([f.trig(effects=[e_ok, e_cmd])])
    append_life_refs(tm, LIFE)
    assert e_ok.selected_object_ids == [0, 900, 901]
    assert e_ok.source_player == -1
    assert e_cmd.selected_object_ids == [0]           # 指令型不追加
    assert e_cmd.source_player == 1                   # 也不中性化


def test_append_skips_duplicates_and_skip_tids(f):
    e = f.eff_hp(sel=[0, 900], sp=1)
    t = f.trig(effects=[e])
    t2 = f.trig(effects=[f.eff_hp(sel=[1], sp=2)])
    tm = f.tm([t, t2])
    append_life_refs(tm, LIFE, skip_tids={t2.trigger_id})
    assert e.selected_object_ids == [0, 900, 901]     # 不重複追加 900
    assert tm.triggers_by_id[t2.trigger_id].effects[0].selected_object_ids == [1]


# ---------- expand_conditions ----------

def test_or_expansion_single_condition(f):
    c = f.cond_bring_area(0, area=(5, 5, 8, 8))
    other = f.cond_timer(3)
    t = f.trig(conds=[c, other])
    tm = f.tm([t])
    changes, dups = expand_conditions(tm, LIFE, death_linked=set())
    # ref 條件被移到尾端後接 OR 副本： [timer, ref0, OR, ref900, OR, ref901]
    types = [x.condition_type for x in t.conditions]
    assert types == [10, 1, 29, 1, 29, 1]
    assert [x.unit_object for x in t.conditions if x.condition_type == 1] == [0, 900, 901]
    assert dups == {}


def test_or_expansion_next_object_field(f):
    c = f.cond_bring_obj(123, 45117)                  # next_object=暗本體
    t = f.trig(conds=[c])
    tm = f.tm([t])
    expand_conditions(tm, LIFE, death_linked=set())
    assert [x.next_object for x in t.conditions if x.condition_type == 2] == [45117, 960, 961]


def test_multi_ref_conditions_fall_back_to_per_life_copies(f):
    t = f.trig(conds=[f.cond_bring_area(0), f.cond_bring_area(0, area=(1, 1, 2, 2))],
               enabled=True)
    tm = f.tm([t])
    changes, dups = expand_conditions(tm, LIFE, death_linked=set())
    assert len(t.conditions) == 2                     # 原觸發不 OR
    assert set(dups[t.trigger_id]) == {2, 3}          # L=2,3 兩份副本（L=1=原觸發）
    for L, vid in dups[t.trigger_id].items():
        v = tm.triggers_by_id[vid]
        assert all(x.unit_object == LIFE[1][L - 1] for x in v.conditions)
        assert v.enabled == t.enabled


def test_death_linked_not_expanded(f):
    t = f.trig(conds=[f.cond_destroy(0)])
    tm = f.tm([t])
    changes, dups = expand_conditions(tm, LIFE, death_linked={t.trigger_id})
    assert len(t.conditions) == 1 and dups == {}


# ---------- dup_locref ----------

def test_dup_locref_per_life_gated(f):
    t = f.trig(effects=[f.eff_task(sel=[555], sp=1, locref=0)], enabled=True)
    tm = f.tm([t])
    changes, gates = dup_locref(tm, LIFE)
    # 原觸發＝L1 拷貝（保持 enabled），L2/L3 副本 disabled 等鏈啟用
    assert gates[(1, 1)] == [t.trigger_id]
    for L in (2, 3):
        vid = gates[(1, L)][0]
        v = tm.triggers_by_id[vid]
        assert v.effects[0].location_object_reference == LIFE[1][L - 1]
        assert v.enabled == 0


# ---------- build_matrix ----------

def inv_matrix(f, sets):
    from types import SimpleNamespace as NS
    return NS(matrix=sets)


def test_matrix_rewrites_sp_and_tp(f):
    t = f.trig(effects=[f.eff_chat(sp=2), f.eff_ownership(sel=[7], sp=8, tp=2)])
    tm = f.tm([t])
    vm, el, ch = build_matrix(tm, {2: {t.trigger_id}})
    v = tm.triggers_by_id[vm[(t.trigger_id, 5)]]
    assert v.effects[0].source_player == 5
    assert v.effects[1].source_player == 8 and v.effects[1].target_player == 5
    assert vm[(t.trigger_id, 2)] == t.trigger_id      # slot==class → 原觸發


def test_matrix_rewrites_condition_player(f):
    t = f.trig(conds=[f.cond_accumulate(sp=3, qty=100)], effects=[f.eff_chat(sp=3)])
    tm = f.tm([t])
    vm, el, ch = build_matrix(tm, {3: {t.trigger_id}})
    v = tm.triggers_by_id[vm[(t.trigger_id, 1)]]
    assert v.conditions[0].source_player == 1


def test_matrix_repoints_internal_activation(f):
    a = f.trig(effects=[f.eff_chat(sp=1)])
    b = f.trig(effects=[f.eff_activate(a.trigger_id), f.eff_chat(sp=1)])
    tm = f.tm([a, b])
    vm, el, ch = build_matrix(tm, {1: {a.trigger_id, b.trigger_id}})
    vb = tm.triggers_by_id[vm[(b.trigger_id, 4)]]
    assert vb.effects[0].trigger_id == vm[(a.trigger_id, 4)]
    # 原觸發（slot==1）內部指向不變
    assert b.effects[0].trigger_id == a.trigger_id


def test_matrix_disables_all_and_enable_lists_originally_enabled(f):
    a = f.trig(enabled=True, effects=[f.eff_chat(sp=1)])
    b = f.trig(enabled=False, effects=[f.eff_chat(sp=1)])
    tm = f.tm([a, b])
    vm, el, ch = build_matrix(tm, {1: {a.trigger_id, b.trigger_id}})
    for s in range(1, 7):
        assert tm.triggers_by_id[vm[(a.trigger_id, s)]].enabled == 0
        assert tm.triggers_by_id[vm[(b.trigger_id, s)]].enabled == 0
        assert el[(1, s)] == [vm[(a.trigger_id, s)]]


def test_matrix_declares_trigger_add_changes(f):
    a = f.trig(effects=[f.eff_chat(sp=1)])
    tm = f.tm([a])
    vm, el, ch = build_matrix(tm, {1: {a.trigger_id}})
    assert sum(1 for c in ch if c.kind == 'trigger_add') == 5   # 六位減原本一位

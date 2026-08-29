# -*- coding: utf-8 -*-
"""T9b-ii 補充：effect_splits 雙模式（follow/anti）與選角 anti 停用。"""
from steps.revive_mount import split_effects
from steps.revive_chains import build_chains
from types import SimpleNamespace as NS


def dock(f):
    # 模擬船塢：E0=P7雜項、E1=765防呆(sp=4)、E2=反召喚(sp=6 僧侶類)
    return f.trig(tid=3672, name='船塢', looping=True, enabled=True, effects=[
        f.eff_task(sel=(), sp=7, x=1, y=1),
        f.eff_remove(sel=(), sp=4, olu=765, area=(57, 187, 73, 196)),
        f.eff_remove(sel=(), sp=6, olu=-1, area=(57, 187, 73, 196))])


def test_anti_mode_enabled_by_default(f):
    t = dock(f)
    tm = f.tm([t])
    enable_lists, anti_lists = {}, {}
    split_effects(tm, [dict(tid=3672, effect_index=1, class_id=6, expect_sp=4,
                            expect_type=15, gate='anti', reason='765防呆')],
                  enable_lists, anti_lists=anti_lists, slots=(1, 2))
    assert t.effects[1].effect_type == 0                 # 本體抽除
    # anti：per 位常駐變體；(箭俠=6, S) 配對時停用 S 位那支
    assert set(anti_lists) == {(6, 1), (6, 2)}
    v1 = tm.triggers_by_id[anti_lists[(6, 1)][0]]
    assert v1.enabled == 1 and v1.looping == 1
    # 泛型複製：除靶效果外全部中和；靶效果 sp 改寫為該位
    live = [e for e in v1.effects if e.effect_type != 0]
    assert len(live) == 1 and live[0].effect_type == 15
    assert live[0].source_player == 1 and live[0].object_list_unit_id == 765


def test_follow_mode_disabled_and_gated(f):
    t = dock(f)
    tm = f.tm([t])
    enable_lists, anti_lists = {(6, 1): [], (6, 2): []}, {}
    split_effects(tm, [dict(tid=3672, effect_index=2, class_id=6, expect_sp=6,
                            expect_type=15, gate='follow', reason='反召喚')],
                  enable_lists, anti_lists=anti_lists, slots=(1, 2))
    v2 = tm.triggers_by_id[enable_lists[(6, 2)][0]]
    assert v2.enabled == 0
    live = [e for e in v2.effects if e.effect_type != 0]
    assert live[0].source_player == 2


def test_selection_deactivates_anti_variants(f):
    tm = f.tm([f.trig(tid=501, name='無敵1', looping=True)])
    rv = dict(spec=NS(lives=2, respawn=(77.5, 103.5), hero_refs={1: 0},
                      displays={1: (78.5, 108.5)}),
              life_refs={1: [0, 900]}, containers={1: [800]},
              class_names={1: ('刀客', '刀俠')}, invuln_tids={1: 501},
              base_hp={1: 190}, enable_lists={(1, 1): [], (1, 2): []},
              anti_lists={(1, 2): [9999]},
              mount={1: dict(mount_ref=26109, flag_cell=(221, 239),
                             rebirth_cell=(230, 239), final_cell=(232, 239))},
              classes=(1,), slots=(1, 2))
    out = build_chains(tm, rv)
    sel = tm.triggers_by_id[out.select[(1, 2)]]
    deacts = {kw['trigger_id'] for n, kw in sel.new_effect.calls if n == 'deactivate_trigger'}
    assert 9999 in deacts
    sel1 = tm.triggers_by_id[out.select[(1, 1)]]
    d1 = {kw['trigger_id'] for n, kw in sel1.new_effect.calls if n == 'deactivate_trigger'}
    assert 9999 not in d1

# -*- coding: utf-8 -*-
"""T9b-i: 死亡連動變體建造器——a/b/c_flag 三類（flag_swap 走矩陣＋條件換裝後處理）。
規則（spec §七之二＋裁決表）：
- a/b：per (C,S) 變體、destroy 條件原地轉 timer(0)、玩家欄改寫、enabled=0，
  掛勾 watch_activate＋timer_deactivate；b 保留其餘條件（OWN 閘門）。
- c_flag：destroy 條件原地轉「命盡旗標讀取」、保留原 enabled、玩家欄改寫，
  quest 啟停邊由跨集重指處理（本模組輸出 dl_variant_map 供其用）。
- extras 含「剝除E{i}空REMOVE」→ 該效果原地轉 effect_type=0（None）。"""
from steps.dl_variants import build_death_linked, convert_flag_swap_conditions

MOUNT = {1: dict(mount_ref=26109, flag_cell=(221, 239), rebirth_cell=(230, 239),
                 final_cell=(232, 239))}
HERO_REFS = {1: 0}


def rulings(*rows):
    return list(rows)


def test_a_type_variant(f):
    t = f.trig(tid=4192, name='1召',
               conds=[f.cond_destroy(0)],
               effects=[f.eff_remove(sel=[12697], sp=1)])
    tm = f.tm([t])
    out = build_death_linked(tm, rulings(dict(tid=4192, name='1召', category='a', extras='')),
                             hero_refs=HERO_REFS, mount=MOUNT, slots=(1, 2))
    v = tm.triggers_by_id[out.variant_map[(4192, 2)]]
    assert v.enabled == 0
    assert v.conditions[0].condition_type == 10 and v.conditions[0].timer == 0   # destroy→timer0
    assert v.effects[0].source_player == 2                                        # 玩家欄改寫
    assert out.variant_map[(4192, 1)] != 4192      # slot==class 也建變體（原觸發退役停用）
    orig = tm.triggers_by_id[4192]
    assert orig.enabled == 0 and orig.name.startswith('退役_')
    hk = out.hooks[(1, 2)]
    assert out.variant_map[(4192, 2)] in hk['watch_activate']
    assert out.variant_map[(4192, 2)] in hk['timer_deactivate']


def test_b_type_keeps_other_conditions(f):
    t = f.trig(tid=4896, name='修端木1',
               conds=[f.cond_area(sp=1, object_list=840), f.cond_destroy(0)],
               effects=[f.eff_ownership(sel=[37096], sp=1, tp=0)],
               looping=True, enabled=True)
    tm = f.tm([t])
    out = build_death_linked(tm, rulings(dict(tid=4896, name='修端木1', category='b', extras='')),
                             hero_refs=HERO_REFS, mount=MOUNT, slots=(1, 2))
    v = tm.triggers_by_id[out.variant_map[(4896, 2)]]
    assert v.looping == 1 and v.enabled == 0
    assert v.conditions[0].condition_type == 5 and v.conditions[0].source_player == 2
    assert v.conditions[1].condition_type == 10 and v.conditions[1].timer == 0


def test_c_flag_reads_final_flag_and_keeps_enabled(f):
    t = f.trig(tid=4204, name='1哥8', enabled=False,
               conds=[f.cond_destroy(0)],
               effects=[f.eff_ownership(sel=[29334], sp=8, tp=1)])
    tm = f.tm([t])
    out = build_death_linked(tm, rulings(dict(tid=4204, name='1哥8', category='c_flag', extras='')),
                             hero_refs=HERO_REFS, mount=MOUNT, slots=(1, 2))
    v = tm.triggers_by_id[out.variant_map[(4204, 2)]]
    c = v.conditions[0]
    assert c.condition_type == 5 and c.object_list == 720
    assert (c.area_x1, c.area_y1) == (232, 239)                 # final_cell
    assert v.enabled == 0                                        # 沿用原 enabled（哥5 啟動）
    assert v.effects[0].target_player == 2
    hk = out.hooks.get((1, 2), {})
    assert v.trigger_id not in hk.get('watch_activate', [])      # c_flag 不掛 watch


def test_strip_empty_remove_extras(f):
    t = f.trig(tid=4898, name='修端木2', looping=True,
               conds=[f.cond_destroy(1)],
               effects=[f.eff_ownership(sel=[37096], sp=2, tp=0),
                        f.eff_remove(sel=(), sp=2)])
    tm = f.tm([t])
    out = build_death_linked(tm, rulings(dict(tid=4898, name='修端木2', category='b',
                                              extras='剝除E1空REMOVE')),
                             hero_refs={2: 1}, mount={2: MOUNT[1]}, slots=(1, 2))
    v = tm.triggers_by_id[out.variant_map[(4898, 1)]]
    assert v.effects[1].effect_type == 0                         # 原地轉 None


def test_name_guard_raises(f):
    from steps.base import BuildError
    import pytest
    t = f.trig(tid=4192, name='名字不對', conds=[f.cond_destroy(0)])
    tm = f.tm([t])
    with pytest.raises(BuildError):
        build_death_linked(tm, rulings(dict(tid=4192, name='1召', category='a', extras='')),
                           hero_refs=HERO_REFS, mount=MOUNT, slots=(1,))


def test_flag_swap_condition_conversion(f):
    # flag_swap 走矩陣後的後處理：destroy(本體)→騎馬旗讀取（全部變體含原觸發）
    t = f.trig(tid=3953, name='1馬召', looping=True,
               conds=[f.cond_destroy(0), f.cond_area(sp=1, object_list=-1)],
               effects=[f.eff_task(sel=[12697], sp=1)])
    tm = f.tm([t])
    vm = {(3953, 1): 3953}
    v2 = tm.copy_trigger(3953, append_after_source=False, add_suffix=False)
    vm[(3953, 2)] = v2.trigger_id
    convert_flag_swap_conditions(tm, [dict(tid=3953, name='1馬召', category='flag_swap',
                                           extras='')],
                                 vm, hero_refs=HERO_REFS, mount=MOUNT, slots=(1, 2))
    for s in (1, 2):
        c = tm.triggers_by_id[vm[(3953, s)]].conditions[0]
        assert c.condition_type == 5 and c.object_list == 720
        assert (c.area_x1, c.area_y1) == (221, 239)              # 騎馬旗（職業列鍵定）

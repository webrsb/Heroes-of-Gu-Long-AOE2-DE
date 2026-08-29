# -*- coding: utf-8 -*-
"""T9b-ii: 上馬改造（X馬3 逐命拷貝＋備身連換）、怪改拆分、補池哨兵。"""
from steps.revive_mount import (rebuild_mount, split_effects, inventory_pools,
                                build_pool_grants)

LIFE = {1: [0, 900, 901]}
MOUNT = {1: dict(mount_ref=26109, mount_const=555, flag_cell=(221, 239),
                 rebirth_cell=(230, 239), final_cell=(232, 239),
                 pool_cells=[(204, 239), (203, 239)])}


def x3_variant(f, sp=1):
    # 模擬經矩陣改寫後的 X馬3 (C=1,S=sp) 變體：BRING(腳1→馬)、REMOVE腳、轉讓馬、啟動X死2(退役)
    return f.trig(name=f'1馬3◇位{sp}', enabled=False, conds=[
        f.cond_bring_obj(0, 26109), f.cond_timer(5)],
        effects=[f.eff_remove(sel=[0], sp=sp),
                 f.eff_ownership(sel=[26109], sp=8, tp=sp),
                 f.eff_activate(3827)])


def chains_stub():
    watch = {(1, sp, L): 7000 + sp * 10 + L for sp in (1, 2) for L in (1, 2)}
    final = {(1, sp): 7100 + sp for sp in (1, 2)}
    horse = {(1, sp, L): 7200 + sp * 10 + L for sp in (1, 2) for L in (1, 2, 3)}
    return watch, final, horse


def test_rebuild_mount_per_life_copies(f):
    v1 = x3_variant(f, sp=2)
    x2 = f.trig(name='1馬2◇位2', effects=[f.eff_activate(v1.trigger_id)])
    tm = f.tm([v1, x2])
    watch, final, horse = chains_stub()
    out = rebuild_mount(tm, x3_variants={(1, 2): v1.trigger_id}, life_refs=LIFE,
                        mount=MOUNT, watch=watch, final=final, horse=horse,
                        retired={3827}, lives=3)
    # 每命一份拷貝
    c2 = tm.triggers_by_id[out.copies[(1, 2, 2)]]
    assert c2.enabled == 0
    # 條件：BRING 改綁第2命 + 無騎馬旗（反相）
    brings = [kw for n, kw in c2.new_condition.calls if n == 'objects_in_area']
    assert brings and brings[0]['area_x1'] == 221 and brings[0].get('inverted') == 1
    assert c2.conditions[0].unit_object == 900
    # 效果：REMOVE 改第2命；REPLACE 剩餘備身(901)→馬騎const；建旗；停watch；啟馬監視
    assert c2.effects[0].selected_object_ids == [900]
    reps = [kw for n, kw in c2.new_effect.calls if n == 'replace_object']
    assert reps[0]['selected_object_ids'] == [901] and reps[0]['object_list_unit_id_2'] == 555
    creates = [kw for n, kw in c2.new_effect.calls if n == 'create_object']
    assert any(kw.get('location_x') == 221 for kw in creates)
    deacts = {kw['trigger_id'] for kw in [kw for n, kw in c2.new_effect.calls
                                          if n == 'deactivate_trigger']}
    assert watch[(1, 2, 2)] in deacts
    acts = {kw['trigger_id'] for kw in [kw for n, kw in c2.new_effect.calls
                                        if n == 'activate_trigger']}
    assert horse[(1, 2, 2)] in acts
    # 退役邊：拷貝的 e8→3827 已轉 None
    assert c2.effects[2].effect_type == 0
    # 終命拷貝：停 final 而非 watch
    c3 = tm.triggers_by_id[out.copies[(1, 2, 3)]]
    d3 = {kw['trigger_id'] for kw in [kw for n, kw in c3.new_effect.calls
                                      if n == 'deactivate_trigger']}
    assert final[(1, 2)] in d3
    # 原變體退役、入邊重指到扇出
    assert tm.triggers_by_id[v1.trigger_id].enabled == 0
    fan = tm.triggers_by_id[out.fanout[(1, 2)]]
    fan_acts = {kw['trigger_id'] for kw in [kw for n, kw in fan.new_effect.calls
                                            if n == 'activate_trigger']}
    assert fan_acts == {out.copies[(1, 2, L)] for L in (1, 2, 3)}
    assert x2.effects[0].trigger_id == out.fanout[(1, 2)]


def test_split_effects_guaikai(f):
    t = f.trig(tid=1946, name='怪改', looping=True, effects=[
        f.eff_task(sel=(), sp=7, x=10, y=10),
        f.eff_task(sel=(), sp=4, x=194, y=124),
        f.eff_task(sel=(), sp=6, x=195, y=37)])
    tm = f.tm([t])
    enable_lists = {(4, s): [] for s in (1, 2)} | {(6, s): [] for s in (1, 2)}
    splits = [dict(tid=1946, effect_index=1, class_id=4, expect_sp=4, expect_type=12,
                   reason='棍禁區'),
              dict(tid=1946, effect_index=2, class_id=6, expect_sp=6, expect_type=12,
                   reason='暗禁區')]
    ch = split_effects(tm, splits, enable_lists, slots=(1, 2))
    assert t.effects[1].effect_type == 0 and t.effects[2].effect_type == 0   # 本體抽除
    assert t.effects[0].effect_type == 12                                     # P7 效果不動
    assert len(enable_lists[(4, 2)]) == 1
    v = tm.triggers_by_id[enable_lists[(4, 2)][0]]
    assert v.enabled == 0 and v.looping == 1
    live = [e for e in v.effects if e.effect_type != 0]
    assert len(live) == 1
    assert live[0].source_player == 2 and live[0].location_x == 194


def test_split_guard_raises(f):
    import pytest
    from steps.base import BuildError
    t = f.trig(tid=1946, name='怪改', effects=[f.eff_task(sel=(), sp=7)])
    tm = f.tm([t])
    with pytest.raises(BuildError):
        split_effects(tm, [dict(tid=1946, effect_index=0, class_id=4, expect_sp=4,
                                expect_type=12, reason='')], {}, slots=(1,))


def test_inventory_pools_and_grants(f):
    q1 = f.trig(tid=100, name='任督圖', effects=[f.eff_damage(sel=[26109], quantity=-14000000)])
    q2 = f.trig(tid=200, name='惡夢', effects=[f.eff_damage(sel=[26109, 0], quantity=-20000000)])
    other = f.trig(tid=300, name='無關', effects=[f.eff_damage(sel=[0], quantity=-5)])
    tm = f.tm([q1, q2, other])
    pools = inventory_pools(tm, mount_ref2cid={26109: 1})
    assert [(p['tid'], p['cid'], p['qty']) for p in pools] == [
        (100, 1, -14000000), (200, 1, -20000000)]
    ch = build_pool_grants(tm, pools, life_refs=LIFE, mount=MOUNT)
    # 池任務觸發補了完成旗效果
    creates = [kw for n, kw in q1.new_effect.calls if n == 'create_object']
    assert creates and creates[0]['location_x'] == 204                       # pool_cells[0]
    # 哨兵：常駐、條件[騎馬旗∧任務旗]、灌全部備身
    sentinels = [t for t in tm.triggers if (t.name or '').startswith('補池')]
    assert len(sentinels) == 2
    s1 = sentinels[0]
    assert s1.enabled == 1 and s1.looping == 0
    areas = [kw for n, kw in s1.new_condition.calls if n == 'objects_in_area']
    assert {(a['area_x1'], a['area_y1']) for a in areas} == {(221, 239), (204, 239)}
    dmg = [kw for n, kw in s1.new_effect.calls if n == 'damage_object']
    assert dmg[0]['selected_object_ids'] == [900, 901] and dmg[0]['quantity'] == -14000000


def test_pool_cells_exhausted_raises(f):
    import pytest
    from steps.base import BuildError
    trigs = [f.trig(tid=100 + i, name=f'池{i}',
                    effects=[f.eff_damage(sel=[26109], quantity=-1)]) for i in range(3)]
    tm = f.tm(trigs)
    pools = inventory_pools(tm, mount_ref2cid={26109: 1})
    with pytest.raises(BuildError):
        build_pool_grants(tm, pools, life_refs=LIFE, mount=MOUNT)   # 只配了 2 格


def test_pool_grants_looping_regen_flag_gated(f):
    loop = f.trig(tid=400, name='九天', looping=True,
                  effects=[f.eff_damage(sel=[26109], quantity=-150)])
    tm = f.tm([loop])
    pools = inventory_pools(tm, mount_ref2cid={26109: 1})
    ch = build_pool_grants(tm, pools, life_refs=LIFE, mount=MOUNT)
    dup = [t for t in tm.triggers if '騎池' in (t.name or '')][0]
    live = [e for e in dup.effects if e.effect_type != 0]
    assert live[0].selected_object_ids == [900, 901] and live[0].quantity == -150
    areas = [kw for n, kw in dup.new_condition.calls if n == 'objects_in_area']
    assert areas[0]['area_x1'] == 221                       # 騎馬旗閘
    # looping 不佔旗格：原觸發無完成旗效果、無哨兵
    assert [kw for n, kw in loop.new_effect.calls if n == 'create_object'] == []
    assert [t for t in tm.triggers if (t.name or '').startswith('補池')] == []

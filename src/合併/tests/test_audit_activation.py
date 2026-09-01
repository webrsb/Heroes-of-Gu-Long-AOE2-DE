# -*- coding: utf-8 -*-
"""啟動稽核器：懸空邊/退役邊/死亡路徑越權/◇命旗防。"""
from analysis.audit_activation import audit


def test_dangling_and_retired_edges(f):
    dead = f.trig(name='退役_舊觸發')
    t = f.trig(name='某任務', effects=[f.eff_activate(9999), f.eff_activate(dead.trigger_id)])
    dead_src = f.trig(name='退役_另一支', effects=[f.eff_activate(dead.trigger_id)])
    vio, _ = audit(f.tm([dead, t, dead_src]))
    kinds = [k for k, _ in vio]
    assert '懸空邊' in kinds and '退役邊' in kinds
    assert not any('退役_另一支' in s for _, s in vio)   # 退役來源放行（不可達）


def test_death_path_only_whitelisted_targets(f):
    quest = f.trig(name='銀2◇命2', effects=[f.eff_task(sel=[1], sp=7, locref=900)])
    msg = f.trig(name='訊1位2命1步')
    w = f.trig(name='監視1位2命1',
               effects=[f.eff_activate(quest.trigger_id), f.eff_activate(msg.trigger_id)])
    vio, _ = audit(f.tm([quest, msg, w]))
    assert [k for k, _ in vio if k == '死亡路徑越權']          # 啟動◇命=違規
    assert all('訊1位2命1步' not in s for _, s in vio)          # 訊息白名單


def test_death_path_deactivate_also_checked(f):
    quest = f.trig(name='某任務')
    w = f.trig(name='重生1位2命1', effects=[f.eff_deactivate(quest.trigger_id)])
    vio, _ = audit(f.tm([quest, w]))
    assert [k for k, _ in vio if k == '死亡路徑停用越權']


def test_respawn_area_condition_flagged(f):
    hit = f.trig(name='1木◇命2', conds=[f.cond_bring_area(900, area=(70, 100, 80, 110))])
    miss = f.trig(name='1木◇命3', conds=[f.cond_bring_area(901, area=(0, 0, 10, 10))])
    vio, _ = audit(f.tm([hit, miss]), life_refs={1: [0, 900, 901]}, respawn=(77.5, 103.5))
    bad = [s for k, s in vio if k == '重生區條件']
    assert len(bad) == 1 and '◇命2' in bad[0]


def test_killvar_slot_consistency(f):
    ok = f.trig(name='5打民團◇位2', conds=[f._cond(78, source_player=2, variable=2, variable2=12)],
                effects=[f.eff_tribute(sp=2, tp=0, quantity=-2)])
    bad = f.trig(name='5打民團◇位3', conds=[f._cond(78, source_player=3, variable=5, variable2=15)],
                 effects=[f.eff_tribute(sp=3, tp=0, quantity=-2)])         # 變數欄漏改
    vio, _ = audit(f.tm([ok, bad]), var_offsets=(0, 10))
    hits = [s for k, s in vio if k == '變數槽位']
    assert len(hits) == 1 and '位3' in hits[0]


def test_life_copy_requires_flag_condition(f):
    bare = f.trig(name='神弓之洛5~1◇命2')
    gated = f.trig(name='神弓之洛5~1◇命3',
                   conds=[f.cond_area(sp=0, object_list=720, area=(231, 239, 231, 239))])
    by_ref = f.trig(name='任務◇命2', conds=[f.cond_destroy(900)])
    vio, _ = audit(f.tm([bare, gated, by_ref]), life_xs={232, 231, 230},
                   life_refs={1: [0, 900, 901]})
    bad = [s for k, s in vio if k == '◇命無旗防']
    assert len(bad) == 1 and '◇命2' in bad[0] and '神弓' in bad[0]


def test_life_copy_gated_by_variable_passes(f):
    """命旗→變數（2026-09-01）：命數條件 variable_value 也算閘，但別班的變數不算。"""
    gated = f.trig(name='神弓之洛5~1◇命2',
                   conds=[f._cond(22, variable=21, quantity=2, comparison=0)])
    wrong = f.trig(name='神弓之洛5~1◇命3',
                   conds=[f._cond(22, variable=2, quantity=2, comparison=0)])  # 擊殺變數
    vio, _ = audit(f.tm([gated, wrong]), life_vars={1: 21, 2: 22},
                   life_refs={1: [0, 900, 901]})
    bad = [s for k, s in vio if k == '◇命無旗防']
    assert len(bad) == 1 and '◇命3' in bad[0]

# -*- coding: utf-8 -*-
"""結構不變量稽核（2026-08-31）：把當天兩個「只有遊玩才發現」的失效變成靜態可查。"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from analysis import audit_structure as A


def test_key_contract_seat_needs_five_variants(f):
    base = f.trig(name='3船血東')
    variants = [f.trig(name=f'3船血東◇位{s}') for s in (1, 2, 4, 5, 6)]
    added = {'3船血東': {'name': '3船血東', 'key': 'seat'}}
    assert A.check_key_contracts([base] + variants, added) == []
    # 這正是 2026-08-31 的 fatal bug：被判 cross → 一個變體都沒生
    v = A.check_key_contracts([base], added)
    assert len(v) == 1 and '實得 0' in v[0] and 'cross' in v[0]


def test_key_contract_class_and_global_must_have_no_variants(f):
    a = f.trig(name='3船暈東')
    added = {'3船暈東': {'name': '3船暈東', 'key': 'class'}}
    assert A.check_key_contracts([a], added) == []
    assert A.check_key_contracts([a, f.trig(name='3船暈東◇位1')], added)


def test_key_contract_requires_declaration(f):
    a = f.trig(name='3船血東')
    v = A.check_key_contracts([a], {'3船血東': {'name': '3船血東'}})
    assert len(v) == 1 and '未宣告 key' in v[0]


def test_variant_edge_must_point_to_same_seat(f):
    """X船6◇位1 指向 3船血東【原支】（座位 3）＝ 2026-08-31 fatal bug 的第二個角度。"""
    blk = f.trig(name='3船血東')
    blk1 = f.trig(name='3船血東◇位1')
    holder = f.trig(name='3船6◇位1', effects=[f.eff_activate(blk.trigger_id)])
    added = {'3船血東': {'name': '3船血東', 'key': 'seat'}}
    v = A.check_variant_edges([blk, blk1, holder], added)
    assert len(v) == 1 and '位3' in v[0] and '位1' in v[0]
    holder.effects = [f.eff_activate(blk1.trigger_id)]
    assert A.check_variant_edges([blk, blk1, holder], added) == []


def test_variant_edge_ignores_global_holder(f):
    """無座位的全域觸發（如 船旗初始化）指向座位鍵觸發不算違規。"""
    blk = f.trig(name='3船血東')
    g = f.trig(name='船旗初始化', effects=[f.eff_activate(blk.trigger_id)])
    assert A.check_variant_edges([blk, g], {'3船血東': {'name': '3船血東', 'key': 'seat'}}) == []


def test_block_order_same_tick(f):
    """同 tick 啟動封鎖與扣費：封鎖 id 較大就攔不住（spike_objhp D 組實測）。"""
    fee = f.trig(name='費')                       # 先建＝小 id
    blk = f.trig(name='封', effects=[f.eff_deactivate(fee.trigger_id)])
    src = f.trig(name='源', effects=[f.eff_activate(fee.trigger_id), f.eff_activate(blk.trigger_id)])
    v = A.check_block_order([fee, blk, src])
    assert len(v) == 1 and '攔不住' in v[0]
    assert A.check_block_order([fee, blk, src], allow=[(blk.trigger_id, fee.trigger_id)]) == []


def test_block_order_ok_when_blocker_id_smaller(f):
    blk = f.trig(name='封')                       # 先建＝小 id
    fee = f.trig(name='費')
    blk.effects = [f.eff_deactivate(fee.trigger_id)]
    src = f.trig(name='源', effects=[f.eff_activate(blk.trigger_id), f.eff_activate(fee.trigger_id)])
    assert A.check_block_order([blk, fee, src]) == []


def test_teleport_loop_detects_destination_inside_source(f):
    """落點落在傳送來源區內 → 落地又被傳走（渡船外落點若含進入感應區就是這型）。"""
    t1 = f.trig(name='入', effects=[f.eff_teleport(sp=1, area=(79, 233, 79, 235), x=81, y=232)])
    t2 = f.trig(name='出', effects=[f.eff_teleport(sp=1, area=(81, 235, 81, 235), x=79, y=234)])
    v = A.check_teleport_loops([t1, t2])
    assert len(v) == 1 and '(79,234)' in v[0]
    t2.effects = [f.eff_teleport(sp=1, area=(81, 235, 81, 235), x=75, y=234)]
    assert A.check_teleport_loops([t1, t2]) == []


def test_teleport_loop_also_checks_task_destinations(f):
    t1 = f.trig(name='入', effects=[f.eff_teleport(sp=1, area=(110, 228, 110, 228), x=112, y=228)])
    t2 = f.trig(name='清', effects=[f.eff_task(sp=1, x=110, y=228)])
    assert len(A.check_teleport_loops([t1, t2])) == 1


def test_reports_seat_coverage_and_hp_range(f):
    entries = [{'kind': 'trigger_add', 'name': f'{s}船級西', 'key': 'seat'} for s in (2, 3, 4, 5, 6)]
    r = A.report_seat_coverage(entries)
    assert len(r) == 1 and '5/6' in r[0]
    t = f.trig(name='灌血', effects=[f.eff_hp(sel=[0], quantity=40192)])
    h = A.report_hp_range([t])
    assert len(h) == 1 and '40192' in h[0] and '-25344' in h[0]


def test_audit_all_wires_everything(f):
    trigs = [f.trig(name=f'{s}船暈東') for s in range(1, 7)]
    entries = [{'kind': 'trigger_add', 'name': f'{s}船暈東', 'key': 'class'} for s in range(1, 7)]
    v, r = A.audit_all(trigs, entries)
    assert v == [] and r == []          # 六座位齊全＝座位覆蓋報告也乾淨


def test_unnamed_triggers_do_not_crash(f):
    """基底有大量無名觸發：`'' in '123456'` 是 True，寫成字串包含判斷會 IndexError。"""
    blk = f.trig(name='3船血東')
    anon = f.trig(name='', effects=[f.eff_activate(blk.trigger_id)])
    added = {'3船血東': {'name': '3船血東', 'key': 'seat'}}
    assert A.check_variant_edges([blk, anon], added) == []
    assert A.report_seat_coverage([{'kind': 'trigger_add', 'name': ''}]) == []


def test_block_order_ignores_targets_with_real_conditions(f):
    """基底 3204 處都是「被停用的目標有真條件」——那種情況攔截者還有機會，不該報。"""
    fee = f.trig(name='費', conds=[f.cond_area(sp=1, area=(1, 1, 2, 2))])
    blk = f.trig(name='封', effects=[f.eff_deactivate(fee.trigger_id)])
    src = f.trig(name='源', effects=[f.eff_activate(fee.trigger_id), f.eff_activate(blk.trigger_id)])
    assert A.check_block_order([fee, blk, src]) == []


def test_block_order_flags_timer0_target(f):
    fee = f.trig(name='費', conds=[f.cond_timer(0)])
    blk = f.trig(name='封', effects=[f.eff_deactivate(fee.trigger_id)])
    src = f.trig(name='源', effects=[f.eff_activate(fee.trigger_id), f.eff_activate(blk.trigger_id)])
    assert len(A.check_block_order([fee, blk, src])) == 1


def test_block_order_ignores_timer_delayed_closer(f):
    """X船窗止 timer 180 停用零條件的 X船入：刻意延後關窗，不是同 tick 攔截 → 不該報。"""
    ent = f.trig(name='入')
    stop = f.trig(name='窗止', conds=[f.cond_timer(180)], effects=[f.eff_deactivate(ent.trigger_id)])
    src = f.trig(name='買票', effects=[f.eff_activate(ent.trigger_id), f.eff_activate(stop.trigger_id)])
    assert A.check_block_order([ent, stop, src]) == []


def test_block_order_gate_scoped_to_own_triggers(f):
    """基底既有形狀（原作風格）降級成報告，閘門只守本次施工新增的東西。"""
    fee = f.trig(name='基底費')
    blk = f.trig(name='基底封', effects=[f.eff_deactivate(fee.trigger_id)])
    src = f.trig(name='基底源', effects=[f.eff_activate(fee.trigger_id), f.eff_activate(blk.trigger_id)])
    trigs = [fee, blk, src]
    own = A.own_trigger_ids(trigs, {'我的觸發': {}})
    assert A.check_block_order(trigs, own_tids=own) == []
    assert len(A.report_block_order(trigs, own_tids=own)) == 1
    own2 = A.own_trigger_ids(trigs, {'基底封': {}})
    assert len(A.check_block_order(trigs, own_tids=own2)) == 1


def test_own_trigger_ids_covers_s39_copies(f):
    a = f.trig(name='3船費東')
    b = f.trig(name='3船費東◇位1')
    c = f.trig(name='別人')
    ids = A.own_trigger_ids([a, b, c], {'3船費東': {}})
    assert ids == {a.trigger_id, b.trigger_id}

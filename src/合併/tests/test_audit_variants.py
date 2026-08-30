# -*- coding: utf-8 -*-
"""變體鏈路完整性：邊指原版(A)、邊指他座位變體(B)、玩家欄未改(C)、外部邊指入原版(D)、乾淨鏈 0 違規。"""
from analysis.audit_variants import audit, load_var_map


def chain(f, remap_edge=True, fix_sp=True, seat=1):
    base_a = f.trig(tid=10, name='5教頭', conds=[f.cond_area(sp=5, qty=1)], effects=[f.eff_chat(sp=5), f.eff_activate(11)])
    base_b = f.trig(tid=11, name='5教頭2', conds=[f.cond_timer(14)], effects=[f.eff_chat(sp=5)])
    va = f.trig(tid=100, name='5教頭◇位1', conds=[f.cond_area(sp=seat if fix_sp else 5, qty=1)],
                effects=[f.eff_chat(sp=seat if fix_sp else 5), f.eff_activate(101 if remap_edge else 11)])
    vb = f.trig(tid=101, name='5教頭2◇位1', conds=[f.cond_timer(14)], effects=[f.eff_chat(sp=seat)])
    return [base_a, base_b, va, vb], {(10, 1): 100, (11, 1): 101}


def test_clean_chain_has_no_findings(f):
    trigs, vm = chain(f)
    assert audit(trigs, vm) == []


def test_edge_to_original_flagged_A(f):
    trigs, vm = chain(f, remap_edge=False)
    kinds = [x.kind for x in audit(trigs, vm)]
    assert kinds == ['A1 同職業邊指原版']


def test_player_field_not_reseated_flagged_C(f):
    trigs, vm = chain(f, fix_sp=False)
    kinds = sorted(set(x.kind for x in audit(trigs, vm)))
    assert kinds == ['C 玩家欄未改座位']


def test_edge_to_other_seat_variant_flagged_B(f):
    trigs, vm = chain(f)
    vb2 = f.trig(tid=201, name='5教頭2◇位2', conds=[f.cond_timer(14)], effects=[f.eff_chat(sp=2)])
    trigs[2].effects[1].trigger_id = 201
    vm[(11, 2)] = 201
    assert [x.kind for x in audit(trigs + [vb2], vm)] == ['B 邊指他座位變體']


def test_external_edge_into_original_flagged_D(f):
    trigs, vm = chain(f)
    relay = f.trig(tid=50, name='中繼', conds=[f.cond_timer(3)], effects=[f.eff_activate(11)])
    assert [x.kind for x in audit(trigs + [relay], vm)] == ['D1 外部邊指入已停用原版']


def test_load_var_map_parses_s39_rows(tmp_path):
    p = tmp_path / '39.tsv'
    p.write_text('s39\ttrigger_add\tT543→位1\ttrigger\t\tT22329\t矩陣變體\n'
                 's39\ttrigger_add\t1召→位1\ttrigger\t\tT9\t連動a變體\n', encoding='utf-8')
    assert load_var_map(str(p)) == {(543, 1): 22329}

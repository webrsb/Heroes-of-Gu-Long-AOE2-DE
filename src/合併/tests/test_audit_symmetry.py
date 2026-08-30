# -*- coding: utf-8 -*-
"""六座位對稱稽核：極性抄反（教頭4 型）、錯家（sp 指別座位）、漏改英雄 ref、順序對調不誤報。"""
from analysis.audit_symmetry import seat_pattern, audit

HERO = {0: 1, 1: 2, 2: 3, 502: 4, 7: 5, 45117: 6}


def test_seat_pattern():
    assert seat_pattern('3教頭4') == (3, 'X教頭4')
    assert seat_pattern('2劍3') == (2, 'XC3')
    assert seat_pattern('6箭3') == (6, 'XC3') and seat_pattern('6暗') == (6, 'XC')
    assert seat_pattern('槍1') == (3, 'C1')
    assert seat_pattern('首  劍1') == (2, '~首  C1')
    assert seat_pattern('科技') == (None, None) and seat_pattern('') == (None, None)


def six(f, make):
    """make(seat, f) → trigger；回傳 6 支（tid 依序）。"""
    return [make(s, f) for s in range(1, 7)]


def test_edge_polarity_minority_flagged_regardless_of_structure(f):
    # 教頭4：4P/5P 多一個 ACT 效果（結構不同），2P/3P 對「X教頭5」抄成 DEACT
    targets = {s: f.trig(tid=100 + s, name=f'{s}教頭5') for s in range(1, 7)}

    def make(s, f):
        effs = [f.eff_chat(sp=s, message='學會')]
        if s in (4, 5):
            effs.append(f.eff_activate(900 + s))
        effs.append(f.eff_deactivate(100 + s) if s in (2, 3) else f.eff_activate(100 + s))
        return f.trig(tid=s, name=f'{s}教頭4', effects=effs)
    trigs = six(f, make) + list(targets.values())
    findings, _ = audit(trigs, HERO)
    hi = [(r.seat, r.field, r.where) for r in findings if r.sev == 'HIGH']
    assert (2, 'edge_pol', '→X教頭5') in hi and (3, 'edge_pol', '→X教頭5') in hi
    assert all(r.seat in (2, 3) for r in findings if r.sev == 'HIGH')


def test_foreign_player_flagged(f):
    def make(s, f):
        return f.trig(tid=s, name=f'{s}孽', effects=[f.eff_tribute(sp=1 if s == 2 else s, tp=0, quantity=-60)])
    findings, _ = audit(six(f, make), HERO)
    hi = [(r.seat, r.field) for r in findings if r.sev == 'HIGH']
    assert (2, 'foreign') in hi and (2, 'sp') in hi
    assert {r.seat for r in findings if r.sev == 'HIGH'} == {2}


def test_unfixed_hero_ref_flagged(f):
    heroes = {1: 0, 2: 1, 3: 2, 4: 502, 5: 7, 6: 45117}

    def make(s, f):
        ref = 8 if s == 6 else heroes[s]          # 6P 漏改成別的 ref
        return f.trig(tid=s, name=f'{s}召', conds=[f.cond_destroy(ref)], effects=[f.eff_chat(sp=s)])
    findings, _ = audit(six(f, make), HERO)
    assert [(r.seat, r.field, r.value) for r in findings if r.sev == 'HIGH'] == [(6, 'uo', 'REF')]


def test_reordered_effects_not_flagged(f):
    heroes = {1: 0, 2: 1, 3: 2, 4: 502, 5: 7, 6: 45117}

    def make(s, f):
        a = f.eff_hp(sel=[heroes[s]], sp=s, quantity=50)
        b = f.eff_hp(sel=[9000 + s], sp=s, quantity=50)
        return f.trig(tid=s, name=f'{s}失血', effects=[b, a] if s == 5 else [a, b])
    findings, _ = audit(six(f, make), HERO)
    assert [r for r in findings if r.sev == 'HIGH'] == []


def test_symmetric_group_clean_and_non_seat_groups_ignored(f):
    def make(s, f):
        return f.trig(tid=s, name=f'{s}技2', conds=[f.cond_area(sp=s, qty=2)], effects=[f.eff_deactivate(50 + s)])
    trigs = six(f, make) + [f.trig(tid=50 + s, name=f'{s}教頭5') for s in range(1, 7)]
    trigs += [f.trig(tid=200 + z, name=f'{z}石2', effects=[f.eff_chat(sp=-1)]) for z in range(1, 7)]  # 石區編號非座位
    findings, stats = audit(trigs, HERO)
    assert findings == [] and stats['groups'] >= 1

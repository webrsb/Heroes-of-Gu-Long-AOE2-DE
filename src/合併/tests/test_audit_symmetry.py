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


def test_foreign_edge_flagged(f):
    # 5道4 型：啟停指到別座位的首觸發
    firsts = {s: f.trig(tid=500 + s, name=f'首  {"刀劍槍棍拳箭"[s-1]}3') for s in range(1, 7)}

    def make(s, f):
        target = 506 if s == 5 else 500 + s          # 5P 指到 6P 的首 箭3
        return f.trig(tid=s, name=f'{s}道4', effects=[f.eff_chat(sp=s), f.eff_deactivate(target)])
    findings, _ = audit(six(f, make) + list(firsts.values()), HERO)
    hi = [(r.seat, r.field) for r in findings if r.sev == 'HIGH']
    assert (5, 'foreign') in hi and {r.seat for r in findings if r.sev == 'HIGH'} == {5}


def test_single_type_mismatch_reported_as_high_with_position(f):
    heroes = {1: 0, 2: 1, 3: 2, 4: 502, 5: 7, 6: 45117}

    def make(s, f):
        second = f.eff_hp(sel=[heroes[s]], sp=s, quantity=10) if s == 3 else f.eff_attack(sel=[heroes[s]], sp=s)
        return f.trig(tid=s, name=f'{s}道4', effects=[f.eff_chat(sp=s), second])
    findings, _ = audit(six(f, make), HERO)
    hi = [(r.seat, r.where, r.field, r.value, r.majority) for r in findings if r.sev == 'HIGH']
    assert hi == [(3, 'E#1', 'type', 27, 28)]


def test_enabled_minority_flagged(f):
    def make(s, f):
        return f.trig(tid=s, name=f'{s}南僧', enabled=(s == 4), conds=[f.cond_area(sp=s, qty=1)],
                      effects=[f.eff_activate(100 + s)])
    trigs = six(f, make) + [f.trig(tid=100 + s, name=f'當僧{s}') for s in range(1, 7)]
    findings, _ = audit(trigs, HERO)
    assert [(r.seat, r.field) for r in findings if r.sev == 'HIGH'] == [(4, 'enabled/looping')]


def test_seat1_unnumbered_target_matches_numbered_pattern(f):
    # 原作慣例：座位 1 的「女」對應 2–6 的「女2」…「女6」；1P 指向「女」不得誤報 edge_missing
    targets = {s: f.trig(tid=200 + s, name='女' if s == 1 else f'女{s}') for s in range(1, 7)}

    def make(s, f):
        return f.trig(tid=s, name=f'{s}當僧', effects=[f.eff_chat(sp=s, message='x'), f.eff_activate(200 + s)])
    findings, _ = audit(six(f, make) + list(targets.values()), HERO)
    assert not [r for r in findings if r.field == 'edge_missing']

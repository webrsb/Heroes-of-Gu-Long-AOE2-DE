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


def test_absent_seats_flags_single_seat_shape_in_uneven_family(f):
    """原型：西碼頭等級門檻只有座位 1 有（X船 座位1 4 支、其他 3 支）。"""
    from analysis.audit_symmetry import absent_seats, seat_pattern
    import collections
    trigs = []
    for s in range(1, 7):
        trigs.append(f.trig(name=f'{s}船', conds=[f.cond_area(sp=s)], effects=[f.eff_chat(sp=s)]))
    gate = f.trig(name='1船', conds=[f.cond_area(sp=1), f.cond_accumulate(sp=1, qty=1159)],
                  effects=[f.eff_chat(sp=1), f.eff_task(sp=1)])
    trigs.append(gate)
    groups = collections.defaultdict(lambda: collections.defaultdict(list))
    for t in trigs:
        s, pat = seat_pattern(t.name)
        groups[pat][s].append(t)
    out = absent_seats(groups)
    assert len(out) == 1 and out[0].tid == gate.trigger_id and out[0].field == 'absent'
    assert out[0].sev == 'HIGH' and '僅座位 [1]' in out[0].value


def test_absent_seats_ignores_class_exclusive_and_even_families(f):
    from analysis.audit_symmetry import absent_seats, seat_pattern
    import collections

    def group(trigs):
        g = collections.defaultdict(lambda: collections.defaultdict(list))
        for t in trigs:
            s, pat = seat_pattern(t.name)
            g[pat][s].append(t)
        return g
    # 職業專屬（樣式只跨 1 座位）
    solo = [f.trig(name='1狂', effects=[f.eff_chat(sp=1)]),
            f.trig(name='1狂2', effects=[f.eff_chat(sp=1)])]
    assert absent_seats(group(solo)) == []
    # 各座位支數相同＝只是形狀差異，交給 C 類 struct
    even = []
    for s in range(1, 7):
        even.append(f.trig(name=f'{s}教頭4', conds=[f.cond_area(sp=s)],
                           effects=[f.eff_chat(sp=s)] * (s % 2 + 1)))
    assert absent_seats(group(even)) == []


def test_shape_of_ignores_area_coords(f):
    from analysis.audit_symmetry import shape_of
    a = f.trig(name='1草', conds=[f.cond_area(sp=1, area=(108, 221, 117, 231))], effects=[f.eff_chat(sp=1)])
    b = f.trig(name='2草', conds=[f.cond_area(sp=2, area=(107, 222, 117, 231))], effects=[f.eff_chat(sp=2)])
    assert shape_of(a) == shape_of(b)      # 原作各座位區域手抖差幾格，不該拆散家族


def test_finding_key_is_stable_and_unique(f):
    from analysis.audit_symmetry import Finding, finding_key
    a = Finding('HIGH', 'X船', 0, 1, 3685, '1船', '整支', 'absent', 'v', 'm')
    b = Finding('MED', 'X船', 0, 1, 3685, '1船', '整支', 'absent', '別的值', '別的多數')
    c = Finding('HIGH', 'X船', 0, 2, 3707, '2船', 'E#0', 'sp', 'v', 'm')
    assert finding_key(a) == finding_key(b)      # 值變動不改鍵（同一條 finding）
    assert finding_key(a) != finding_key(c)


def test_parse_argv_separates_flags_from_positionals():
    """--record 曾被吃成 spec 路徑 → 那輪 renames 全沒套用、帳本用舊名建檔（2026-08-31）。"""
    from analysis.audit_symmetry import parse_argv
    p, out, spec, flags = parse_argv(['prog', 'base.aoe2scenario', 'r.md', '--record'])
    assert (p, out, spec) == ('base.aoe2scenario', 'r.md', 'merge_spec.yaml')
    assert flags == {'--record'}
    p, out, spec, flags = parse_argv(['prog', 'b', 'r.md', 'other_spec.yaml'])
    assert spec == 'other_spec.yaml' and flags == set()

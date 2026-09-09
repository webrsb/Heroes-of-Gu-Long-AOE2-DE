# -*- coding: utf-8 -*-
"""s91 特徵斷言：職業綁定物件的 P8 託管——獨立重驗最終檔狀態。
守的是「本體改了、鏡像改了、九環旗忘了」這種漏一種／漏一座位的無聲錯誤。"""
from types import SimpleNamespace as NS

HERO = {c: c for c in range(1, 7)}                 # ref 1..6
MIRROR = {c: 14160 + c for c in range(1, 7)}
FLAG = {c: 14500 + c for c in range(1, 7)}
PARAMS = {'hero_refs': HERO, 'mirrors': MIRROR, 'class_flags': FLAG}
ALL = (HERO, MIRROR, FLAG)


def um_with(owners):
    """owners: {ref: player}。"""
    units = {p: [] for p in range(9)}
    for ref, p in owners.items():
        units[p].append(NS(reference_id=ref, unit_const=1, x=0.0, y=0.0, player=p))
    return NS(units=units)


def default_owners():
    return {ref: 8 for tbl in ALL for ref in tbl.values()}


def sel_trigs(f, skip=(), tables=ALL):
    out = []
    for cid in range(1, 7):
        for s in range(1, 7):
            effs = [f.eff_ownership([tbl[cid]], sp=8, tp=s) for tbl in tables
                    if (tbl[cid], cid, s) not in skip]
            out.append(f.trig(name=f'選角{cid}位{s}', effects=effs))
    return out


def run(f, owners=None, trigs=None):
    from analysis.class_bound_check import check_class_bound
    return check_class_bound(um_with(owners or default_owners()),
                             f.tm(trigs if trigs is not None else sel_trigs(f)), PARAMS)


def bad(results):
    return [msg for ok, msg in results if not ok]


def test_clean_passes(f):
    res = run(f)
    assert bad(res) == []
    assert len(res) == 3 * 6 + 3 * 6 * 6            # P 18 項 ＋ T 108 項


def test_flag_left_on_class_player_is_violation(f):
    """歷史漏洞重現：九環旗種子沒歸 P8，還留在 P{cid}。"""
    owners = default_owners()
    owners[FLAG[3]] = 3
    msgs = bad(run(f, owners=owners))
    assert len(msgs) == 1
    assert 'P[九環旗] 職業3' in msgs[0] and '開場屬 P3' in msgs[0]


def test_missing_transfer_on_one_seat(f):
    """六座位漏一個——最常見的漏，必須抓到。"""
    trigs = sel_trigs(f, skip=[(FLAG[2], 2, 5)])
    msgs = bad(run(f, trigs=trigs))
    assert len(msgs) == 1
    assert '選角2位5 沒轉讓職業2 ref' in msgs[0]


def test_wrong_direction(f):
    trigs = [t for t in sel_trigs(f) if t.name != '選角1位1']
    trigs.append(f.trig(name='選角1位1',
                        effects=[f.eff_ownership([HERO[1]], sp=8, tp=1),
                                 f.eff_ownership([MIRROR[1]], sp=8, tp=1),
                                 f.eff_ownership([FLAG[1]], sp=0, tp=1)]))
    msgs = bad(run(f, trigs=trigs))
    assert len(msgs) == 1 and '方向錯' in msgs[0] and 'P0→P1' in msgs[0]


def test_cross_class_transfer(f):
    """裁決表抄錯列：選角1位1 轉讓了職業2 的旗。"""
    trigs = [t for t in sel_trigs(f) if t.name != '選角1位1']
    trigs.append(f.trig(name='選角1位1',
                        effects=[f.eff_ownership([HERO[1]], sp=8, tp=1),
                                 f.eff_ownership([MIRROR[1]], sp=8, tp=1),
                                 f.eff_ownership([FLAG[1]], sp=8, tp=1),
                                 f.eff_ownership([FLAG[2]], sp=8, tp=1)]))
    msgs = bad(run(f, trigs=trigs))
    assert any('抄錯列' in m for m in msgs)


def test_table_without_class_flags_still_checks_rest(f):
    """本檔若沒宣告 class_flags，其餘兩表照驗、不因此靜默。"""
    from analysis.class_bound_check import check_class_bound
    owners = {ref: 8 for tbl in (HERO, MIRROR) for ref in tbl.values()}
    owners[MIRROR[4]] = 4
    tm = f.tm(sel_trigs(f, tables=(HERO, MIRROR)))
    msgs = bad(check_class_bound(um_with(owners), tm,
                                 {'hero_refs': HERO, 'mirrors': MIRROR}))
    assert len(msgs) == 1 and 'P[鏡像] 職業4' in msgs[0]


def test_asymmetric_start_units_report(f):
    """六座位同 const 同格＝座位資源（不報）；只有一位有的＝要人看一眼（報）。"""
    from analysis.class_bound_check import report_asymmetric_start_units
    units = {p: [] for p in range(9)}
    for p in range(1, 7):
        units[p].append(NS(reference_id=1000 + p, unit_const=837, x=85.5, y=100.5, player=p))
        units[p].append(NS(reference_id=1100 + p, unit_const=1291, x=0.5, y=120.5, player=p))
    units[1].append(NS(reference_id=32561, unit_const=72, x=20.5, y=239.5, player=1))
    units[8].append(NS(reference_id=14523, unit_const=720, x=234.5, y=239.5, player=8))
    rows = report_asymmetric_start_units(NS(units=units))
    assert len(rows) == 1
    assert rows[0].startswith('B P1 ref32561 const72')


def test_asymmetric_report_catches_undeclared_class_object(f):
    """漏宣告的職業綁定物件（六位各一顆、格子各異）會整組被報出來。"""
    from analysis.class_bound_check import report_asymmetric_start_units
    units = {p: [] for p in range(9)}
    for p in range(1, 7):
        units[p].append(NS(reference_id=14500 + p, unit_const=720,
                           x=234.5, y=240.0 - p, player=p))
    rows = report_asymmetric_start_units(NS(units=units))
    assert len(rows) == 6 and all('const720' in r for r in rows)


def test_asymmetric_report_distinguishes_drift_from_class_row(f):
    """六位都有同 const 但只差一格＝擺位參差；六位各一顆各在各的格＝職業列（要優先查）。"""
    from analysis.class_bound_check import report_asymmetric_start_units
    units = {p: [] for p in range(9)}
    for p in range(1, 7):
        y = 97.5 if p == 1 else 98.5                       # P1 差一格（原作 837 就這樣）
        units[p].append(NS(reference_id=13260 + p, unit_const=837, x=154.5, y=y, player=p))
        units[p].append(NS(reference_id=13270 + p, unit_const=837, x=85.5, y=100.5, player=p))
    rows = report_asymmetric_start_units(NS(units=units))
    assert len(rows) == 6 and all('沒對齊' in r for r in rows)

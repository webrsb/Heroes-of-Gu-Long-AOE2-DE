# -*- coding: utf-8 -*-
"""balance_check：建置後實值對帳＋等級單調（s91 特徵斷言，比照 ferry_check 回傳 (ok,msg) 列表）。"""
from analysis.balance_check import check_mob_balance

P7 = 7


def _create(f, const, x, y):
    return f._eff(11, source_player=P7, object_list_unit_id=const,
                  location_x=x, location_y=y)


def _hp(f, x, y, qty):
    return f._eff(27, source_player=P7, quantity=qty, operation=-1,
                  area_x1=x, area_y1=y, area_x2=x, area_y2=y)


def _atk(f, x, y, amount, cls=0):
    e = f._eff(28, source_player=P7, quantity=amount, operation=2,
               area_x1=x, area_y1=y, area_x2=x, area_y2=y)
    e.armour_attack_class, e.armour_attack_quantity = cls, amount
    return e


ROWS = [
    dict(tid=0, name='民團', const=74, lv=1, kind='m', itv=2.0,
         base_hp=60, base_atk=17, hp=70, atk=17),
    dict(tid=1, name='山賊', const=448, lv=4, kind='f', itv=1.9,
         base_hp=95, base_atk=11, hp=95, atk=14),
]


def _tm(f, hp0=10, atk0=0, hp1=0, atk1=3):
    t0 = f.trig(name='民團', tid=0, effects=[_create(f, 74, 1, 1), _hp(f, 1, 1, hp0), _atk(f, 1, 1, atk0)])
    t1 = f.trig(name='山賊', tid=1, effects=[_create(f, 448, 2, 2), _hp(f, 2, 2, hp1), _atk(f, 2, 2, atk1)])
    return f.tm([t0, t1])


def test_all_ok(f):
    results = check_mob_balance(_tm(f), ROWS)
    assert results and all(ok for ok, _ in results)


def test_tampered_hp_flagged(f):
    results = check_mob_balance(_tm(f, hp0=99), ROWS)
    assert any(not ok and '民團' in msg and '血' in msg for ok, msg in results)


def test_nonzero_attack_class_flagged(f):
    tm = _tm(f)
    tm.triggers[0].effects[2].armour_attack_class = 3
    results = check_mob_balance(tm, ROWS)
    assert any(not ok and 'class' in msg for ok, msg in results)


def test_monotonic_violation_flagged(f):
    rows = [dict(ROWS[0]), dict(ROWS[1])]
    rows[1]['atk'] = 5                       # Lv4 基準DPS 遠低於 Lv1 → 單調破壞
    t0 = f.trig(name='民團', tid=0, effects=[_create(f, 74, 1, 1), _hp(f, 1, 1, 10), _atk(f, 1, 1, 0)])
    t1 = f.trig(name='山賊', tid=1, effects=[_create(f, 448, 2, 2), _hp(f, 2, 2, 0), _atk(f, 2, 2, 0)])
    with_rows = f.tm([t0, t1])
    rows[1]['base_atk'] = 5                  # 差值 0，實值對帳過，單調檢查抓
    results = check_mob_balance(with_rows, rows)
    assert any(not ok and '單調' in msg for ok, msg in results)

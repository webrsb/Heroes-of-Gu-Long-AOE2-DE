# -*- coding: utf-8 -*-
"""balance_check：建置後實值對帳＋等級單調（s91 特徵斷言，比照 ferry_check 回傳 (ok,msg) 列表）。"""
from types import SimpleNamespace
from analysis.balance_check import check_mob_balance

P7 = 7


def _create(f, const, x, y):
    return f._eff(11, source_player=P7, object_list_unit_id=const,
                  location_x=x, location_y=y)


def _hp(f, x, y, qty, const=-1):
    return f._eff(27, source_player=P7, object_list_unit_id=const, quantity=qty,
                  operation=-1, area_x1=x, area_y1=y, area_x2=x, area_y2=y)


def _atk(f, x, y, amount, cls=0, const=-1):
    e = f._eff(28, source_player=P7, object_list_unit_id=const, quantity=amount,
               operation=2, area_x1=x, area_y1=y, area_x2=x, area_y2=y)
    e.armour_attack_class, e.armour_attack_quantity = cls, amount
    return e


def _rect_atk(f, x1, y1, x2, y2, amount, const, cls=0):
    e = f._eff(28, source_player=P7, object_list_unit_id=const, quantity=amount,
               operation=2, area_x1=x1, area_y1=y1, area_x2=x2, area_y2=y2)
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
    rows[1]['base_atk'] = 5                  # 差值 0，實值對帳過，單調檢查抓
    results = check_mob_balance(_tm(f, atk1=0), rows)
    assert any(not ok and '單調' in msg for ok, msg in results)


def test_monotonic_hp_regression_flagged(f):
    # DPS 遞增但血倒退：對帳全過（delta 全 0），只有單調檢查該抓
    rows = [
        dict(tid=0, name='A', const=1, lv=1, kind='m', itv=1.0, base_hp=100, base_atk=10, hp=100, atk=10),
        dict(tid=1, name='B', const=2, lv=2, kind='m', itv=1.0, base_hp=50, base_atk=20, hp=50, atk=20),
    ]
    t0 = f.trig(name='A', tid=0, effects=[_create(f, 1, 1, 1), _hp(f, 1, 1, 0), _atk(f, 1, 1, 0)])
    t1 = f.trig(name='B', tid=1, effects=[_create(f, 2, 2, 2), _hp(f, 2, 2, 0), _atk(f, 2, 2, 0)])
    results = check_mob_balance(f.tm([t0, t1]), rows)
    assert all(ok for ok, msg in results if '單調' not in msg)
    assert any(not ok and '單調' in msg for ok, msg in results)


def test_hp_none_row_skips_hp_check_but_checks_attack(f):
    rows = [dict(ROWS[0]), dict(ROWS[1])]
    rows[0]['hp'] = None                     # 表二列：血不驗，攻照驗
    t0 = f.trig(name='民團', tid=0, effects=[_create(f, 74, 1, 1), _hp(f, 1, 1, 999), _atk(f, 1, 1, 0)])
    t1 = f.trig(name='山賊', tid=1, effects=[_create(f, 448, 2, 2), _hp(f, 2, 2, 0), _atk(f, 2, 2, 3)])
    results = check_mob_balance(f.tm([t0, t1]), rows)
    assert not any('格(1,1)' in msg and '血' in msg for ok, msg in results)
    assert any('格(1,1)' in msg and '攻' in msg for ok, msg in results)
    assert all(ok for ok, _ in results)


def test_two_creates_same_const_each_tile_reconciled(f):
    t0 = f.trig(name='民團', tid=0, effects=[
        _create(f, 74, 1, 1), _hp(f, 1, 1, 10), _atk(f, 1, 1, 0),
        _create(f, 74, 3, 3), _hp(f, 3, 3, 10), _atk(f, 3, 3, 0)])
    t1 = f.trig(name='山賊', tid=1, effects=[_create(f, 448, 2, 2), _hp(f, 2, 2, 0), _atk(f, 2, 2, 3)])
    results = check_mob_balance(f.tm([t0, t1]), ROWS)
    assert all(ok for ok, _ in results)
    assert any('格(1,1)' in msg for _, msg in results) and any('格(3,3)' in msg for _, msg in results)


def test_same_const_explicit_tag_not_cross_summed_across_tiles(f):
    # 2026-09-02 品質審查回歸測：T4785 型真實資料——多生成格共用同一 const，且每格 tile 效果
    # 各自 olu=該 const（非 -1）。曾誤加「olu==const 即算」旁支，導致同 const 的其他格數值被
    # 錯誤疊加進本格對帳（12+5+5=22≠17），已改回純幾何涵蓋（只認自己格）。
    t0 = f.trig(name='民團', tid=0, effects=[
        _create(f, 74, 1, 1), _hp(f, 1, 1, 10, const=74), _atk(f, 1, 1, 5, const=74),
        _create(f, 74, 3, 3), _hp(f, 3, 3, 10, const=74), _atk(f, 3, 3, 5, const=74)])
    t1 = f.trig(name='山賊', tid=1, effects=[_create(f, 448, 2, 2), _hp(f, 2, 2, 0), _atk(f, 2, 2, 3)])
    rows = [dict(tid=0, name='民團', const=74, lv=1, kind='m', itv=2.0,
                 base_hp=60, base_atk=12, hp=70, atk=17), ROWS[1]]
    results = check_mob_balance(f.tm([t0, t1]), rows)
    assert all(ok for ok, _ in results)


def test_noise_const_not_accumulated(f):
    t0 = f.trig(name='民團', tid=0, effects=[
        _create(f, 74, 1, 1), _hp(f, 1, 1, 10), _hp(f, 1, 1, 999, const=999),
        _atk(f, 1, 1, 0), _atk(f, 1, 1, 888, const=999)])
    t1 = f.trig(name='山賊', tid=1, effects=[_create(f, 448, 2, 2), _hp(f, 2, 2, 0), _atk(f, 2, 2, 3)])
    results = check_mob_balance(f.tm([t0, t1]), ROWS)
    assert all(ok for ok, _ in results)      # 雜訊未被累加，對帳仍過


def test_real_parser_path_without_triggers_by_id(f):
    t0 = f.trig(name='民團', tid=0, effects=[_create(f, 74, 1, 1), _hp(f, 1, 1, 10), _atk(f, 1, 1, 0)])
    t1 = f.trig(name='山賊', tid=1, effects=[_create(f, 448, 2, 2), _hp(f, 2, 2, 0), _atk(f, 2, 2, 3)])
    tm = SimpleNamespace(triggers=[t0, t1])           # 無 triggers_by_id：模擬正式 parser
    results = check_mob_balance(tm, ROWS)
    assert results and all(ok for ok, _ in results)


def test_rect_atk_counted_in_reconciliation(f):
    # T2711 母夜叉案例：矩形涵蓋生成格、olu=表列 const，未歸零前應被抓 not ok；歸零後對帳過
    row = dict(tid=0, name='母夜叉', const=430, lv=52, kind='m', itv=2.0,
               base_hp=100, base_atk=12, hp=571, atk=190)
    t = f.trig(name='母夜叉', tid=0, effects=[
        _create(f, 430, 180, 149), _hp(f, 180, 149, 471), _atk(f, 180, 149, 178),
        _rect_atk(f, 180, 149, 207, 168, 3164, const=430)])
    results = check_mob_balance(f.tm([t]), [row])
    assert any(not ok and '攻' in msg for ok, msg in results)          # 12+178+3164≠190

    t.effects[3].armour_attack_quantity = 0                            # 寫入端修完後的狀態
    results = check_mob_balance(f.tm([t]), [row])
    assert all(ok for ok, msg in results)                              # 12+178+0＝190


def test_real_parser_path_out_of_range_tid_reports_not_ok(f):
    t0 = f.trig(name='民團', tid=0, effects=[_create(f, 74, 1, 1), _hp(f, 1, 1, 10), _atk(f, 1, 1, 0)])
    tm = SimpleNamespace(triggers=[t0])                # 只有 1 支，rows 卻要 T5
    rows = [dict(ROWS[0], tid=5)]
    results = check_mob_balance(tm, rows)              # 不得炸 IndexError
    assert any(not ok and 'T5' in msg and '不存在' in msg for ok, msg in results)

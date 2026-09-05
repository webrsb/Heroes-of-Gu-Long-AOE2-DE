# -*- coding: utf-8 -*-
"""s374 野怪平衡：格 27 改 hp 差值、格 28 改 atk 差值、全域 28 歸零折入。"""
import pytest
from steps.base import BuildError
from steps.s374_mobbalance import apply_mob_balance

P7 = 7


def _create(f, const, x, y):
    return f._eff(11, source_player=P7, object_list_unit_id=const,
                  location_x=x, location_y=y)


def _hp(f, x, y, qty, const=-1):
    return f._eff(27, source_player=P7, object_list_unit_id=const, quantity=qty,
                  operation=-1, area_x1=x, area_y1=y, area_x2=x, area_y2=y)


def _atk(f, x, y, amount, const=-1):
    e = f._eff(28, source_player=P7, object_list_unit_id=const, quantity=amount,
               operation=2, area_x1=x, area_y1=y, area_x2=x, area_y2=y)
    e.armour_attack_class, e.armour_attack_quantity = 0, amount
    return e


def _gatk(f, amount, const=-1):
    e = f._eff(28, source_player=P7, object_list_unit_id=const, quantity=amount,
               operation=2)
    e.armour_attack_class, e.armour_attack_quantity = 0, amount
    return e


def _rect_atk(f, x1, y1, x2, y2, amount, const):
    e = f._eff(28, source_player=P7, object_list_unit_id=const, quantity=amount,
               operation=2, area_x1=x1, area_y1=y1, area_x2=x2, area_y2=y2)
    e.armour_attack_class, e.armour_attack_quantity = 0, amount
    return e


def _rect_hp(f, x1, y1, x2, y2, qty, const):
    return f._eff(27, source_player=P7, object_list_unit_id=const, quantity=qty,
                  operation=-1, area_x1=x1, area_y1=y1, area_x2=x2, area_y2=y2)


def row(**kw):
    d = dict(tid=0, name='民團', const=74, lv=1, kind='m', itv=2.0,
             base_hp=60, base_atk=17, hp=70, atk=17)
    d.update(kw)
    return d


def test_single_const_rewrites_tile_and_zeroes_global(f):
    t = f.trig(name='民團', tid=0, effects=[
        _create(f, 74, 80, 84), _hp(f, 80, 84, 30), _atk(f, 80, 84, 9),
        _create(f, 74, 77, 80), _hp(f, 77, 80, 30), _atk(f, 77, 80, 9),
        _gatk(f, 20, const=74)])
    tm = f.tm([t])
    changes = apply_mob_balance(tm, [row()])
    assert t.effects[1].quantity == 10 and t.effects[4].quantity == 10          # 70-60
    assert (t.effects[2].armour_attack_class, t.effects[2].armour_attack_quantity) == (0, 0)  # 17-17
    assert t.effects[2].operation == 2
    assert t.effects[6].armour_attack_quantity == 0                              # 全域歸零
    assert [c.kind for c in changes] == ['effect'] * len(changes)
    assert [c.field for c in changes] == ['hp_add', 'atk_add', 'hp_add', 'atk_add', 'global_atk']


def test_two_consts_scoped_by_tile(f):
    t = f.trig(name='劍勇', tid=0, effects=[
        _create(f, 765, 69, 190), _hp(f, 69, 190, 11200, const=765), _atk(f, 69, 190, 975, const=765),
        _create(f, 640, 66, 192), _hp(f, 66, 192, 9750, const=640), _atk(f, 66, 192, 4167, const=640)])
    tm = f.tm([t])
    apply_mob_balance(tm, [
        row(name='劍勇', const=765, base_hp=65, base_atk=9, hp=None, atk=716),
        row(name='劍勇', const=640, base_hp=200, base_atk=26, hp=None, atk=1067)])
    assert t.effects[1].quantity == 11200 and t.effects[4].quantity == 9750     # hp: null 不動
    assert t.effects[2].armour_attack_quantity == 707                            # 716-9
    assert t.effects[5].armour_attack_quantity == 1041                           # 1067-26


def test_name_mismatch_raises(f):
    t = f.trig(name='別的', tid=0, effects=[_create(f, 74, 1, 1), _hp(f, 1, 1, 1), _atk(f, 1, 1, 1)])
    with pytest.raises(BuildError):
        apply_mob_balance(f.tm([t]), [row()])


def test_missing_tile_attack_raises(f):
    t = f.trig(name='民團', tid=0, effects=[_create(f, 74, 1, 1), _hp(f, 1, 1, 1)])
    with pytest.raises(BuildError):
        apply_mob_balance(f.tm([t]), [row()])


def test_negative_delta_raises(f):
    t = f.trig(name='民團', tid=0, effects=[_create(f, 74, 1, 1), _hp(f, 1, 1, 1), _atk(f, 1, 1, 1)])
    with pytest.raises(BuildError):
        apply_mob_balance(f.tm([t]), [row(atk=10)])          # 10 < base_atk 17


def test_duplicate_tile_effects_first_wins_rest_zeroed(f):
    t = f.trig(name='民團', tid=0, effects=[
        _create(f, 74, 1, 1), _hp(f, 1, 1, 5), _hp(f, 1, 1, 25), _atk(f, 1, 1, 4), _atk(f, 1, 1, 5)])
    tm = f.tm([t])
    apply_mob_balance(tm, [row()])
    assert t.effects[1].quantity == 10 and t.effects[2].quantity == 0
    assert t.effects[3].armour_attack_quantity == 0                              # delta 0
    assert t.effects[4].armour_attack_quantity == 0


def test_upper_bound_delta_raises(f):
    t = f.trig(name='民團', tid=0, effects=[_create(f, 74, 1, 1), _hp(f, 1, 1, 1), _atk(f, 1, 1, 1)])
    with pytest.raises(BuildError):
        apply_mob_balance(f.tm([t]), [row(hp=40000)])         # 40000-60=39940 > 32767


def test_noise_effect_of_other_const_untouched(f):
    t = f.trig(name='民團', tid=0, effects=[
        _create(f, 74, 1, 1),
        _hp(f, 1, 1, 30), _hp(f, 1, 1, 50, const=999),
        _atk(f, 1, 1, 9), _atk(f, 1, 1, 7, const=999)])
    tm = f.tm([t])
    apply_mob_balance(tm, [row()])
    assert t.effects[1].quantity == 10                                           # 70-60，正常格
    assert t.effects[2].quantity == 50                                           # 雜訊 const 不動
    assert t.effects[3].armour_attack_quantity == 0                              # 17-17，正常格
    assert t.effects[4].armour_attack_quantity == 7                              # 雜訊 const 不動


def test_area_atk_of_listed_const_zeroed(f):
    # T2711 母夜叉案例：矩形涵蓋生成格、olu=表列 const，總量已折入格效果，須歸零
    t = f.trig(name='民團', tid=0, effects=[
        _create(f, 74, 80, 84), _hp(f, 80, 84, 30), _atk(f, 80, 84, 9),
        _rect_atk(f, 70, 70, 100, 100, 3164, const=74)])
    tm = f.tm([t])
    changes = apply_mob_balance(tm, [row()])
    assert t.effects[3].armour_attack_quantity == 0
    assert any(c.field == 'area_atk' for c in changes)


def test_area_atk_olu_minus1_covering_raises(f):
    t = f.trig(name='民團', tid=0, effects=[
        _create(f, 74, 80, 84), _hp(f, 80, 84, 30), _atk(f, 80, 84, 9),
        _rect_atk(f, 70, 70, 100, 100, 500, const=-1)])
    with pytest.raises(BuildError):
        apply_mob_balance(f.tm([t]), [row()])


def test_area_hp_of_listed_const_raises(f):
    t = f.trig(name='民團', tid=0, effects=[
        _create(f, 74, 80, 84), _hp(f, 80, 84, 30), _atk(f, 80, 84, 9),
        _rect_hp(f, 70, 70, 100, 100, 500, const=74)])
    with pytest.raises(BuildError):
        apply_mob_balance(f.tm([t]), [row()])


def test_area_atk_of_other_const_untouched(f):
    # T2712 青武案例：矩形 olu 非本表 const（就算幾何涵蓋生成格），與本表無關，略過不動
    t = f.trig(name='民團', tid=0, effects=[
        _create(f, 74, 80, 84), _hp(f, 80, 84, 30), _atk(f, 80, 84, 9),
        _rect_atk(f, 70, 70, 100, 100, 500, const=999)])
    tm = f.tm([t])
    apply_mob_balance(tm, [row()])
    assert t.effects[3].armour_attack_quantity == 500

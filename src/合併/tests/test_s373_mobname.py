# -*- coding: utf-8 -*-
"""s373 野怪生成改名：每個帶座標建立效果尾端追加改名、格式、跳過無座標、防呆。"""
import pytest
from steps.base import BuildError
from steps.s373_mobname import apply_mob_names


def spawn(f, tid=2743, name='青銅獅', const=700, locs=((93, 56), (86, 54)), stray=True):
    effs = []
    for x, y in locs:
        effs += [f.eff_remove(sp=7, area=(x, y, x, y)),
                 f.eff_create(sp=7, olu=const, x=x, y=y),
                 f.eff_hp(sel=[], sp=7), f.eff_attack(sel=[], sp=7)]
    if stray:
        effs.append(f.eff_create(sp=7, olu=const))          # 無座標殘留（T2743 E16 型）
    return f.trig(tid=tid, name=name, effects=effs)


def renames(t):
    return [kw for n, kw in t.new_effect.calls if n == 'change_object_name']


def test_one_rename_per_located_create_with_level(f):
    t = spawn(f)
    tm = f.tm([t])
    changes = apply_mob_names(tm, [dict(tid=2743, name='青銅獅', const=700, display='青銅獅', lv=14)])
    rs = renames(t)
    assert len(rs) == 2                                  # 無座標的第 3 個建立不改名
    assert rs[0] == dict(object_list_unit_id=700, source_player=7,
                         area_x1=93, area_y1=56, area_x2=93, area_y2=56, message='Lv14 青銅獅')
    assert rs[1]['area_x1'] == 86 and rs[1]['message'] == 'Lv14 青銅獅'
    kinds = [c.kind for c in changes]
    assert kinds.count('eff_add') == 2 and 'skip' in kinds


def test_no_level_uses_display_only(f):
    t = spawn(f, tid=3998, name='豬王', const=424, locs=((238, 65),), stray=False)
    apply_mob_names(f.tm([t]), [dict(tid=3998, name='豬王', const=424, display='鐵豬王', lv=None)])
    assert renames(t)[0]['message'] == '鐵豬王'


def test_multi_const_trigger_uses_row_per_const(f):
    effs = [f.eff_create(sp=7, olu=424, x=10, y=10), f.eff_create(sp=7, olu=698, x=12, y=10)]
    t = f.trig(tid=4680, name='鐵鎚', effects=effs)
    apply_mob_names(f.tm([t]), [dict(tid=4680, name='鐵鎚', const=424, display='賓周幫幫眾', lv=None),
                                dict(tid=4680, name='鐵鎚', const=698, display='賓周幫幫眾', lv=None)])
    rs = renames(t)
    assert [(r['object_list_unit_id'], r['area_x1']) for r in rs] == [(424, 10), (698, 12)]


def test_name_mismatch_raises(f):
    t = spawn(f)
    with pytest.raises(BuildError):
        apply_mob_names(f.tm([t]), [dict(tid=2743, name='不對', const=700, display='青銅獅', lv=14)])


def test_missing_const_row_raises(f):
    effs = [f.eff_create(sp=7, olu=424, x=10, y=10), f.eff_create(sp=7, olu=698, x=12, y=10)]
    t = f.trig(tid=4680, name='鐵鎚', effects=effs)
    with pytest.raises(BuildError):
        apply_mob_names(f.tm([t]), [dict(tid=4680, name='鐵鎚', const=424, display='賓周幫幫眾', lv=None)])


def test_unused_row_raises(f):
    t = spawn(f)
    with pytest.raises(BuildError):
        apply_mob_names(f.tm([t]), [dict(tid=2743, name='青銅獅', const=700, display='青銅獅', lv=14),
                                    dict(tid=2743, name='青銅獅', const=999, display='幽靈', lv=1)])


def test_duplicate_row_raises(f):
    t = spawn(f)
    with pytest.raises(BuildError):
        apply_mob_names(f.tm([t]), [dict(tid=2743, name='青銅獅', const=700, display='青銅獅', lv=14),
                                    dict(tid=2743, name='青銅獅', const=700, display='青銅獅', lv=14)])


def test_trigger_without_located_create_raises(f):
    t = f.trig(tid=1, name='空', effects=[f.eff_create(sp=7, olu=700)])
    with pytest.raises(BuildError):
        apply_mob_names(f.tm([t]), [dict(tid=1, name='空', const=700, display='x', lv=1)])


def test_missing_trigger_raises(f):
    with pytest.raises(BuildError):
        apply_mob_names(f.tm([]), [dict(tid=5, name='x', const=1, display='x', lv=1)])

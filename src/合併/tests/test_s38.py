# -*- coding: utf-8 -*-
"""T8: s38 展示英雄/備身/容器/職業名——雙世代名萃取、本體改造、備身生成、初始化觸發。"""
import pytest
from types import SimpleNamespace as NS
from core.revive_model import ReviveSpec
from steps.s38_choose import extract_class_names, setup_bodies
from steps.base import BuildError

HERO_CONSTS = {1: 845, 2: 432, 3: 752, 4: 428, 5: 1811, 6: 765}
GEN1 = ['刀客', '劍客', '槍客', '棍僧', '拳師', '暗殺']
GEN2 = ['刀俠', '劍俠', '槍俠', '棍俠', '拳俠', '暗俠']


def rspec(lives=3):
    return ReviveSpec(lives=lives, respawn=(77.5, 103.5),
                      displays={1: (78.5, 108.5), 2: (80.5, 108.5), 3: (82.5, 108.5),
                                4: (83.5, 109.5), 5: (83.5, 111.5), 6: (83.5, 113.5)},
                      hero_refs={1: 0, 2: 1, 3: 2, 4: 502, 5: 7, 6: 45117},
                      retired=list(range(1805, 1811)) + list(range(3821, 3827)))


def name_tm(f):
    trigs = []
    for i in range(6):
        trigs.append(f.trig(tid=1805 + i, effects=[
            f.eff_chat(sp=-1, message=f'<RED>{GEN2[i]}已死亡')]))
    for i in range(6):
        trigs.append(f.trig(tid=3821 + i, effects=[
            f.eff_chat(sp=-1, message=f'<RED>{GEN1[i]}已死亡')]))
    return f.tm(trigs)


def test_extract_class_names_two_generations(f):
    names = extract_class_names(name_tm(f), rspec())
    assert names[1] == ('刀客', '刀俠')
    assert names[5] == ('拳師', '拳俠')


def test_extract_class_names_missing_raises(f):
    tm = f.tm([f.trig(tid=3821, effects=[f.eff_chat(message='沒有死亡字樣')])])
    with pytest.raises(BuildError):
        extract_class_names(tm, rspec())


def make_um(hero_consts=HERO_CONSTS):
    hero_refs = {1: 0, 2: 1, 3: 2, 4: 502, 5: 7, 6: 45117}
    units = [[] for _ in range(9)]
    for cid, ref in hero_refs.items():
        units[cid].append(NS(reference_id=ref, unit_const=hero_consts[cid],
                             x=70.0 + cid, y=100.0, player=cid))
    um = NS(units=units, added=[])
    seq = [90000]

    def add_unit(**kw):
        seq[0] += 1
        u = NS(reference_id=seq[0], **kw)
        um.added.append(u)
        um.units[0 if kw['player'] == 0 else int(kw['player'])].append(u)
        return u

    um.add_unit = add_unit
    return um


def test_setup_bodies_moves_heroes_and_creates_spares(f):
    um = make_um()
    tm = f.tm([])
    out = setup_bodies(um, tm, rspec(), extract=lambda _tm, _r: {c: (GEN1[c - 1], GEN2[c - 1])
                                                                 for c in range(1, 7)})
    # 本體：owner→8、座標→展示位
    hero_refs = {0, 1, 2, 502, 7, 45117}
    heroes = [u for u in um.units[8] if u.reference_id in hero_refs]
    assert len(heroes) == 6
    h1 = next(u for u in heroes if u.reference_id == 0)
    assert (h1.x, h1.y) == (78.5, 108.5) and h1.player == 8
    # 備身 6×2 掛 P8、駐各自容器；容器 6×2＝const1291 Gaia @respawn
    spares = [u for u in um.added if getattr(u, 'garrisoned_in_id', -1) != -1]
    boxes = [u for u in um.added if u.unit_const == 1291]
    navs = [u for u in um.added if u.unit_const == 837]
    assert len(spares) == 12 and len(boxes) == 12 and len(navs) == 12   # 每位2顆顯示器
    assert all(u.player == 8 for u in spares)
    assert all(u.player == 0 and (u.x, u.y) == (77.5, 103.5) for u in boxes)
    box_refs = {u.reference_id for u in boxes}
    assert all(u.garrisoned_in_id in box_refs for u in spares)
    # life_refs：{cid: [本體, 備1, 備2]}
    lr = out['life_refs']
    assert lr[1][0] == 0 and len(lr[1]) == 3
    assert set(lr) == set(range(1, 7))
    # 職業名
    assert out['class_names'][1] == ('刀客', '刀俠')


def test_setup_bodies_spare_const_follows_swapped_hero(f):
    um = make_um()
    tm = f.tm([])
    out = setup_bodies(um, tm, rspec(), extract=lambda *_: {c: ('x', 'y') for c in range(1, 7)})
    spares5 = [u for u in um.added if u.unit_const == 1811]
    assert len(spares5) == 2                      # 拳備身用換皮後 const


def test_setup_bodies_p5_not_swapped_raises(f):
    um = make_um({**HERO_CONSTS, 5: 94})          # s35 沒先跑
    with pytest.raises(BuildError):
        setup_bodies(um, f.tm([]), rspec(), extract=lambda *_: {c: ('x', 'y') for c in range(1, 7)})


def test_setup_bodies_builds_init_triggers(f):
    um = make_um()
    tm = f.tm([])
    setup_bodies(um, tm, rspec(), extract=lambda *_: {c: (GEN1[c - 1], GEN2[c - 1])
                                                      for c in range(1, 7)})
    init = tm.triggers_by_id[[t.trigger_id for t in tm.triggers if t.name == '選角初始化'][0]]
    calls = init.new_effect.calls
    captions = [kw for n, kw in calls if n == 'change_object_caption']
    freezes = [kw for n, kw in calls if n == 'freeze_object']
    gaias = [kw for n, kw in calls if n == 'change_ownership' and kw.get('target_player') == 0]
    hints = [kw for n, kw in calls if n == 'display_instructions']
    assert len(captions) == 6 and captions[0]['message'] == '刀客'    # 血條手法浮動字幕
    assert [kw for n, kw in calls if n == 'change_view'] == []        # 不拉鏡頭
    assert [kw for n, kw in calls if n == 'change_object_name'] == [] # 不改名（保留原作等級格式）
    assert hints[0]['display_time'] == 600
    assert len(freezes) == 6
    assert len(gaias) == 12                       # 備身 P8→Gaia（防歸順）
    assert [t for t in tm.triggers if (t.name or '').startswith('展示無敵')] == []

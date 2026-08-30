# -*- coding: utf-8 -*-
"""T9b-iii: 退役斷邊（活化邊重指/未映射熔斷、停用邊放行）、轉生旗建立、
跨集重指（矩陣變體啟停邊→同位連動變體）、踢人清理鏈。"""
import pytest
from steps.base import BuildError
from steps.revive_retire import (retire_and_cut, build_rebirth_flag_triggers,
                                 repoint_cross, build_kick_cleanup)

MOUNT = {1: dict(mount_ref=26109, flag_cell=(221, 239), rebirth_cell=(230, 239),
                 final_cell=(232, 239))}


def test_retire_cuts_activate_edges_via_repoint(f):
    dead = f.trig(tid=1805, name='1死', enabled=False)
    x51 = f.trig(tid=1690, name='1 51', effects=[f.eff_deactivate(3821),
                                                 f.eff_activate(1805)])
    other = f.trig(effects=[f.eff_deactivate(1805)])
    tm = f.tm([dead, x51, other])
    ch = retire_and_cut(tm, retired=[1805], repoint={1805: 7777})
    assert dead.enabled == 0 and dead.name.startswith('退役_')
    assert x51.effects[1].trigger_id == 7777          # 活化邊重指
    assert x51.effects[0].trigger_id == 3821          # 停用邊照舊
    assert other.effects[0].trigger_id == 1805        # 停用退役觸發＝無害放行


def test_retire_unmapped_activate_edge_raises(f):
    dead = f.trig(tid=1805, name='1死')
    src = f.trig(effects=[f.eff_activate(1805)])
    tm = f.tm([dead, src])
    with pytest.raises(BuildError):
        retire_and_cut(tm, retired=[1805], repoint={})


def test_rebirth_flag_triggers(f):
    tm = f.tm([])
    fmap, ch = build_rebirth_flag_triggers(tm, MOUNT, classes=(1,))
    t = tm.triggers_by_id[fmap[1]]
    assert t.enabled == 0                              # 由 X51 活化邊重指驅動
    creates = [kw for n, kw in t.new_effect.calls if n == 'create_object']
    assert creates[0]['location_x'] == 230 and creates[0]['object_list_unit_id'] == 720


def test_repoint_cross(f):
    dl_orig = f.trig(tid=4204, name='1哥8')
    quest = f.trig(tid=4189, name='1哥5', effects=[f.eff_activate(4204), f.eff_chat(sp=1)])
    tm = f.tm([dl_orig, quest])
    vq = tm.copy_trigger(4189, append_after_source=False, add_suffix=False)   # 位2 變體
    variant_map = {(4189, 1): 4189, (4189, 2): vq.trigger_id}
    dl_vm = {(4204, 1): 8801, (4204, 2): 8802}
    repoint_cross(tm, variant_map, dl_vm)
    assert quest.effects[0].trigger_id == 8801         # slot==class 原觸發也重指
    assert tm.triggers_by_id[vq.trigger_id].effects[0].trigger_id == 8802


def test_kick_cleanup(f):
    fence = f.trig(tid=555, name='踢掉2p', effects=[f.eff_remove(sel=(), sp=2)])
    tm = f.tm([fence])
    chains = dict(watch={(1, 2, 1): 71, (1, 1, 1): 72}, timer={(1, 2, 1): 73},
                  final={(1, 2): 74, (1, 1): 75}, horse={(1, 2, 1): 76},
                  select={(1, 2): 77, (1, 1): 78})
    ch = build_kick_cleanup(tm, chains, fences={2: 555})
    deacts = {kw['trigger_id'] for n, kw in fence.new_effect.calls
              if n == 'deactivate_trigger'}
    assert deacts == {71, 73, 74, 76, 77}              # 只清位2的鏈路，直接掛柵欄


def test_repoint_cross_reverse_dl_to_matrix(f):
    """修端木 型：連動變體（位2）停用 1木 原觸發 → 改指 1木 的位2 矩陣變體；位1（=職業座位）保留原邊。"""
    wood = f.trig(tid=1924, name='1木')
    dl_orig = f.trig(tid=4896, name='修端木1', effects=[f.eff_deactivate(1924)])
    tm = f.tm([wood, dl_orig])
    v1 = tm.copy_trigger(4896, append_after_source=False, add_suffix=False)   # 位1
    v2 = tm.copy_trigger(4896, append_after_source=False, add_suffix=False)   # 位2
    w2 = tm.copy_trigger(1924, append_after_source=False, add_suffix=False)    # 1木 位2 矩陣變體
    variant_map = {(1924, 2): w2.trigger_id}
    dl_vm = {(4896, 1): v1.trigger_id, (4896, 2): v2.trigger_id}
    ch = repoint_cross(tm, variant_map, dl_vm)
    assert v2.effects[0].trigger_id == w2.trigger_id
    assert v1.effects[0].trigger_id == 1924
    assert any('連動→矩陣' in c.reason for c in ch)

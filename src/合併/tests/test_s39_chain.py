# -*- coding: utf-8 -*-
"""T9a: 復活鏈——選角觸發、watch/timer/final、訊息三態、馬監視級聯。
縮小模型：2 職業(1,2)×2 玩家位(1,2)、lives=3。"""
from types import SimpleNamespace as NS
from steps.s39_revive import build_chains

LIVES = 3
LIFE = {1: [0, 900, 901], 2: [1, 910, 911]}
CONTAINERS = {1: [800, 801], 2: [810, 811]}
NAMES = {1: ('刀客', '刀俠'), 2: ('劍客', '劍俠')}
MOUNT = {1: dict(mount_ref=26109, flag_cell=(221, 239), rebirth_cell=(230, 239),
                 final_cell=(232, 239),
                 life_cells=[(50, 239), (51, 239), (52, 239)]),
         2: dict(mount_ref=26186, flag_cell=(221, 238), rebirth_cell=(230, 238),
                 final_cell=(232, 238),
                 life_cells=[(50, 238), (51, 238), (52, 238)])}


def rv(f):
    return dict(
        spec=NS(lives=LIVES, respawn=(77.5, 103.5),
                hero_refs={1: 0, 2: 1},
                displays={1: (78.5, 108.5), 2: (80.5, 108.5)}),
        life_refs=LIFE, containers=CONTAINERS, class_names=NAMES,
        mirrors={1: 14162, 2: 14163},
        enable_lists={(c, s): [] for c in (1, 2) for s in (1, 2)},
        mount=MOUNT, classes=(1, 2), slots=(1, 2))


def build(f, tm=None):
    tm = tm or f.tm([f.trig(tid=501, name='展示無敵1', looping=True),
                     f.trig(tid=502, name='展示無敵2', looping=True)])
    return tm, build_chains(tm, rv(f))


def _effs(t, name):
    return [kw for n, kw in t.new_effect.calls if n == name]


def test_watch_chain_linkage(f):
    tm, out = build(f)
    w1 = tm.triggers_by_id[out.watch[(1, 2, 1)]]
    assert w1.enabled == 0 and w1.looping == 0
    destroys = [kw for n, kw in w1.new_condition.calls if n == 'destroy_object']
    assert destroys[0]['unit_object'] == 0
    assert [kw for n, kw in w1.new_condition.calls if n == 'objects_in_area'] == []
    # 監視純 destroy（v4：上馬由 X馬3 顯式停用當前監視）；啟動 timer 與訊息三態
    acts = {kw['trigger_id'] for kw in _effs(w1, 'activate_trigger')}
    assert out.timer[(1, 2, 1)] in acts
    assert set(out.msgs[(1, 2, 1)]) <= acts


def test_timer_revives_next_life(f):
    tm, out = build(f)
    t1 = tm.triggers_by_id[out.timer[(1, 2, 1)]]
    timers = [kw for n, kw in t1.new_condition.calls if n == 'timer']
    assert timers[0]['timer'] == 10
    owns = _effs(t1, 'change_ownership')
    assert any(kw['selected_object_ids'] == [900] and kw['target_player'] == 2 for kw in owns)
    removes = _effs(t1, 'remove_object')
    assert any(kw.get('selected_object_ids') == [800] for kw in removes)      # 容器1(第2命)
    # 命旗遞移：除命1旗(50,239)、立命2旗(51,239)
    assert any(kw.get('object_list_unit_id') == 720 and kw.get('area_x1') == 50
               for kw in removes)
    creates = _effs(t1, 'create_object')
    assert any(kw.get('object_list_unit_id') == 720 and kw.get('location_x') == 51
               for kw in creates)
    acts = {kw['trigger_id'] for kw in _effs(t1, 'activate_trigger')}
    assert out.watch[(1, 2, 2)] in acts


def test_msg_trio_flag_selection(f):
    tm, out = build(f)
    m_foot, m_gen2, m_horse = [tm.triggers_by_id[x] for x in out.msgs[(1, 2, 1)]]
    txt = lambda t: _effs(t, 'display_instructions')[0]['message']
    assert txt(m_foot) == '<RED>刀客已受傷，10秒後重生(1)'
    assert txt(m_gen2) == '<RED>刀俠已受傷，10秒後重生(1)'
    assert txt(m_horse) == '<RED>馬騎刀俠已受傷，10秒後重生(1)'
    # 旗標條件：馬騎讀騎馬旗(221,239)；俠讀轉生旗(230,239)且無騎馬旗
    a_horse = [kw for n, kw in m_horse.new_condition.calls if n == 'objects_in_area']
    assert a_horse[0]['area_x1'] == 221 and a_horse[0].get('inverted') != 1
    a_gen2 = [kw for n, kw in m_gen2.new_condition.calls if n == 'objects_in_area']
    assert a_gen2[0]['area_x1'] == 221 and a_gen2[0].get('inverted') == 1
    assert a_gen2[1]['area_x1'] == 230 and a_gen2[1].get('inverted') != 1


def test_final_creates_flag_and_revealer(f):
    tm, out = build(f)
    fin = tm.triggers_by_id[out.final[(1, 2)]]
    destroys = [kw for n, kw in fin.new_condition.calls if n == 'destroy_object']
    assert destroys[0]['unit_object'] == 901                                   # 最後一命
    creates = _effs(fin, 'create_object')
    assert any(kw['object_list_unit_id'] == 837 and kw['source_player'] == 2 for kw in creates)
    assert any(kw.get('location_x') == 232 for kw in creates)                  # 命盡旗@final_cell
    # 末命旗(52,239)拔除 → locref 家族熄火
    assert any(kw.get('object_list_unit_id') == 720 and kw.get('area_x1') == 52
               for kw in _effs(fin, 'remove_object'))
    txts = [tm.triggers_by_id[x] for x in out.final_msgs[(1, 2)]]
    assert any('已死亡' in _effs(t, 'display_instructions')[0]['message'] for t in txts)


def test_horse_watch_per_life(f):
    tm, out = build(f)
    hw = tm.triggers_by_id[out.horse[(1, 2, 1)]]
    assert hw.enabled == 0                                        # 由 X馬3◇命L 啟動
    destroys = [kw for n, kw in hw.new_condition.calls if n == 'destroy_object']
    assert destroys[0]['unit_object'] == 26109
    acts = {kw['trigger_id'] for kw in _effs(hw, 'activate_trigger')}
    assert out.timer[(1, 2, 1)] in acts
    assert set(out.msgs[(1, 2, 1)]) <= acts
    # 終命版：訊息＋revealer＋命盡旗
    hwf = tm.triggers_by_id[out.horse[(1, 2, LIVES)]]
    creates = _effs(hwf, 'create_object')
    assert any(kw.get('object_list_unit_id') == 837 for kw in creates)
    assert any(kw.get('location_x') == 232 for kw in creates)
    assert any(kw.get('object_list_unit_id') == 720 and kw.get('area_x1') == 52
               for kw in _effs(hwf, 'remove_object'))


def test_selection_trigger(f):
    tm, out = build(f)
    sel = tm.triggers_by_id[out.select[(1, 2)]]
    conds = [kw for n, kw in sel.new_condition.calls if n == 'object_selected_multiplayer']
    assert conds[0]['unit_object'] == 0 and conds[0]['source_player'] == 2
    owns = _effs(sel, 'change_ownership')
    assert any(kw['selected_object_ids'] == [0] and kw['target_player'] == 2 for kw in owns)
    assert any(kw['selected_object_ids'] == [14162] and kw['target_player'] == 2
               for kw in owns)                                     # 角落鏡像隨選角轉讓
    caps = _effs(sel, 'change_object_caption')
    assert any(kw['selected_object_ids'] == [0] for kw in caps)               # 清職業名字幕
    # 第1命旗(50,239)：locref 家族選路起點
    assert any(kw.get('object_list_unit_id') == 720 and kw.get('location_x') == 50
               for kw in _effs(sel, 'create_object'))
    deacts = {kw['trigger_id'] for kw in _effs(sel, 'deactivate_trigger')}
    assert out.select[(1, 1)] in deacts and out.select[(2, 2)] in deacts      # 互斥
    acts = {kw['trigger_id'] for kw in _effs(sel, 'activate_trigger')}
    assert out.watch[(1, 2, 1)] in acts
    assert out.horse[(1, 2, 1)] not in acts                       # 馬監視由 X馬3 啟動，非選角


def test_all_new_triggers_declared(f):
    tm, out = build(f)
    added = len(tm.triggers) - 2                                   # 扣掉預置的兩支無敵
    assert sum(1 for c in out.changes if c.kind == 'trigger_add') == added

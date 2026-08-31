# -*- coding: utf-8 -*-
"""渡船 spec 區塊結構（2026-08-30 spec §三／§五）：先驗產生器輸出，貼入後同一組斷言驗 merge_spec.yaml。
在 src/合併 下以 python -m pytest 執行（cwd 依賴）。"""
from pathlib import Path
import yaml
from tools import gen_ferry_spec as g

SEATS = range(1, 7)
PIERS = ('東', '西')
KINDS = ('船入', '船暈', '船窗止', '船出', '船清入', '船清出', '船免')
X6 = {'東': {1: 3750, 2: 3755, 3: 3760, 4: 3765, 5: 3770, 6: 3775},
      '西': {1: 3781, 2: 3787, 3: 3793, 4: 3799, 5: 3805, 6: 3811}}
X4 = {'東': ({1: 3748, 2: 3753, 3: 3758, 4: 3763, 5: 3768, 6: 3773}, 1),
      '西': ({1: 3779, 2: 3785, 3: 3791, 4: 3797, 5: 3803, 6: 3809}, 2)}
FERRY_IDS = set(range(3734, 3746)) | {3732, 3733} | set(range(3673, 3686)) \
    | {t for d in X6.values() for t in d.values()} | {t for d, _ in X4.values() for t in d.values()}


def _adds(entries):
    return [e for e in entries if e.get('kind') == 'trigger_add']


def _check_block(entries):
    adds = _adds(entries)
    names = [a['name'] for a in adds]
    assert len(names) == len(set(names)) == 87
    for s in SEATS:
        for p in PIERS:
            for k in KINDS:
                assert f'{s}{k}{p}' in names
    assert {'船卸東', '船卸西', '船旗初始化'} <= set(names)
    # 名稱引用閉合＋先定義後引用
    seen = set()
    for e in entries:
        if e.get('kind') == 'trigger_add':
            for eff in e.get('effects') or []:
                if 'trigger_name' in eff:
                    assert eff['trigger_name'] in seen, eff
            seen.add(e['name'])
        elif e.get('kind') == 'effect_add' and 'trigger_name' in e['effect']:
            assert e['effect']['trigger_name'] in seen, e
    # X船6：CREATE 837 中和（東座位 6 在 E1）、東 E4 頭暈啟動中和、三個啟動＋一個私訊
    for p in PIERS:
        for s, tid in X6[p].items():
            mine = [e for e in entries if e.get('trigger_id') == tid]
            assert all(e['name'] == f'{s}船6' for e in mine)
            create_idx = 1 if (p == '東' and s == 6) else 2
            assert any(e.get('kind') == 'effect' and e.get('field') == 'effect_type' and e.get('index') == create_idx
                       and e.get('old') == 11 and e.get('new') == 0 for e in mine), (p, s)
            if p == '東':
                assert any(e.get('kind') == 'effect' and e.get('index') == 4 and e.get('old') == 8 and e.get('new') == 0 for e in mine)
            adds_ = [e for e in mine if e.get('kind') == 'effect_add']
            acts = sorted(e['effect']['trigger_name'] for e in adds_ if e['effect']['type'] == 'activate_trigger')
            assert acts == sorted([f'{s}船入{p}', f'{s}船窗止{p}', f'{s}船暈{p}', f'{s}船免{p}'])
            chats = [e for e in adds_ if e['effect']['type'] == 'send_chat']
            assert len(chats) == 1 and chats[0]['effect']['source_player'] == s \
                and chats[0]['effect']['message'].startswith('<ORANGE>')
    # X船4：REMOVE 中和（東 E1、西 E2）
    for p, (ids, idx) in X4.items():
        for s, tid in ids.items():
            assert any(e.get('trigger_id') == tid and e['name'] == f'{s}船4' and e.get('kind') == 'effect'
                       and e.get('index') == idx and e.get('old') == 15 and e.get('new') == 0 for e in entries)
    # X草 整支停用；X草2 只中和 E0/E1
    for tid, nm in {3734: '1草', 3736: '2草', 3738: '3草', 3740: '4草', 3742: '5草', 3744: '6草'}.items():
        assert any(e.get('trigger_id') == tid and e['name'] == nm and e.get('kind') == 'trigger'
                   and e.get('field') == 'enabled' and e.get('old') == 1 and e.get('new') == 0 for e in entries)
    for tid, nm in {3735: '1草2.', 3737: '2草2', 3739: '3草2', 3741: '4草2', 3743: '5草2', 3745: '6草2'}.items():
        mine = [e for e in entries if e.get('trigger_id') == tid]
        assert all(e['name'] == nm for e in mine)
        assert sorted(e['index'] for e in mine if e.get('field') == 'effect_type' and e.get('old') == 8 and e.get('new') == 0) == [0, 1]
        assert not any(e.get('kind') == 'trigger' for e in mine)          # 不得整支停用（E2 要活）
    # 船卸：一次性，由 船/船2 各啟動兩岸
    for a in adds:
        if a['name'].startswith('船卸'):
            assert a['enabled'] == 0 and a['looping'] == 0
            assert [c['type'] for c in a['conditions']] == ['timer', 'objects_in_area'] and a['conditions'][0]['timer'] == 8
        if '船入' in a['name']:
            assert [c['type'] for c in a['conditions']] == ['objects_in_area']     # 不再設閱歷門檻（靜默失敗）
        if '船免' in a['name']:
            assert a['enabled'] == 0 and a['looping'] == 1 and a['conditions'] == []
            assert [e['type'] for e in a['effects']] == ['deactivate_trigger'] * 3
            assert all('trigger_id' in e for e in a['effects'])          # 壓的是基底報價鏈，數字 id
    for tid, nm in {3732: '船', 3733: '船2'}.items():
        acts = sorted(e['effect']['trigger_name'] for e in entries
                      if e.get('trigger_id') == tid and e.get('kind') == 'effect_add')
        assert acts == ['船卸東', '船卸西'], (tid, acts)
    # 等級門檻反相（<1159 才推）＋東解除器停用；西清場點＝使用者指定 (79,235)
    for tid in (3673, 3675, 3677, 3679, 3681, 3683, 3685):
        assert any(e.get('trigger_id') == tid and e.get('kind') == 'condition' and e.get('index') == 1
                   and e.get('field') == 'inverted' and e.get('old') == -1 and e.get('new') == 1 for e in entries), tid
    for tid in (3674, 3676, 3678, 3680, 3682, 3684):
        assert any(e.get('trigger_id') == tid and e.get('kind') == 'trigger' and e.get('field') == 'enabled'
                   and e.get('old') == 1 and e.get('new') == 0 for e in entries), tid
    for a in adds:
        if '船清出西' in a['name']:
            eff = a['effects'][0]
            assert (eff['location_x'], eff['location_y']) == (79, 235), a['name']
    # 進場感應區＝貼牆整排（非單一旗格），且入／暈同區；西不得含出港清場格 (79,235)
    ENTER = {'東': (112, 226, 112, 228), '西': (79, 233, 79, 234)}
    for s in SEATS:
        for p in PIERS:
            for kind in ('船入', '船暈'):
                a = next(x for x in adds if x['name'] == f'{s}{kind}{p}')
                c = a['conditions'][0]
                got = (c['area_x1'], c['area_y1'], c['area_x2'], c['area_y2'])
                assert got == ENTER[p], (a['name'], got)
            a = next(x for x in adds if x['name'] == f'{s}船入{p}')
            e = a['effects'][0]
            assert (e['area_x1'], e['area_y1'], e['area_x2'], e['area_y2']) == ENTER[p]
    # 暈在入之前（同 tick 競態）
    for s in SEATS:
        for p in PIERS:
            assert names.index(f'{s}船暈{p}') < names.index(f'{s}船入{p}')
    # 3船6 訊息
    assert any(e.get('trigger_id') == 3760 and e.get('field') == 'message' and '100000' in e['new'] for e in entries)


def test_generator_block():
    _check_block(g.entries())


def test_generator_render_is_valid_yaml_list():
    text = g.render()
    parsed = yaml.safe_load('trigger_fixes:\n' + text)['trigger_fixes']
    assert parsed == g.entries()
    assert all(line.startswith('    ') for line in text.splitlines() if line.strip())


def test_merge_spec_contains_block():
    raw = yaml.safe_load(Path('merge_spec.yaml').read_text(encoding='utf-8'))
    entries = raw['params']['trigger_fixes']
    ferry = [e for e in entries if (e.get('kind') == 'trigger_add' and '船' in e['name'])
             or e.get('trigger_id') in FERRY_IDS]
    _check_block(ferry)

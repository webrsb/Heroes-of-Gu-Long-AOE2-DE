# -*- coding: utf-8 -*-
"""裁決合併：代理產出併回帳本，並與 merge_spec 對帳自動改判 fixed。"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools.merge_verdicts import spec_covers, spec_index, merge


SPEC = [
    {'trigger_id': 3782, 'name': '2船', 'kind': 'effect', 'index': 0, 'field': 'source_player',
     'old': 1, 'new': 2, 'reason': '停止單位錯停1P'},
    {'trigger_id': 199, 'name': '2教頭4', 'kind': 'effect', 'index': 3, 'field': 'effect_type',
     'old': 9, 'new': 8, 'reason': '抄成 DEACT'},
    {'trigger_id': 4713, 'name': '2刀4', 'kind': 'trigger', 'field': 'looping', 'old': 0, 'new': 1,
     'reason': '補循環'},
]


def test_spec_covers_effect_field_exact_match():
    idx = spec_index(SPEC)
    ok, why = spec_covers('X船|2|T3782|E#0|sp', idx)
    assert ok and 'source_player' in why
    assert not spec_covers('X船|2|T3782|E#1|sp', idx)[0]      # 位置不同不算
    assert not spec_covers('X船|2|T3782|E#0|qty', idx)[0]     # 欄位不同不算


def test_spec_covers_trigger_flag_and_foreign():
    idx = spec_index(SPEC)
    assert spec_covers('XC4|2|T4713|整支|enabled/looping', idx)[0]
    assert spec_covers('X船|2|T3782|整支|foreign', idx)[0]     # A 與 C 常是同一 bug 的兩份報告
    assert not spec_covers('X船|2|T3782|整支|struct', idx)[0]


def test_spec_covers_ignores_unknown_tid_and_bad_key():
    idx = spec_index(SPEC)
    assert not spec_covers('X船|2|T9999|E#0|sp', idx)[0]
    assert not spec_covers('壞掉的key', idx)[0]
    assert not spec_covers('X船|2|TNone|組|count', idx)[0]


def test_merge_applies_agent_verdicts_then_autofix(tmp_path):
    from analysis.ledger import save
    led = {'X船|2|T3782|E#0|sp': {'verdict': 'pending', 'reason': ''},
           'X某|1|T111|整支|struct': {'verdict': 'pending', 'reason': ''},
           'X另|3|T222|E#0|qty': {'verdict': 'pending', 'reason': ''}}
    vf = tmp_path / 'a.yaml'
    save(vf, {'X某|1|T111|整支|struct': {'verdict': 'wontfix', 'reason': '同名不同族'},
              'X另|3|T222|E#0|qty': {'verdict': 'pending', 'reason': '建議修：…'},
              '不在帳本的key': {'verdict': 'wontfix', 'reason': 'x'}})
    new, stats = merge(led, [vf], SPEC)
    assert new['X某|1|T111|整支|struct']['verdict'] == 'wontfix'
    assert new['X另|3|T222|E#0|qty']['verdict'] == 'pending'      # spec 沒這條 → 保留代理裁決
    assert new['X船|2|T3782|E#0|sp']['verdict'] == 'fixed'        # spec 有 → 自動改判
    assert stats['from_agents'] == 2 and stats['auto_fixed'] == 1 and stats['unknown_key'] == 1


def test_merge_never_downgrades_agent_wontfix(tmp_path):
    """代理判 wontfix 的不該被 spec 對帳蓋成 fixed（只有 pending 才自動改判）。"""
    from analysis.ledger import save
    led = {'X船|2|T3782|E#0|sp': {'verdict': 'pending', 'reason': ''}}
    vf = tmp_path / 'a.yaml'
    save(vf, {'X船|2|T3782|E#0|sp': {'verdict': 'wontfix', 'reason': '刻意跨座位'}})
    new, _ = merge(led, [vf], SPEC)
    assert new['X船|2|T3782|E#0|sp']['verdict'] == 'wontfix'

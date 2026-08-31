# -*- coding: utf-8 -*-
"""稽核裁決帳本：新增／待裁決／已裁決／消失 四分類，以及一次建檔。"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from analysis import ledger as L


def test_load_missing_file_is_empty(tmp_path):
    assert L.load(tmp_path / '不存在.yaml') == {}


def test_save_and_load_roundtrip(tmp_path):
    p = tmp_path / 'l.yaml'
    L.save(p, {'X船|1|T3685|absent': {'verdict': 'wontfix', 'reason': '原作廢棄路線'}})
    got = L.load(p)
    assert got == {'X船|1|T3685|absent': {'verdict': 'wontfix', 'reason': '原作廢棄路線'}}


def test_classify_four_buckets():
    led = {'a': {'verdict': 'wontfix', 'reason': 'r'},
           'b': {'verdict': 'pending', 'reason': ''},
           'c': {'verdict': 'fixed', 'reason': 'r'}}
    cls = L.classify([('a', 1), ('b', 2), ('d', 4)], led)
    assert [k for k, _ in cls['resolved']] == ['a']
    assert [k for k, _ in cls['pending']] == ['b']
    assert [k for k, _ in cls['new']] == ['d']
    assert [k for k, _ in cls['gone']] == ['c']          # 帳本有、這次沒報＝前提可能被改壞
    assert '消失 1' in L.summary(cls) and '前提被改壞' in L.summary(cls)


def test_unknown_verdict_treated_as_pending(tmp_path):
    p = tmp_path / 'l.yaml'
    p.write_text('entries:\n  - {key: "k", verdict: 亂寫, reason: ""}\n', encoding='utf-8')
    assert L.load(p)['k']['verdict'] == 'pending'


def test_merge_pending_adds_new_keys_only():
    led = {'a': {'verdict': 'wontfix', 'reason': 'r'}}
    cls = L.classify([('a', 1), ('b', 2)], led)
    out = L.merge_pending(led, cls)
    assert out['a']['verdict'] == 'wontfix' and out['b']['verdict'] == 'pending'


def test_duplicate_keys_collapse():
    cls = L.classify([('a', 1), ('a', 2)], {})
    assert len(cls['new']) == 1


def test_roundtrip_with_del_and_control_chars(tmp_path):
    """原作觸發名含 DEL（\x7f少林寺）：原樣寫進 YAML 會讓整份檔案讀不回來。"""
    p = tmp_path / 'l.yaml'
    key = '~首  C1|2|T5294|E#0|sp'
    reason = '原名 "\x7f少林寺" 的訊息\t含控制字元'
    L.save(p, {key: {'verdict': 'wontfix', 'reason': reason}})
    assert '\x7f' not in p.read_text(encoding='utf-8')       # 檔案裡必須是跳脫形式
    got = L.load(p)
    assert got[key]['verdict'] == 'wontfix' and '\x7f少林寺' in got[key]['reason']


def test_load_tolerates_legacy_raw_del(tmp_path):
    p = tmp_path / 'l.yaml'
    p.write_text('entries:\n  - {key: "k", verdict: wontfix, reason: "壞\x7f檔"}\n', encoding='utf-8')
    assert L.load(p)['k']['reason'] == '壞\x7f檔'

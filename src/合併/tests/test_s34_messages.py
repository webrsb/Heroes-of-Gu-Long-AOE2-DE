# -*- coding: utf-8 -*-
"""s34 任務欄文字校正：替換／第 k 次去重／搬欄位，出現次數防呆。"""
import pytest
from types import SimpleNamespace as NS
from steps.base import BuildError
from steps.s34_messages import apply_messages


def mm(**kw):
    base = dict(instructions='', hints='', victory='', loss='', history='', scouts='')
    base.update(kw)
    return NS(**base)


def test_replace_all_occurrences_when_no_occurrence_given():
    m = mm(hints='A 舊字 B 舊字\r\n')
    ch = apply_messages(m, {'replacements': [{'field': 'hints', 'old': '舊字', 'new': '新字', 'expect_count': 2}]})
    assert m.hints == 'A 新字 B 新字\r\n' and ch[0].kind == 'msg_replace'


def test_remove_second_occurrence_only():
    blk = '新增回血術\r\n箭客\r\n'
    m = mm(instructions=f'頭{blk}中{blk}尾')
    apply_messages(m, {'replacements': [{'field': 'instructions', 'old': blk, 'new': '', 'expect_count': 2, 'occurrence': 2}]})
    assert m.instructions == f'頭{blk}中尾'


def test_count_mismatch_raises():
    m = mm(hints='只有一次')
    with pytest.raises(BuildError):
        apply_messages(m, {'replacements': [{'field': 'hints', 'old': '一次', 'new': 'x', 'expect_count': 2}]})


def test_move_victory_changelog_to_history_keeps_credits():
    m = mm(victory='改檔紀錄…\r\n本人鳴謝\r\n', history='')
    ch = apply_messages(m, {'moves': [{'from_field': 'victory', 'to_field': 'history', 'keep': '本人鳴謝\r\n'}]})
    assert m.history == '改檔紀錄…\r\n本人鳴謝\r\n' and m.victory == '本人鳴謝\r\n'
    assert ch[0].kind == 'msg_move'


def test_move_into_nonempty_target_raises_unless_append():
    m = mm(victory='X保留', history='已有')
    with pytest.raises(BuildError):
        apply_messages(m, {'moves': [{'from_field': 'victory', 'to_field': 'history', 'keep': '保留'}]})
    apply_messages(m, {'moves': [{'from_field': 'victory', 'to_field': 'history', 'keep': '保留', 'append': True}]})
    assert m.history == '已有X保留'


def test_unknown_field_raises():
    with pytest.raises(BuildError):
        apply_messages(mm(), {'replacements': [{'field': 'title', 'old': 'a', 'new': 'b'}]})

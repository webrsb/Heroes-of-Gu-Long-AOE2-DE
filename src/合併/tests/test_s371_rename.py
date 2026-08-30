# -*- coding: utf-8 -*-
"""s371 觸發重命名：套用、舊名防呆、重複防呆、對稱稽核吃得到座位首碼。"""
import pytest
from steps.base import BuildError
from steps.s371_rename import apply_renames
from analysis.audit_symmetry import seat_pattern


def test_rename_applies_and_records_change(f):
    t = f.trig(tid=5399, name='觸發事件 3')
    ch = apply_renames(f.tm([t]), [{'tid': 5399, 'old': '觸發事件 3', 'new': '3客棧8罰'}])
    assert t.name == '3客棧8罰' and ch[0].kind == 'rename' and ch[0].old == '觸發事件 3'


def test_old_name_mismatch_raises(f):
    t = f.trig(tid=5399, name='別名')
    with pytest.raises(BuildError):
        apply_renames(f.tm([t]), [{'tid': 5399, 'old': '觸發事件 3', 'new': '3客棧8罰'}])


def test_duplicate_tid_raises(f):
    t = f.trig(tid=1, name='觸發事件 1')
    with pytest.raises(BuildError):
        apply_renames(f.tm([t]), [{'tid': 1, 'old': '觸發事件 1', 'new': 'a'}, {'tid': 1, 'old': 'a', 'new': 'b'}])


def test_new_names_group_by_leading_seat_digit():
    assert seat_pattern('3客棧8罰') == (3, 'X客棧8罰')
    assert seat_pattern('5拳氣起') == (5, 'XC氣起')          # 職業字換 C，六座位同組
    assert seat_pattern('6當僧') == (6, 'X當僧')

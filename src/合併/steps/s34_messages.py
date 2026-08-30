# -*- coding: utf-8 -*-
"""s34 任務欄文字校正（params.messages）。

只修正面板「已經寫出來、但與觸發實碼不符」的文字，不新增任何面板未揭露的任務或隱藏機制（保持原作神祕性）。
三種操作，皆帶防呆（舊字串出現次數必須等於 expect_count，否則 BuildError 要求重查）：
  replacements: {field, old, new, expect_count=1, occurrence=None|k}  — occurrence=k 只換第 k 次（去重用 new: ''）
  moves:        {from_field, to_field, keep}                          — 把 from 欄全文搬到 to 欄尾端，from 欄只留 keep
面板欄位：instructions / hints / victory / loss / history / scouts（原文 CRLF 換行，spec 的 old/new 用雙引號字串寫 \\r\\n）。
"""
from core.change import Change
from .base import Step, BuildError

FIELDS = ('instructions', 'hints', 'victory', 'loss', 'history', 'scouts')


def _field(mm, name):
    if name not in FIELDS:
        raise BuildError(f'缺裁決：messages 欄位「{name}」不在 {FIELDS}')
    return getattr(mm, name) or ''


def _nth(text, sub, k):
    idx = -1
    for _ in range(k):
        idx = text.find(sub, idx + 1)
        if idx < 0:
            return -1
    return idx


def apply_messages(mm, params):
    changes = []
    for r in params.get('replacements') or []:
        f, old, new = r['field'], r['old'], r['new']
        text = _field(mm, f)
        n = text.count(old)
        expect = int(r.get('expect_count', 1))
        if n != expect:
            raise BuildError(f'缺裁決：messages.{f} 「{old[:24]}…」出現 {n} 次 ≠ 預期 {expect}，請重查')
        occ = r.get('occurrence')
        if occ is None:
            text = text.replace(old, new)
        else:
            i = _nth(text, old, int(occ))
            text = text[:i] + new + text[i + len(old):]
        setattr(mm, f, text)
        changes.append(Change('s34', 'msg_replace', f'messages.{f}', 'text', old[:40], new[:40] or '(刪除)',
                              r.get('reason', '')))
    for m in params.get('moves') or []:
        src, dst, keep = m['from_field'], m['to_field'], m['keep']
        st, dt = _field(mm, src), _field(mm, dst)
        if keep not in st:
            raise BuildError(f'缺裁決：messages.{src} 找不到保留段「{keep[:24]}…」，請重查')
        if dt.strip() and not m.get('append'):
            raise BuildError(f'缺裁決：messages.{dst} 非空（{len(dt)} 字），要附加請填 append: true')
        setattr(mm, dst, dt + st)
        setattr(mm, src, keep)
        changes.append(Change('s34', 'msg_move', f'messages.{src}→{dst}', 'text', f'{len(st)} 字',
                              f'{src} 留 {len(keep)} 字', m.get('reason', '')))
    return changes


class MessagesStep(Step):
    id = 's34'
    title = '任務欄文字校正'
    intro = '依 params.messages 修正面板與觸發實碼不符的文字、去重、搬改檔紀錄；不新增面板未揭露的機制。'

    def apply(self, ctx):
        params = ctx.spec.params.get('messages')
        if not params:
            return []
        return apply_messages(ctx.base.message_manager, params)

    def test_guide(self, changes):
        if not changes:
            return None
        return (f'任務欄文字：{len(changes)} 處。遊戲內開任務欄看提示頁：迪加獎勵改成「做3個…做5個…」、'
                '技能點費用多了第九招 80 點註記、神兵說明五段一致；改檔紀錄移到歷史頁。\n'
                '陽性對照：入侵者強弱排名表原文不動。')


STEP = MessagesStep()

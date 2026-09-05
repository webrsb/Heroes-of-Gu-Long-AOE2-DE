# -*- coding: utf-8 -*-
"""s51 狀態頭頂字幕（spec docs/superpowers/specs/2026-09-02-狀態頭頂字幕-design.md）。
狀態牌（每職業一顆，Change Object Name 寫入）→ 同觸發尾端附掛 change_object_caption
到該職業全部命 ref；清除類與「條件引用 mount_ref」的觸發加掛 mount_ref。
重生 timer／上馬拷貝補 caption ' '，保證新身體/新馬出場乾淨（替身不顯示）。
sel 有值時 sp 不過濾（通用指南 §7.1 實測）→ caption 一律 source_player=-1。"""
from core.change import Change
from .base import Step, BuildError, trig_by_id

CLEAR = ' '                       # caption 清除慣用手法（s39 清職業名同式）
RENAME, CAPTION, ACTIVATE, OWNERSHIP = 26, 88, 8, 18


def load_status_caption(sc: dict):
    """裁決表載入：boards 六職業齊；texts find(strip) 唯一、to: null＝清除。"""
    boards = {int(k): int(v) for k, v in (sc.get('boards') or {}).items()}
    if sorted(boards.values()) != [1, 2, 3, 4, 5, 6]:
        raise BuildError(f'缺裁決：status_caption.boards 職業覆蓋不齊：{boards}')
    texts = {}
    for row in sc.get('texts') or []:
        find = str(row['find']).strip()
        if find in texts:
            raise BuildError(f'缺裁決：status_caption.texts 重複 find「{find}」')
        to = row.get('to')
        texts[find] = CLEAR if to is None else str(to)
    if not texts:
        raise BuildError('缺裁決：status_caption.texts 空表')
    return boards, texts


def cond_refs(t):
    refs = set()
    for c in t.conditions:
        for a in ('unit_object', 'next_object'):
            v = getattr(c, a, -1)
            if v not in (-1, None):
                refs.add(v)
    return refs


def derive_boards(tm, life_refs, candidates):
    """由原觸發「X毒」推導 牌ref→職業，與裁決表對帳（spec §二.2，防寫死盲信）。
    原作重名前科（「6毒」＝T955 毒鏢任務＋T4472 設定器）→ 同名觸發以
    「恰一個狀態牌寫入」過濾，倖存者必須恰一支。"""
    derived = {}
    for cid in range(1, 7):
        named = [x for x in tm.triggers if (x.name or '') == f'{cid}毒']
        cands = []
        for t in named:
            hits = [e.selected_object_ids[0] for e in t.effects
                    if getattr(e, 'effect_type', None) == RENAME
                    and len(getattr(e, 'selected_object_ids', None) or []) == 1
                    and e.selected_object_ids[0] in candidates]
            if len(hits) == 1:
                cands.append((t, hits[0]))
        if len(cands) != 1:
            raise BuildError(f'缺前置：「{cid}毒」帶恰一個狀態牌寫入的觸發不是恰一支'
                             f'（同名 {len(named)}、倖存 {len(cands)}）')
        t, board = cands[0]
        if life_refs[cid][0] not in cond_refs(t):
            raise BuildError(f'缺前置：「{cid}毒」條件未引用職業{cid}本體 ref{life_refs[cid][0]}')
        derived[board] = cid
    return derived


class StatusCaptionStep(Step):
    id = 's51'
    title = '狀態字幕'
    intro = '狀態牌寫入→頭頂 caption 附掛；重生/上馬清字（spec 2026-09-02）。'

    def apply(self, ctx):
        sc = ctx.spec.params.get('status_caption')
        if not sc:
            return []
        rv = ctx.notes.get('revive') or {}
        life_refs = rv.get('life_refs')
        if not life_refs:
            raise BuildError('缺前置：notes[revive].life_refs 不存在（s38 未跑？）')
        boards, texts = load_status_caption(sc)
        tm = ctx.base.trigger_manager
        derived = derive_boards(tm, life_refs, set(boards))
        if derived != boards:
            raise BuildError(f'缺裁決：牌ref→職業推導 {derived} 與 boards {boards} 不一致')
        return []          # 掃描附掛與清字 hooks 由 Task 4/5 補上

    def test_guide(self, changes):
        return None


STEP = StatusCaptionStep()

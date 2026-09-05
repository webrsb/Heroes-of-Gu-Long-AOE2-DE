# -*- coding: utf-8 -*-
"""s91 特徵斷言：狀態頭頂字幕（spec 2026-09-02 §五）。
獨立於 s51 重驗**最終觸發狀態**：每個狀態牌寫入其後有正確 caption（命ref 全覆蓋、
清除類/馬設定器含 mount_ref）、重生/上馬清字齊、表外文字與混搭 sel 為零。
回傳 [(ok, msg)]，s91 對 not ok 者升 BuildError。"""
from steps.base import trig_by_id

RENAME, CAPTION, OWNERSHIP = 26, 88, 18
CLEAR = ' '


def _cond_refs(t):
    refs = set()
    for c in t.conditions:
        for a in ('unit_object', 'next_object'):
            v = getattr(c, a, -1)
            if v not in (-1, None):
                refs.add(v)
    return refs


def _sel(e):
    return list(getattr(e, 'selected_object_ids', None) or [])


def check_status_caption(tm, params, notes):
    sc = params['status_caption']
    boards = {int(k): int(v) for k, v in sc['boards'].items()}
    texts = {str(r['find']).strip(): (CLEAR if r.get('to') is None else str(r['to']))
             for r in sc['texts']}
    life_refs = (notes.get('revive') or {}).get('life_refs') or {}
    if not life_refs:
        return [(False, '缺 notes[revive].life_refs，無從驗證')]
    mount_refs = {int(k): int(v) for k, v in params['revive']['mount_refs'].items()}
    rvo = notes.get('revive_out') or {}
    out, n_writes = [], 0
    board_set = set(boards)

    for t in tm.triggers:
        effs = list(t.effects)
        for i, e in enumerate(effs):
            if getattr(e, 'effect_type', None) != RENAME:
                continue
            sel = _sel(e)
            if not (set(sel) & board_set):
                continue
            if len(sel) != 1:
                out.append((False, f'T{t.trigger_id}「{t.name}」狀態牌 sel 混搭 {sel}'))
                continue
            n_writes += 1
            head = texts.get((getattr(e, 'message', '') or '').strip())
            if head is None:
                out.append((False, f'T{t.trigger_id}「{t.name}」表外狀態文字'))
                continue
            cid = boards[sel[0]]
            need = set(life_refs[cid])
            if head == CLEAR or mount_refs[cid] in _cond_refs(t):
                need.add(mount_refs[cid])
            ok = any(getattr(x, 'effect_type', None) == CAPTION
                     and getattr(x, 'message', None) == head
                     and need <= set(_sel(x))
                     for x in effs[i + 1:])
            out.append((ok, f'T{t.trigger_id}「{t.name}」寫牌後應有 caption「{head}」全目標'))

    def has_clear(t, refs):
        return any(getattr(x, 'effect_type', None) == CAPTION
                   and getattr(x, 'message', None) == CLEAR
                   and set(refs) <= set(_sel(x))
                   for x in t.effects)

    for key, tid in sorted(((rvo.get('chains') or {}).get('timer') or {}).items()):
        t = trig_by_id(tm, tid)
        dep = [x for x in t.effects if getattr(x, 'effect_type', None) == OWNERSHIP
               and getattr(x, 'source_player', -1) == 0]
        refs = _sel(dep[0]) if len(dep) == 1 else []
        out.append((bool(refs) and has_clear(t, refs),
                    f'重生 T{tid}「{t.name}」應清字於部署 ref'))
    for (cid, s, L), tid in sorted((rvo.get('mount_copies') or {}).items()):
        t = trig_by_id(tm, tid)
        out.append((has_clear(t, [mount_refs[cid]]),
                    f'上馬拷貝 T{tid}「{t.name}」應清字於 mount ref'))
    out.append((n_writes > 0, f'狀態牌寫入共 {n_writes} 個（0＝掃描壞掉）'))
    return out

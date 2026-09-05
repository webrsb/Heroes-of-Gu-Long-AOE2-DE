# -*- coding: utf-8 -*-
"""s91 特徵斷言：狀態頭頂字幕（spec 2026-09-02 §五）。
獨立於 s51 重驗**最終觸發狀態**：每個狀態牌寫入其後有正確 caption（命ref 全覆蓋、
清除類/馬設定器含 mount_ref）、重生/上馬清字齊、表外文字與混搭 sel 為零、
六職業寫入覆蓋（防座位變體縮水）、部署觸發獨立列舉與 notes 對帳（防 s39→notes 共源盲點）。
回傳 [(ok, msg)]，s91 對 not ok 者升 BuildError。
註：trig_by_id 僅為觸發查找工具、非寫入端規則邏輯，借用不違反獨立重驗原則。"""
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
    mount_refs = {int(k): int(v)
                  for k, v in ((params.get('revive') or {}).get('mount_refs') or {}).items()}
    if sorted(mount_refs) != [1, 2, 3, 4, 5, 6]:
        return [(False, f'params.revive.mount_refs 職業覆蓋不齊：{mount_refs}，無從驗證')]
    rvo = notes.get('revive_out') or {}
    out, writes_per_class = [], {}
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
            cid = boards[sel[0]]
            writes_per_class[cid] = writes_per_class.get(cid, 0) + 1
            head = texts.get((getattr(e, 'message', '') or '').strip())
            if head is None:
                out.append((False, f'T{t.trigger_id}「{t.name}」職業{cid} 表外狀態文字'))
                continue
            need = set(life_refs[cid])
            if head == CLEAR or mount_refs[cid] in _cond_refs(t):
                need.add(mount_refs[cid])
            ok = any(getattr(x, 'effect_type', None) == CAPTION
                     and getattr(x, 'message', None) == head
                     and need <= set(_sel(x))
                     for x in effs[i + 1:])
            out.append((ok, f'T{t.trigger_id}「{t.name}」職業{cid}牌{sel[0]} '
                            f'寫牌後應有 caption「{head}」全目標'))

    for cid in sorted(set(boards.values())):   # 防座位變體/職業族群縮水（哨兵有鑑別力版）
        n = writes_per_class.get(cid, 0)
        out.append((n > 0, f'職業{cid} 狀態牌寫入 {n} 個（0＝該職業全漏，變體縮水？）'))

    def has_clear(t, refs):
        return any(getattr(x, 'effect_type', None) == CAPTION
                   and getattr(x, 'message', None) == CLEAR
                   and set(refs) <= set(_sel(x))
                   for x in t.effects)

    timer_map = (rvo.get('chains') or {}).get('timer') or {}
    for (cid, _s, L), tid in sorted(timer_map.items()):
        t = trig_by_id(tm, tid)
        if t is None:
            out.append((False, f'重生 T{tid} 不存在（notes 列舉失真）'))
            continue
        dep = [x for x in t.effects if getattr(x, 'effect_type', None) == OWNERSHIP
               and getattr(x, 'source_player', -1) == 0]
        refs = _sel(dep[0]) if len(dep) == 1 else []
        lifes = life_refs.get(cid) or []
        expected = lifes[L] if 0 <= L < len(lifes) else None
        out.append((bool(refs) and expected is not None
                    and refs == [expected] and has_clear(t, refs),
                    f'重生 T{tid}「{t.name}」應清字於部署 ref（鍵 職業{cid}命{L}）'))
    # 部署觸發獨立列舉 vs notes 列舉（notes 若漏列，s51 不掛清字、逐支驗也看不見——這排補上）
    all_life = {r for refs in life_refs.values() for r in refs}
    indep = sum(1 for t in tm.triggers
                if any(getattr(e, 'effect_type', None) == OWNERSHIP
                       and getattr(e, 'source_player', -1) == 0
                       and (set(_sel(e)) & all_life)
                       for e in t.effects))
    out.append((indep == len(timer_map),
                f'部署觸發獨立列舉 {indep} 支 vs notes 列舉 {len(timer_map)} 支'))

    for (cid, _s, _L), tid in sorted((rvo.get('mount_copies') or {}).items()):
        t = trig_by_id(tm, tid)
        if t is None:
            out.append((False, f'上馬拷貝 T{tid} 不存在（notes 列舉失真）'))
            continue
        out.append((has_clear(t, [mount_refs[cid]]),
                    f'上馬拷貝 T{tid}「{t.name}」應清字於 mount ref'))
    return out

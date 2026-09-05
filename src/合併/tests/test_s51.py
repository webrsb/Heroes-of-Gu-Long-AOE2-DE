# -*- coding: utf-8 -*-
"""s51 狀態頭頂字幕（spec 2026-09-02）：載入/推導/掃描附掛/清字 hooks/報告項。"""
import pytest
from types import SimpleNamespace as NS
from steps.base import BuildError

BOARDS = {20501: 1, 20502: 2, 20504: 3, 20503: 4, 20505: 5, 20506: 6}
B_OF = {v: k for k, v in BOARDS.items()}                     # 職業→牌ref
LIFE = {c: [c * 10, c * 10 + 1, c * 10 + 2] for c in range(1, 7)}
MOUNT = {c: 900 + c for c in range(1, 7)}
POISON_RAW = '中毒　狀態　2秒-100生命值'
POISON_HEAD = '中毒 2秒-100精力'
TEXTS = [{'find': POISON_RAW, 'to': POISON_HEAD},
         {'find': '正常　狀態', 'to': None}]


def poison_trigs(f):
    """六支「X毒」原觸發：推導牌ref用（條件引用本體 ref、E 改牌）。"""
    return [f.trig(name=f'{cid}毒',
                   conds=[f.cond_bring_obj(777, LIFE[cid][0])],
                   effects=[f.eff_rename([B_OF[cid]], message=POISON_RAW)])
            for cid in range(1, 7)]


def hook_trigs(f):
    """最小清字 hook 固定件：一支重生 timer＋一支上馬拷貝。"""
    tmr = f.trig(name='重生1位1命1', effects=[f.eff_ownership([LIFE[1][1]], sp=0, tp=1)])
    mcp = f.trig(name='1馬3◇命1')
    return tmr, mcp


def make_ctx(f, extra_trigs=(), texts=TEXTS, boards=BOARDS, notes_patch=None):
    tmr, mcp = hook_trigs(f)
    tm = f.tm(poison_trigs(f) + list(extra_trigs) + [tmr, mcp])
    notes = {'revive': {'life_refs': LIFE},
             'revive_out': {'chains': {'timer': {(1, 1, 1): tmr.trigger_id}},
                            'mount_copies': {(1, 1, 1): mcp.trigger_id}}}
    if notes_patch:
        notes = notes_patch(notes)
    params = {'status_caption': {'boards': dict(boards), 'texts': list(texts)},
              'revive': {'mount_refs': dict(MOUNT)}}
    return NS(base=NS(trigger_manager=tm), spec=NS(params=params), notes=notes), tm


def caption_calls(t):
    return [obj for name, obj in t.new_effect.calls if name == 'change_object_caption']


def test_load_rejects_incomplete_boards(f):
    from steps.s51_status_caption import load_status_caption
    with pytest.raises(BuildError):
        load_status_caption({'boards': {20501: 1}, 'texts': TEXTS})


def test_load_rejects_duplicate_find(f):
    from steps.s51_status_caption import load_status_caption
    with pytest.raises(BuildError):
        load_status_caption({'boards': BOARDS,
                             'texts': TEXTS + [{'find': POISON_RAW, 'to': 'X'}]})


def test_load_maps_null_to_clear(f):
    from steps.s51_status_caption import load_status_caption, CLEAR
    _, texts = load_status_caption({'boards': BOARDS, 'texts': TEXTS})
    assert texts['正常　狀態'] == CLEAR
    assert texts[POISON_RAW] == POISON_HEAD


def test_derive_boards_from_poison_family(f):
    from steps.s51_status_caption import derive_boards
    tm = f.tm(poison_trigs(f))
    assert derive_boards(tm, LIFE, set(BOARDS)) == BOARDS


def test_derive_boards_mismatch_raises(f):
    from steps.s51_status_caption import StatusCaptionStep
    swapped = dict(BOARDS)
    swapped[20503], swapped[20504] = swapped[20504], swapped[20503]   # 抹掉 3/4 對調
    ctx, _ = make_ctx(f, boards=swapped)
    with pytest.raises(BuildError):
        StatusCaptionStep().apply(ctx)


def test_derive_boards_missing_poison_raises(f):
    from steps.s51_status_caption import derive_boards
    tm = f.tm(poison_trigs(f)[:5])            # 少「6毒」
    with pytest.raises(BuildError):
        derive_boards(tm, LIFE, set(BOARDS))


def test_derive_boards_tolerates_name_collision(f):
    # 原作重名前科：「6毒」＝T955 毒鏢任務（無牌寫入）＋T4472 設定器。decoy 放最前驗順序無關。
    from steps.s51_status_caption import derive_boards
    decoy = f.trig(name='6毒', effects=[f.eff_chat(sp=6, message='學毒鏢')])
    tm = f.tm([decoy] + poison_trigs(f))
    assert derive_boards(tm, LIFE, set(BOARDS)) == BOARDS

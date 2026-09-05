# -*- coding: utf-8 -*-
"""s91 特徵斷言：狀態頭頂字幕——獨立重驗最終觸發狀態（spec §五）。"""
from types import SimpleNamespace as NS

BOARDS = {20501: 1, 20502: 2, 20504: 3, 20503: 4, 20505: 5, 20506: 6}
LIFE = {c: [c * 10, c * 10 + 1, c * 10 + 2] for c in range(1, 7)}
MOUNT = {c: 900 + c for c in range(1, 7)}
RAW, HEAD = '中毒　狀態　2秒-100生命值', '中毒 2秒-100精力'
PARAMS = {'status_caption': {'boards': BOARDS,
                             'texts': [{'find': RAW, 'to': HEAD},
                                       {'find': '正常　狀態', 'to': None}]},
          'revive': {'mount_refs': MOUNT}}


def build(f, write_effects, timer_effects=None, mount_effects=None):
    w = f.trig(name='1毒x', effects=write_effects)
    tmr = f.trig(name='重生1位1命1', effects=timer_effects if timer_effects is not None
                 else [f.eff_ownership([LIFE[1][1]], sp=0, tp=1),
                       f.eff_caption([LIFE[1][1]], message=' ')])
    mcp = f.trig(name='1馬3◇命1', effects=mount_effects if mount_effects is not None
                 else [f.eff_caption([MOUNT[1]], message=' ')])
    tm = f.tm([w, tmr, mcp])
    notes = {'revive': {'life_refs': LIFE},
             'revive_out': {'chains': {'timer': {(1, 1, 1): tmr.trigger_id}},
                            'mount_copies': {(1, 1, 1): mcp.trigger_id}}}
    return tm, notes


def bad(results):
    return [msg for ok, msg in results if not ok]


def test_all_green(f):
    from analysis.status_check import check_status_caption
    tm, notes = build(f, [f.eff_rename([20501], message=RAW),
                          f.eff_caption(LIFE[1], message=HEAD)])
    assert bad(check_status_caption(tm, PARAMS, notes)) == []


def test_missing_caption_flagged(f):
    from analysis.status_check import check_status_caption
    tm, notes = build(f, [f.eff_rename([20501], message=RAW)])
    assert any('1毒x' in m for m in bad(check_status_caption(tm, PARAMS, notes)))


def test_wrong_text_flagged(f):
    from analysis.status_check import check_status_caption
    tm, notes = build(f, [f.eff_rename([20501], message=RAW),
                          f.eff_caption(LIFE[1], message='錯字')])
    assert any('1毒x' in m for m in bad(check_status_caption(tm, PARAMS, notes)))


def test_clear_must_cover_mount(f):
    from analysis.status_check import check_status_caption
    tm, notes = build(f, [f.eff_rename([20501], message='正常　狀態'),
                          f.eff_caption(LIFE[1], message=' ')])   # 少 mount ref
    assert any('1毒x' in m for m in bad(check_status_caption(tm, PARAMS, notes)))


def test_hook_missing_flagged(f):
    from analysis.status_check import check_status_caption
    tm, notes = build(f, [f.eff_rename([20501], message=RAW),
                          f.eff_caption(LIFE[1], message=HEAD)],
                      timer_effects=[f.eff_ownership([LIFE[1][1]], sp=0, tp=1)])
    assert any('重生' in m for m in bad(check_status_caption(tm, PARAMS, notes)))

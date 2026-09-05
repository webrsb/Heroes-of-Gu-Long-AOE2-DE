# -*- coding: utf-8 -*-
"""s91 特徵斷言：狀態頭頂字幕——獨立重驗最終觸發狀態（spec §五）。"""

BOARDS = {20501: 1, 20502: 2, 20504: 3, 20503: 4, 20505: 5, 20506: 6}
B_OF = {v: k for k, v in BOARDS.items()}
LIFE = {c: [c * 10, c * 10 + 1, c * 10 + 2] for c in range(1, 7)}
MOUNT = {c: 900 + c for c in range(1, 7)}
RAW, HEAD = '中毒　狀態　2秒-100生命值', '中毒 2秒-100精力'
PARAMS = {'status_caption': {'boards': BOARDS,
                             'texts': [{'find': RAW, 'to': HEAD},
                                       {'find': '正常　狀態', 'to': None}]},
          'revive': {'mount_refs': MOUNT}}


def build(f, write_effects, write_conds=(), timer_effects=None, mount_effects=None,
          bg_classes=range(2, 7), extra_trigs=()):
    """職業1 寫入器由測試自組；2-6 給合規背景寫入（餵飽六職業覆蓋哨兵）。"""
    w = f.trig(name='1毒x', conds=list(write_conds), effects=write_effects)
    bg = [f.trig(name=f'{c}毒x', effects=[f.eff_rename([B_OF[c]], message=RAW),
                                        f.eff_caption(LIFE[c], message=HEAD)])
          for c in bg_classes]
    tmr = f.trig(name='重生1位1命1', effects=timer_effects if timer_effects is not None
                 else [f.eff_ownership([LIFE[1][1]], sp=0, tp=1),
                       f.eff_caption([LIFE[1][1]], message=' ')])
    mcp = f.trig(name='1馬3◇命1', effects=mount_effects if mount_effects is not None
                 else [f.eff_caption([MOUNT[1]], message=' ')])
    tm = f.tm([w] + bg + list(extra_trigs) + [tmr, mcp])
    notes = {'revive': {'life_refs': LIFE},
             'revive_out': {'chains': {'timer': {(1, 1, 1): tmr.trigger_id}},
                            'mount_copies': {(1, 1, 1): mcp.trigger_id}}}
    return tm, notes


def bad(results):
    return [msg for ok, msg in results if not ok]


def run(f, **kw):
    from analysis.status_check import check_status_caption
    tm, notes = build(f, **kw)
    return check_status_caption(tm, PARAMS, notes), tm, notes


def test_all_green(f):
    res, _, _ = run(f, write_effects=[f.eff_rename([20501], message=RAW),
                                      f.eff_caption(LIFE[1], message=HEAD)])
    assert bad(res) == []


def test_missing_caption_flagged(f):
    res, _, _ = run(f, write_effects=[f.eff_rename([20501], message=RAW)])
    assert any('1毒x' in m and '職業1' in m for m in bad(res))


def test_wrong_text_flagged(f):
    res, _, _ = run(f, write_effects=[f.eff_rename([20501], message=RAW),
                                      f.eff_caption(LIFE[1], message='錯字')])
    assert any('1毒x' in m for m in bad(res))


def test_caption_before_write_flagged(f):
    res, _, _ = run(f, write_effects=[f.eff_caption(LIFE[1], message=HEAD),
                                      f.eff_rename([20501], message=RAW)])
    assert any('1毒x' in m for m in bad(res))


def test_clear_must_cover_mount(f):
    res, _, _ = run(f, write_effects=[f.eff_rename([20501], message='正常　狀態'),
                                      f.eff_caption(LIFE[1], message=' ')])   # 少 mount ref
    assert any('1毒x' in m for m in bad(res))


def test_nonclear_mount_keyed_missing_mount_flagged(f):
    # M1 突變殺手：非清除、條件引用 mount_ref → caption 需含馬；漏馬要被抓
    res, _, _ = run(f, write_conds=[f.cond_bring_obj(777, MOUNT[1])],
                    write_effects=[f.eff_rename([20501], message=RAW),
                                   f.eff_caption(LIFE[1], message=HEAD)])
    assert any('1毒x' in m for m in bad(res))


def test_mixed_sel_flagged(f):
    res, _, _ = run(f, write_effects=[f.eff_rename([20501, 999], message=RAW),
                                      f.eff_caption(LIFE[1], message=HEAD)])
    assert any('混搭' in m for m in bad(res))


def test_off_table_text_flagged(f):
    res, _, _ = run(f, write_effects=[f.eff_rename([20501], message='不明狀態'),
                                      f.eff_caption(LIFE[1], message=HEAD)])
    assert any('表外' in m for m in bad(res))


def test_hook_missing_flagged(f):
    res, _, _ = run(f, write_effects=[f.eff_rename([20501], message=RAW),
                                      f.eff_caption(LIFE[1], message=HEAD)],
                    timer_effects=[f.eff_ownership([LIFE[1][1]], sp=0, tp=1)])
    assert any('重生' in m for m in bad(res))


def test_mount_hook_missing_flagged(f):
    res, _, _ = run(f, write_effects=[f.eff_rename([20501], message=RAW),
                                      f.eff_caption(LIFE[1], message=HEAD)],
                    mount_effects=[])
    assert any('上馬拷貝' in m for m in bad(res))


def test_class_coverage_flagged(f):
    res, _, _ = run(f, write_effects=[f.eff_rename([20501], message=RAW),
                                      f.eff_caption(LIFE[1], message=HEAD)],
                    bg_classes=range(2, 6))          # 職業6 無寫入
    assert any('職業6' in m and '全漏' in m for m in bad(res))


def test_timer_enumeration_mismatch_flagged(f):
    # notes 漏列部署觸發（s39→notes 共源盲點）→ 獨立列舉對不上
    rogue = f.trig(name='重生2位1命1', effects=[f.eff_ownership([LIFE[2][1]], sp=0, tp=1)])
    res, _, _ = run(f, write_effects=[f.eff_rename([20501], message=RAW),
                                      f.eff_caption(LIFE[1], message=HEAD)],
                    extra_trigs=[rogue])
    assert any('獨立列舉' in m for m in bad(res))


def test_deploy_key_mismatch_flagged(f):
    from analysis.status_check import check_status_caption
    tm, notes = build(f, write_effects=[f.eff_rename([20501], message=RAW),
                                        f.eff_caption(LIFE[1], message=HEAD)])
    (key, tid), = notes['revive_out']['chains']['timer'].items()
    notes['revive_out']['chains']['timer'] = {(2, 1, 1): tid}   # 鍵錯位：實際部署的是職業1命1
    res = check_status_caption(tm, PARAMS, notes)
    assert any('重生' in m for m in bad(res))


def test_missing_life_refs_single_row(f):
    from analysis.status_check import check_status_caption
    tm, notes = build(f, write_effects=[f.eff_rename([20501], message=RAW)])
    notes['revive'] = {}
    res = check_status_caption(tm, PARAMS, notes)
    assert len(res) == 1 and not res[0][0] and 'life_refs' in res[0][1]


def test_missing_mount_refs_single_row(f):
    from analysis.status_check import check_status_caption
    tm, notes = build(f, write_effects=[f.eff_rename([20501], message=RAW)])
    params = {'status_caption': PARAMS['status_caption'], 'revive': {}}
    res = check_status_caption(tm, params, notes)
    assert len(res) == 1 and not res[0][0] and '覆蓋不齊' in res[0][1]

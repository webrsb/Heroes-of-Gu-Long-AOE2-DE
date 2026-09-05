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


def test_load_rejects_incomplete_boards():
    from steps.s51_status_caption import load_status_caption
    with pytest.raises(BuildError):
        load_status_caption({'boards': {20501: 1}, 'texts': TEXTS})


def test_load_rejects_duplicate_find():
    from steps.s51_status_caption import load_status_caption
    with pytest.raises(BuildError):
        load_status_caption({'boards': BOARDS,
                             'texts': TEXTS + [{'find': POISON_RAW, 'to': 'X'}]})


def test_load_maps_null_to_clear():
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
    with pytest.raises(BuildError, match='不一致'):
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


def test_load_rejects_missing_to_key():
    from steps.s51_status_caption import load_status_caption
    with pytest.raises(BuildError, match='缺 find/to 欄'):
        load_status_caption({'boards': BOARDS, 'texts': [{'find': POISON_RAW}]})


def test_load_rejects_empty_to():
    from steps.s51_status_caption import load_status_caption
    with pytest.raises(BuildError, match='空字串'):
        load_status_caption({'boards': BOARDS, 'texts': [{'find': POISON_RAW, 'to': ' '}]})


def test_load_rejects_unsupported_caption_chars():
    from steps.s51_status_caption import load_status_caption
    with pytest.raises(BuildError, match='不支援字元'):
        load_status_caption({'boards': BOARDS,
                             'texts': [{'find': POISON_RAW, 'to': '中毒％'}]})


def test_load_rejects_empty_texts():
    from steps.s51_status_caption import load_status_caption
    with pytest.raises(BuildError, match='空表'):
        load_status_caption({'boards': BOARDS, 'texts': []})


def test_derive_condition_without_hero_ref_raises(f):
    from steps.s51_status_caption import derive_boards
    trigs = poison_trigs(f)
    trigs[0].conditions = []                     # 「1毒」失去本體 ref 條件
    with pytest.raises(BuildError, match='未引用職業1本體'):
        derive_boards(f.tm(trigs), LIFE, set(BOARDS))


def test_derive_two_writers_same_name_raises(f):
    from steps.s51_status_caption import derive_boards
    dup = f.trig(name='6毒', conds=[f.cond_bring_obj(777, LIFE[6][0])],
                 effects=[f.eff_rename([20506], message=POISON_RAW)])
    tm = f.tm(poison_trigs(f) + [dup])
    with pytest.raises(BuildError, match=r'T\d+\(牌'):
        derive_boards(tm, LIFE, set(BOARDS))


def test_apply_missing_life_refs_raises(f):
    from steps.s51_status_caption import StatusCaptionStep
    def drop(notes):
        notes['revive'] = {}
        return notes
    ctx, _ = make_ctx(f, notes_patch=drop)
    with pytest.raises(BuildError, match='life_refs'):
        StatusCaptionStep().apply(ctx)


def test_caption_appended_on_life_refs(f):
    from steps.s51_status_caption import StatusCaptionStep
    ctx, tm = make_ctx(f)
    StatusCaptionStep().apply(ctx)
    t1 = next(t for t in tm.triggers if t.name == '1毒')
    calls = caption_calls(t1)
    assert len(calls) == 1
    assert calls[0]['message'] == POISON_HEAD
    assert calls[0]['selected_object_ids'] == LIFE[1]          # 毒條件不含 mount → 不加掛
    assert calls[0]['source_player'] == -1


def test_clear_includes_mount_ref(f):
    from steps.s51_status_caption import StatusCaptionStep, CLEAR
    cure = f.trig(name='1毒4', effects=[f.eff_rename([20501], message='正常　狀態')])
    ctx, _ = make_ctx(f, extra_trigs=[cure])
    StatusCaptionStep().apply(ctx)
    calls = caption_calls(cure)
    assert len(calls) == 1
    assert calls[0]['message'] == CLEAR
    assert calls[0]['selected_object_ids'] == LIFE[1] + [MOUNT[1]]


def test_mount_setter_includes_mount_ref(f):
    from steps.s51_status_caption import StatusCaptionStep
    m3 = f.trig(name='3毒3', conds=[f.cond_bring_obj(777, MOUNT[3])],
                effects=[f.eff_rename([20504], message=POISON_RAW)])
    ctx, _ = make_ctx(f, extra_trigs=[m3])
    StatusCaptionStep().apply(ctx)
    calls = caption_calls(m3)
    assert len(calls) == 1
    assert calls[0]['selected_object_ids'] == LIFE[3] + [MOUNT[3]]
    assert calls[0]['source_player'] == -1


def test_unknown_text_raises_with_text_listed(f):
    from steps.s51_status_caption import StatusCaptionStep
    odd = f.trig(name='怪字', effects=[f.eff_rename([20502], message='不明狀態')])
    ctx, _ = make_ctx(f, extra_trigs=[odd])
    with pytest.raises(BuildError, match='不明狀態'):
        StatusCaptionStep().apply(ctx)


def test_mixed_sel_raises(f):
    from steps.s51_status_caption import StatusCaptionStep
    bad = f.trig(name='混搭', effects=[f.eff_rename([20501, 999], message=POISON_RAW)])
    ctx, _ = make_ctx(f, extra_trigs=[bad])
    with pytest.raises(BuildError, match='混搭'):
        StatusCaptionStep().apply(ctx)


def test_crlf_and_fullwidth_strip(f):
    from steps.s51_status_caption import StatusCaptionStep, CLEAR
    crlf = f.trig(name='2頭暈', effects=[f.eff_rename([20502], message='正常　狀態\r\n')])
    ctx, _ = make_ctx(f, extra_trigs=[crlf])
    StatusCaptionStep().apply(ctx)
    assert caption_calls(crlf)[0]['message'] == CLEAR


def test_derive_duplicate_board_claim_raises(f):
    # 覆審備忘：單射分支自身的測試——「2毒」也寫牌 B_OF[1]，走「同時被職業」中止
    from steps.s51_status_caption import derive_boards
    trigs = poison_trigs(f)
    trigs[1].effects = [f.eff_rename([B_OF[1]], message=POISON_RAW)]
    with pytest.raises(BuildError, match='同時被職業'):
        derive_boards(f.tm(trigs), LIFE, set(BOARDS))


def test_two_writes_same_trigger_keep_order(f):
    # 順序契約：同觸發先設後清 → caption 依效果序附掛，淨結果鏡射牌面最終態
    from steps.s51_status_caption import StatusCaptionStep, CLEAR
    both = f.trig(name='設後清', effects=[f.eff_rename([20501], message=POISON_RAW),
                                       f.eff_rename([20501], message='正常　狀態')])
    ctx, _ = make_ctx(f, extra_trigs=[both])
    StatusCaptionStep().apply(ctx)
    calls = caption_calls(both)
    assert [c['message'] for c in calls] == [POISON_HEAD, CLEAR]
    assert calls[1]['selected_object_ids'] == LIFE[1] + [MOUNT[1]]


def test_ghost_write_raises(f):
    # 反向哨兵：非牌 sel 卻寫裁決表文字＝掃描盲點，中止不默默漏
    from steps.s51_status_caption import StatusCaptionStep
    ghost = f.trig(name='盲點', effects=[f.eff_rename([999], message=POISON_RAW)])
    ctx, _ = make_ctx(f, extra_trigs=[ghost])
    with pytest.raises(BuildError, match='掃描盲點'):
        StatusCaptionStep().apply(ctx)


def test_scan_problems_reported_together(f):
    # 混搭與表外同時存在 → 一次掃完統一報，兩者都在訊息裡
    from steps.s51_status_caption import StatusCaptionStep
    bad = f.trig(name='混搭', effects=[f.eff_rename([20501, 999], message=POISON_RAW)])
    odd = f.trig(name='怪字', effects=[f.eff_rename([20502], message='不明狀態')])
    ctx, _ = make_ctx(f, extra_trigs=[bad, odd])
    with pytest.raises(BuildError) as ei:
        StatusCaptionStep().apply(ctx)
    assert '混搭' in str(ei.value) and '不明狀態' in str(ei.value)


def test_unknown_texts_aggregated_and_counted(f):
    from steps.s51_status_caption import StatusCaptionStep
    odd1 = f.trig(name='怪字1', effects=[f.eff_rename([20501], message='不明甲')])
    odd2 = f.trig(name='怪字2', effects=[f.eff_rename([20502], message='不明乙')])
    odd3 = f.trig(name='怪字3', effects=[f.eff_rename([20503], message='不明甲')])   # 重複只記首見
    ctx, _ = make_ctx(f, extra_trigs=[odd1, odd2, odd3])
    with pytest.raises(BuildError) as ei:
        StatusCaptionStep().apply(ctx)
    msg = str(ei.value)
    assert '2 種' in msg and '怪字1' in msg and '怪字3' not in msg


def test_mount_refs_incomplete_raises(f):
    from steps.s51_status_caption import StatusCaptionStep
    ctx, _ = make_ctx(f)
    ctx.spec.params['revive']['mount_refs'] = {1: 901}
    with pytest.raises(BuildError, match='覆蓋不齊'):
        StatusCaptionStep().apply(ctx)


def test_hooks_append_clear(f):
    from steps.s51_status_caption import StatusCaptionStep, CLEAR
    ctx, tm = make_ctx(f)
    StatusCaptionStep().apply(ctx)
    tmr = next(t for t in tm.triggers if t.name == '重生1位1命1')
    mcp = next(t for t in tm.triggers if t.name == '1馬3◇命1')
    tc, mc = caption_calls(tmr), caption_calls(mcp)
    assert tc[0]['message'] == CLEAR and tc[0]['selected_object_ids'] == [LIFE[1][1]]
    assert mc[0]['message'] == CLEAR and mc[0]['selected_object_ids'] == [MOUNT[1]]


def test_missing_mount_copies_raises(f):
    from steps.s51_status_caption import StatusCaptionStep
    def drop(notes):
        del notes['revive_out']['mount_copies']
        return notes
    ctx, _ = make_ctx(f, notes_patch=drop)
    with pytest.raises(BuildError, match='mount_copies'):
        StatusCaptionStep().apply(ctx)


def test_timer_without_deploy_effect_raises(f):
    from steps.s51_status_caption import StatusCaptionStep
    ctx, tm = make_ctx(f)
    tmr = next(t for t in tm.triggers if t.name == '重生1位1命1')
    tmr.effects = []                       # 抽掉部署效果
    with pytest.raises(BuildError, match='部署'):
        StatusCaptionStep().apply(ctx)


def test_non_ref_keyed_writer_reported(f):
    # 零條件寫入器（醉酒 X酒3 型）與純 TIMER 寫入器（神弓 6刀3 型）都要列報告
    from steps.s51_status_caption import StatusCaptionStep
    child = f.trig(name='1酒3', effects=[f.eff_rename([20501], message=POISON_RAW)])
    parent = f.trig(name='1酒2', effects=[f.eff_activate(child.trigger_id)])
    bow = f.trig(name='6刀3', conds=[f.cond_timer(7)],
                 effects=[f.eff_rename([20506], message=POISON_RAW)])
    ctx, _ = make_ctx(f, extra_trigs=[child, parent, bow])
    changes = StatusCaptionStep().apply(ctx)
    r1 = [c for c in changes if c.kind == 'report' and '1酒3' in c.target]
    r2 = [c for c in changes if c.kind == 'report' and '6刀3' in c.target]
    assert len(r1) == 1 and '1酒2' in r1[0].new
    assert len(r2) == 1 and '無' in r2[0].new


def test_clear_writer_not_reported(f):
    # 清除類（正常）不列報告——455 筆會淹掉真正的缺口候選
    from steps.s51_status_caption import StatusCaptionStep
    cure = f.trig(name='1毒4', effects=[f.eff_rename([20501], message='正常　狀態')])
    ctx, _ = make_ctx(f, extra_trigs=[cure])
    changes = StatusCaptionStep().apply(ctx)
    assert not [c for c in changes if c.kind == 'report' and '1毒4' in c.target]


def test_noop_without_params(f):
    from steps.s51_status_caption import StatusCaptionStep
    ctx = NS(base=NS(trigger_manager=f.tm([])), spec=NS(params={}), notes={})
    assert StatusCaptionStep().apply(ctx) == []

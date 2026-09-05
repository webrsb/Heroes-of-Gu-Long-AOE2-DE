# -*- coding: utf-8 -*-
"""s91 結構不變量步驟：違規即 BuildError、報告項不擋建置。"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pytest
from types import SimpleNamespace as NS
from steps.s91_invariants import STEP
from steps.base import BuildError


def _ctx(f, trigs, entries, allow=None):
    params = {'trigger_fixes': entries}
    if allow is not None:
        params['invariant_allow'] = {'block_order': allow}
    return NS(base=NS(trigger_manager=f.tm(trigs)), spec=NS(params=params), notes={})


def test_passes_and_reports(f):
    trigs = [f.trig(name=f'{s}船暈東') for s in range(1, 7)]
    entries = [{'kind': 'trigger_add', 'name': f'{s}船暈東', 'key': 'class'} for s in range(1, 7)]
    # 名稱含「船」但沒有渡船全套 → 特徵斷言會失敗，故此處用不含「船」的名字測純結構路徑
    trigs = [f.trig(name=f'{s}級西') for s in range(1, 6)]
    entries = [{'kind': 'trigger_add', 'name': f'{s}級西', 'key': 'class'} for s in range(1, 6)]
    changes = STEP.apply(_ctx(f, trigs, entries))
    assert changes[0].new.startswith('K/E/O/G 0 違規')
    reports = [c for c in changes if c.kind == 'report']
    assert len(reports) == 1 and '5/6' in reports[0].new          # 座位覆蓋不齊＝報告不擋


def test_key_contract_violation_aborts(f):
    t = f.trig(name='3血東')
    entries = [{'kind': 'trigger_add', 'name': '3血東', 'key': 'seat'}]
    with pytest.raises(BuildError) as ei:
        STEP.apply(_ctx(f, [t], entries))
    assert '實得 0' in str(ei.value) and 'cross' in str(ei.value)


def test_block_order_violation_aborts_and_allowlist_works(f):
    """閘門只守本次施工（spec 新增）的觸發；基底既有形狀降級為報告。"""
    fee = f.trig(name='費')
    blk = f.trig(name='封', effects=[f.eff_deactivate(fee.trigger_id)])
    src = f.trig(name='源', effects=[f.eff_activate(fee.trigger_id), f.eff_activate(blk.trigger_id)])
    mine = [{'kind': 'trigger_add', 'name': '封', 'key': 'class'}]
    with pytest.raises(BuildError):
        STEP.apply(_ctx(f, [fee, blk, src], mine))
    changes = STEP.apply(_ctx(f, [fee, blk, src], mine,
                              allow=[[blk.trigger_id, fee.trigger_id]]))
    assert changes[0].kind == 'audit'
    # 非本次施工的同型形狀：不擋建置，但要出現在報告裡
    changes = STEP.apply(_ctx(f, [fee, blk, src], []))
    assert any(c.kind == 'report' and '攔不住' in c.new for c in changes)


def test_s91_mob_balance_feature_gate(f):
    """params.mob_balance 存在時，s91 須跑 check_mob_balance 並把違規升為 BuildError。"""
    t = f.trig(name='民團', tid=0, effects=[
        f._eff(11, source_player=7, object_list_unit_id=74, location_x=1, location_y=1)])
    ctx = _ctx(f, [t], [])
    # 無 27/28 效果 → 實值 60+0 ≠ 70 → 違規
    ctx.spec.params['mob_balance'] = [dict(
        tid=0, name='民團', const=74, lv=1, kind='m', itv=2.0,
        base_hp=60, base_atk=17, hp=70, atk=17)]
    with pytest.raises(BuildError) as ei:
        STEP.apply(ctx)
    assert '≠' in str(ei.value)

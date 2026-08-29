import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pytest
from types import SimpleNamespace as NS
from steps.s10_transplant import plan_cross_refs
from steps.base import BuildError
from analysis.pairing import PairTable
from AoE2ScenarioParser.datasets.effects import EffectId

def _t(tid, act=()):
    return NS(trigger_id=tid, name=f'T{tid}', conditions=[],
              effects=[NS(effect_type=int(EffectId.ACTIVATE_TRIGGER), trigger_id=x) for x in act])

def test_internal_refs_not_planned():
    plan = plan_cross_refs([_t(0, act=[1]), _t(1)], {0, 1}, PairTable(), '群')
    assert plan == []

def test_cross_ref_mapped():
    pt = PairTable(a2b={99: 42})
    plan = plan_cross_refs([_t(0, act=[99])], {0}, pt, '群')
    assert plan == [(0, 0, 42)]     # (第0個copy, 第0個效果, 回填 42)

def test_cross_ref_unmapped_raises():
    with pytest.raises(BuildError) as e:
        plan_cross_refs([_t(0, act=[99])], {0}, PairTable(), '幫眾')
    assert '幫眾' in str(e.value) and '99' in str(e.value)

@pytest.mark.slow
def test_s10_with_empty_spec_is_noop():
    from core import scenario_io
    from core.specfile import MergeSpec
    from steps.s10_transplant import STEP
    from steps.base import BuildContext
    base = scenario_io.load(scenario_io.ORIGIN_BASE)
    src = scenario_io.load(scenario_io.ORIGIN_SOURCE)
    n = len(base.trigger_manager.triggers)
    ctx = BuildContext(base, src, MergeSpec([], [], {}), None, {})
    assert STEP.apply(ctx) == []
    assert len(base.trigger_manager.triggers) == n
    assert ctx.pairing is not None   # 配對表已建，供後續 step

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pytest
from types import SimpleNamespace as NS
from steps.s30_attackfix import restore, needs_fix, ADD, SUB
from AoE2ScenarioParser.datasets.effects import EffectId

# restore() 語意移植自 src/新負血劍譜/fix_attack.py（ZZ_test02d 實測驗證）：
# 兩層還原 —— 撤銷 DE ×256 切分得 M，再把 M 按 int16 解讀得作者語意值 S。

def test_restore_positive_small_untouched():
    assert restore(100) is None          # cls=0 且正值：DE 已正確處理
    assert restore(30000) is None

def test_restore_two_layer_known_values():
    assert restore(16646156) == (500, SUB)    # cls254,amt12 → M=65036 → int16 −500
    assert restore(16384000) == (1536, SUB)   # cls250,amt0  → M=64000 → int16 −1536
    assert restore(65636) == (356, ADD)       # cls1,amt100  → M=356

def test_restore_negative_raw():
    assert restore(-100) == (100, SUB)

def test_needs_fix_only_attack_effects():
    def e(q, et=int(EffectId.CHANGE_OBJECT_ATTACK)):
        return NS(effect_type=et, quantity=q)
    assert needs_fix(e(16646156))
    assert not needs_fix(e(100))
    assert not needs_fix(e(16646156, et=1))
    assert not needs_fix(e(None))

@pytest.mark.slow
def test_s30_fixes_base_and_leaves_none():
    from core import scenario_io
    from core.specfile import MergeSpec
    from steps.s30_attackfix import STEP
    from steps.base import BuildContext
    base = scenario_io.load(scenario_io.ORIGIN_BASE)
    ctx = BuildContext(base, None, MergeSpec([], [], {}), None, {})
    changes = STEP.apply(ctx)
    print('修復筆數:', len(changes))
    remaining = [e for t in base.trigger_manager.triggers for e in t.effects if needs_fix(e)]
    assert remaining == []
    assert len(changes) >= 481    # |值|>=65536 的就有 481，兩層規則只會更多

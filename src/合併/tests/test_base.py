import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from steps.base import Step, BuildContext, BuildError
from core.change import Change

class DummyStep(Step):
    id = 's99'
    title = '假步驟'
    intro = '測試用'
    def apply(self, ctx):
        ctx.notes['ran'] = True
        return [Change(self.id, 'param', 'x', '—', '1', '2', 'test')]

def test_step_apply_and_notes():
    ctx = BuildContext(base=None, source=None, spec=None, pairing=None, notes={})
    step = DummyStep()
    changes = step.apply(ctx)
    assert ctx.notes['ran'] and changes[0].step == 's99'
    assert step.test_guide(changes) is None  # 基底預設免測

def test_builderror_is_exception():
    try:
        raise BuildError('缺裁決：群組 X 的物件 ref 123 在基底不存在')
    except BuildError as e:
        assert '缺裁決' in str(e)

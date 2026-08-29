import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pytest
from build import run_pipeline, filter_until
from steps.base import Step, BuildContext, BuildError
from core.change import Change

class Ok(Step):
    id = 's10'; title = 'ok'; intro = 'i'
    def apply(self, ctx): return [Change('s10', 'param', 'x', '—', '', '', 'r')]
    def test_guide(self, changes): return '怎麼測：x'

class Boom(Step):
    id = 's20'; title = 'boom'; intro = 'i'
    def apply(self, ctx): raise BuildError('缺裁決：y')

def test_pipeline_collects_results_and_writes_logs(tmp_path):
    ctx = BuildContext(None, None, None, None, {})
    results = run_pipeline(ctx, [Ok()], tmp_path)
    assert results[0].guide == '怎麼測：x'
    assert (tmp_path / '10_ok.tsv').exists() and (tmp_path / '10_ok.md').exists()

def test_builderror_aborts(tmp_path):
    ctx = BuildContext(None, None, None, None, {})
    with pytest.raises(BuildError):
        run_pipeline(ctx, [Ok(), Boom()], tmp_path)

def test_filter_until():
    steps = [Ok(), Boom()]
    assert [s.id for s in filter_until(steps, 's10')] == ['s10']
    assert [s.id for s in filter_until(steps, None)] == ['s10', 's20']

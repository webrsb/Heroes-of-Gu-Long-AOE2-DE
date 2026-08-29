import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pytest
from core import scenario_io

def test_paths_exist():
    assert scenario_io.ORIGIN_BASE.exists()
    assert scenario_io.ORIGIN_SOURCE.exists()

@pytest.mark.slow
def test_roundtrip_preserves_trigger_count(tmp_path):
    s = scenario_io.load(scenario_io.ORIGIN_BASE)
    n = len(s.trigger_manager.triggers)
    out = tmp_path / 'rt.aoe2scenario'
    scenario_io.write_out(s, out)
    s2 = scenario_io.load(out)
    assert len(s2.trigger_manager.triggers) == n == 5599
    assert s2.option_manager.legacy_execution_order is True

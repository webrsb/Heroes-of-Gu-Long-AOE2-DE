import sys, os
from pathlib import Path
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


def test_game_scenario_dir_prefers_env_var(tmp_path, monkeypatch):
    d = tmp_path / 'scenario'; d.mkdir()
    monkeypatch.setenv('AOE2_SCENARIO_DIR', str(d))
    assert scenario_io.game_scenario_dir() == d


def test_game_scenario_dir_expands_tilde_and_skips_missing(tmp_path, monkeypatch):
    """候選依序取第一個存在的：另一台機器的碟符要跳過，`~` 要展開。
    連環境變數指到不存在的目錄也一樣跳過——否則兩台機器只能各自改常數。"""
    monkeypatch.setenv('AOE2_SCENARIO_DIR', str(tmp_path / '也不存在'))
    monkeypatch.setattr(scenario_io, 'GAME_SCENARIO_DIRS',
                        ('Q:/沒有這台碟', str(tmp_path / '不存在'), '~'))
    assert scenario_io.game_scenario_dir() == Path('~').expanduser()


def test_game_scenario_dir_finds_the_real_one_on_this_machine():
    """回歸：Windows 與 macOS（Feral 移植的 VFS 目錄）兩條候選至少要命中一條。"""
    assert scenario_io.game_scenario_dir().is_dir()


def test_deploy_raises_instead_of_silently_missing(monkeypatch, tmp_path):
    """找不到遊戲目錄要中止——不能複製到不存在的路徑後回報「已部署」。"""
    monkeypatch.delenv('AOE2_SCENARIO_DIR', raising=False)
    monkeypatch.setattr(scenario_io, 'GAME_SCENARIO_DIRS', (str(tmp_path / '不存在'),))
    src = tmp_path / 'x.aoe2scenario'; src.write_bytes(b'x')
    with pytest.raises(FileNotFoundError, match='找不到遊戲劇情資料夾'):
        scenario_io.deploy(src)

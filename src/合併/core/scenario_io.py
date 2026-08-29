# -*- coding: utf-8 -*-
"""origin 載入與唯一寫檔點。任何 step 不得自行 write_to_file。"""
import shutil
from pathlib import Path
from AoE2ScenarioParser.scenarios.aoe2_de_scenario import AoE2DEScenario

REPO = Path(__file__).resolve().parents[3]   # F:/aoe2de
ORIGIN_BASE = REPO / 'src/origin/古龍921_無法無天.aoe2scenario'
ORIGIN_SOURCE = REPO / 'src/origin/古龍921_新負血劍譜5.aoe2scenario'
GAME_SCENARIO_DIR = Path('C:/Users/Ricky/Games/Age of Empires 2 DE'
                         '/76561198023399153/resources/_common/scenario')

def load(path) -> AoE2DEScenario:
    return AoE2DEScenario.from_file(str(path))

def write_out(scenario, out_path: Path) -> None:
    out_path = Path(out_path); out_path.parent.mkdir(parents=True, exist_ok=True)
    scenario.option_manager.legacy_execution_order = True  # 鐵律：防 DE 重排觸發
    scenario.write_to_file(str(out_path))

def deploy(out_path: Path) -> Path:
    dst = GAME_SCENARIO_DIR / Path(out_path).name
    shutil.copy2(out_path, dst)
    return dst

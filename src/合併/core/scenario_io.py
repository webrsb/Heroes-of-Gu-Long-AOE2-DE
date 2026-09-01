# -*- coding: utf-8 -*-
"""origin 載入與唯一寫檔點。任何 step 不得自行 write_to_file。"""
import os
import shutil
from pathlib import Path
from AoE2ScenarioParser.scenarios.aoe2_de_scenario import AoE2DEScenario

REPO = Path(__file__).resolve().parents[3]   # repo 根（core → 合併 → src → 根）
ORIGIN_BASE = REPO / 'src/origin/古龍921_無法無天.aoe2scenario'
ORIGIN_SOURCE = REPO / 'src/origin/古龍921_新負血劍譜5.aoe2scenario'

# 遊戲的劇情資料夾（丟進去，遊戲內 單人→劇情 就看得到）。同一份程式碼要能在兩台機器跑，
# 所以列候選、依序取第一個存在的；順序即優先序，環境變數 AOE2_SCENARIO_DIR 蓋過全部。
# macOS 是 Feral Interactive 的原生移植，玩家資料在它的 VFS 目錄下，不是 ~/Games。
GAME_SCENARIO_DIRS = (
    'C:/Users/Ricky/Games/Age of Empires 2 DE'
    '/76561198023399153/resources/_common/scenario',
    '~/Library/Application Support/Feral Interactive/Age Of Empires II'
    '/VFS/User/Games/Age of Empires 2 DE'
    '/76561198023399153/resources/_common/scenario',
)


def _scenario_dir_candidates():
    env = os.environ.get('AOE2_SCENARIO_DIR')
    return ((env,) if env else ()) + GAME_SCENARIO_DIRS


def game_scenario_dir() -> Path:
    """→ 這台機器的遊戲劇情資料夾。找不到就 raise——寧可中止，也不要把檔案
    複製到一個不存在的路徑後回報「已部署」。"""
    for cand in _scenario_dir_candidates():
        p = Path(cand).expanduser()
        if p.is_dir():
            return p
    tried = '\n  '.join(str(Path(c).expanduser()) for c in _scenario_dir_candidates())
    raise FileNotFoundError(
        f'找不到遊戲劇情資料夾。試過：\n  {tried}\n'
        '用環境變數 AOE2_SCENARIO_DIR 指定，或補進 GAME_SCENARIO_DIRS。')

def load(path) -> AoE2DEScenario:
    return AoE2DEScenario.from_file(str(path))

def write_out(scenario, out_path: Path) -> None:
    out_path = Path(out_path); out_path.parent.mkdir(parents=True, exist_ok=True)
    scenario.option_manager.legacy_execution_order = True  # 鐵律：防 DE 重排觸發
    scenario.write_to_file(str(out_path))

def deploy(out_path: Path) -> Path:
    dst = game_scenario_dir() / Path(out_path).name
    shutil.copy2(out_path, dst)
    return dst

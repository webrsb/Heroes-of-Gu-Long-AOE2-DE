# -*- coding: utf-8 -*-
"""單一入口建置流程。用法：
    python build.py                 # 全跑，出 out/古龍921_合併.aoe2scenario
    python build.py --until s30    # 跑到 s30，出 out/古龍921_合併_until_s30.aoe2scenario
    python build.py --deploy       # 建置後複製到遊戲劇情資料夾
    python build.py --report       # 產盤點報告（不建置）
"""
import argparse, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.stdout.reconfigure(encoding='utf-8')

from core.logging_out import write_step_logs
from core.testguide import StepResult, render_guide
from core.specfile import load_spec
from core import scenario_io
from steps import get_steps
from steps.base import BuildContext, BuildError

HERE = Path(__file__).resolve().parent
LOGS = HERE / 'logs'
OUT = HERE / 'out'

def filter_until(steps, until):
    return [s for s in steps if until is None or s.id <= until]

def run_pipeline(ctx, steps, logs_dir):
    results = []
    for step in steps:
        changes = step.apply(ctx)          # BuildError 直接中止
        ctx.notes.setdefault('all_changes', []).extend(changes)
        write_step_logs(step.id, step.title, step.intro, changes, logs_dir)
        results.append(StepResult(step.id, step.title, changes, step.test_guide(changes)))
        print(f'{step.id} {step.title}: {len(changes)} 筆異動')
    return results

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--until')
    ap.add_argument('--deploy', action='store_true')
    ap.add_argument('--report', action='store_true')
    a = ap.parse_args()
    if a.report:
        from analysis.inventory import write_report
        return write_report()
    spec = load_spec(HERE / 'merge_spec.yaml')
    base = scenario_io.load(scenario_io.ORIGIN_BASE)
    source = scenario_io.load(scenario_io.ORIGIN_SOURCE)
    ctx = BuildContext(base=base, source=source, spec=spec, pairing=None, notes={})
    from steps.s90_audit import collect_dangling
    ctx.notes['initial_trigger_count'] = len(base.trigger_manager.triggers)
    ctx.notes['baseline_dangling'] = collect_dangling(base)
    steps = filter_until(get_steps(), a.until)
    try:
        results = run_pipeline(ctx, steps, LOGS)
    except BuildError as e:
        print(f'建置中止：{e}'); return 1
    suffix = f'_until_{a.until}' if a.until else ''
    out_path = OUT / f'古龍921_合併{suffix}.aoe2scenario'
    scenario_io.write_out(ctx.base, out_path)
    (LOGS / '測試指引.md').write_text(render_guide(results), encoding='utf-8',
                                   newline='\n')
    print(f'產出：{out_path}')
    if a.deploy:
        print(f'部署：{scenario_io.deploy(out_path)}')
    print('建議 commit：git add src/合併/logs && git commit -m "build(合併): <本輪摘要>"')
    return 0

if __name__ == '__main__':
    sys.exit(main())

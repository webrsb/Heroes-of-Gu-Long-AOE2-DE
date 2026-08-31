# -*- coding: utf-8 -*-
"""渡船特徵斷言 CLI（唯讀）：對產物跑 analysis/ferry_check.py 的全部斷言。
用法（在 src/合併 下）：python tools/verify_ferry.py [out/古龍921_合併.aoe2scenario]"""
import io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, __file__.rsplit('tools', 1)[0])
from core.scenario_io import load
from analysis.ferry_check import check_ferry


def main(path):
    results = check_ferry(load(path).trigger_manager)
    fails = [m for ok, m in results if not ok]
    for ok, m in results:
        print(('OK   ' if ok else 'FAIL ') + m)
    tail = '全部通過' if not fails else f'{len(fails)} 項 FAIL'
    print(f'\n{len(results)} 項；{tail}')
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else 'out/古龍921_合併.aoe2scenario'))

# -*- coding: utf-8 -*-
"""
修復 Change Object Attack 被 DE 轉檔切壞的效果。

依據 古龍921_DE遷移記錄.md §3.3c / §3.3d / §3.3e（全部經實際傷害量測驗證）：

    DE 轉檔把 AoC 的單純攻擊力數值當成「護甲類型打包值」在 ×256 邊界重新切分，
    導致任何 |原值| >= 256 的效果在 DE 完全無作用。

    還原：V = (|DE現值| >> 16) * 256 + (|DE現值| & 0xFFFF)
    正值 -> class=0, amount=V,  operation=ADD
    負值 -> class=0, amount=V,  operation=SUBTRACT

    class=0 已實測等同「近戰攻擊 +N」（ZZ_test02d E2/E3 傷害相同），
    且無 255 上限（E5/E6 帶 30000 一擊秒殺）。

本腳本**不覆寫原檔**，另存為 _attackfix 後綴。
用法:
    python fix_attack.py            # 產生修復檔
    python fix_attack.py --dry-run  # 只列出將要做的變更
"""
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

from AoE2ScenarioParser.scenarios.aoe2_de_scenario import AoE2DEScenario
from AoE2ScenarioParser.datasets.effects import EffectId
from AoE2ScenarioParser.datasets.trigger_lists import Operation

SRC = r"F:\aoe2de\src\- 古龍 ９２１ 新負血劍譜５ -utf8.aoe2scenario"
DST = r"F:\aoe2de\src\- 古龍 ９２１ 新負血劍譜５ -utf8_attackfix.aoe2scenario"
REPORT = r"F:\aoe2de\attack_fix_report.tsv"

ADD = int(Operation.ADD)
SUB = int(Operation.SUBTRACT)
DRY = '--dry-run' in sys.argv


def as_int16(v):
    v &= 0xFFFF
    return v - 65536 if v >= 32768 else v


def restore(de_raw):
    """DE 現值 -> (原值絕對量, operation)。回傳 None 表示不需修改。

    兩層還原：
      1. 撤銷 DE 轉檔的 ×256 重新切分   -> 取得 AoC 存檔值 M
      2. 把 M 當 int16 解讀              -> 取得作者真正的語意值 S
         （作者也用 int16 回繞表達負值，例如 55536 = −10000、64000 = −1536）
    """
    sign = -1 if de_raw < 0 else 1
    v = abs(de_raw)
    cls = v >> 16
    amt = v & 0xFFFF
    if sign > 0 and cls == 0:
        return None                       # 原值 < 256，DE 已正確處理
    M = cls * 256 + amt
    S = as_int16(M) if sign > 0 else as_int16(-M)
    if S == 0:
        return None
    return abs(S), (ADD if S > 0 else SUB)


def main():
    sc = AoE2DEScenario.from_file(SRC)
    tm = sc.trigger_manager

    rows = []
    skipped = 0
    for t in tm.triggers:
        for i, e in enumerate(t.effects):
            if e.effect_type != EffectId.CHANGE_OBJECT_ATTACK:
                continue
            raw = e.quantity
            if raw is None:
                continue
            r = restore(raw)
            if r is None:
                skipped += 1
                continue
            V, op = r
            rows.append((t.trigger_id, t.name, i, raw,
                         e.armour_attack_class, e.armour_attack_quantity,
                         V, op, e))

    print(f"Change Object Attack 總數: {skipped + len(rows)}")
    print(f"  ✅ 無需修改（class=0，原值 <256）: {skipped}")
    print(f"  🔴 需修復: {len(rows)}")
    n_add = sum(1 for r in rows if r[7] == ADD)
    print(f"       正值 -> ADD:      {n_add}")
    print(f"       負值 -> SUBTRACT: {len(rows) - n_add}")

    # 明細（UTF-8 BOM，方便 Excel 直接開）
    with open(REPORT, 'w', encoding='utf-8-sig') as f:
        f.write("trigger_id\ttrigger_name\teffect_index\tde_raw\t"
                "de_class\tde_amount\trestored_value\tnew_operation\n")
        for tid, tname, i, raw, cls, amt, V, op, _e in rows:
            f.write(f"{tid}\t{tname}\t{i}\t{raw}\t{cls}\t{amt}\t{V}\t"
                    f"{'ADD' if op == ADD else 'SUBTRACT'}\n")
    print(f"\n明細已寫出: {REPORT}")

    print("\n最大的正值加成（ADD）:")
    print(f"  {'觸發器':<24}{'DE現值':>11}{'DE誤讀':>16}{'還原值':>9}")
    for tid, tname, i, raw, cls, amt, V, op, _e in \
            sorted([r for r in rows if r[7] == ADD],
                   key=lambda r: -r[6])[:6]:
        print(f"  [{tid}] {tname[:14]:<18}{raw:>11}"
              f"{'cls%d,+%d' % (cls, amt):>16}{V:>9}")
    print("\n最大的扣除（SUBTRACT）:")
    for tid, tname, i, raw, cls, amt, V, op, _e in \
            sorted([r for r in rows if r[7] == SUB],
                   key=lambda r: -r[6])[:6]:
        print(f"  [{tid}] {tname[:14]:<18}{raw:>11}"
              f"{'cls%d,+%d' % (cls, amt):>16}{V:>9}")

    # 成對檢查：加成與扣除是否數量級相符
    from collections import Counter
    mags = Counter()
    for *_x, V, op, _e in rows:
        mags[(V, 'ADD' if op == ADD else 'SUB')] += 1
    paired = sum(c for (V, k), c in mags.items()
                 if k == 'ADD' and (V, 'SUB') in mags)
    print(f"\n成對檢查：有對應扣除值的加成效果數 = {paired}")

    if DRY:
        print("\n--dry-run：未寫出修復檔")
        return

    # 實際改寫
    for tid, tname, i, raw, cls, amt, V, op, e in rows:
        e.operation = op
        e.armour_attack_class = 0
        e.armour_attack_quantity = V

    sc.write_to_file(DST)
    print(f"\n修復檔已寫出: {DST}")
    print("（原檔未變動）")

    # 讀回驗證
    print("\n讀回驗證：")
    sc2 = AoE2DEScenario.from_file(DST)
    still_bad = 0
    total = 0
    for t in sc2.trigger_manager.triggers:
        for e in t.effects:
            if e.effect_type != EffectId.CHANGE_OBJECT_ATTACK:
                continue
            total += 1
            if e.armour_attack_class not in (0, None):
                still_bad += 1
    print(f"  修復檔的 Change Object Attack 總數: {total}")
    print(f"  class 仍非 0 的: {still_bad}  "
          f"{'✅ 全部已正規化' if still_bad == 0 else '🔴 仍有殘留'}")


if __name__ == '__main__':
    main()

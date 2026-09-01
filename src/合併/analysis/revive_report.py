# -*- coding: utf-8 -*-
"""復活盤點報表產生器（plan T6 Step 4）：對合併產物實跑 build_inventory，
輸出 reports/復活盤點.md——五類數量、死亡連動 54 行分類提案、const_filtered、
馬系統鏈路、X死斷邊清單、cross 清單、總量預估與 30k 熔斷檢查。
用法: python -m analysis.revive_report <scenario> <out_md>"""
import sys, io
from collections import defaultdict
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

HERO_REFS = {1: 0, 2: 1, 3: 2, 4: 502, 5: 7, 6: 45117}
HERO_CONSTS = {1: 845, 2: 432, 3: 752, 4: 428, 5: 1811, 6: 765}
RETIRED = [1805, 1806, 1807, 1808, 1809, 1810, 3821, 3822, 3823, 3824, 3825, 3826]
FUSE = 30000


def main(src, out_md):
    from AoE2ScenarioParser.scenarios.aoe2_de_scenario import AoE2DEScenario
    from analysis.revive_inventory import build_inventory
    scn = AoE2DEScenario.from_file(src)
    tm = scn.trigger_manager
    inv = build_inventory(tm, HERO_REFS, HERO_CONSTS, exclude=RETIRED)
    by_id = {t.trigger_id: t for t in tm.triggers}

    def nm(tid):
        t = by_id[tid]
        return f'T{tid}「{t.name or "(無名)"}」'

    # 啟停邊索引：誰 activate/deactivate 誰
    act_in, deact_in = defaultdict(list), defaultdict(list)
    for t in tm.triggers:
        for e in t.effects:
            et = getattr(e, 'effect_type', None)
            tgt = getattr(e, 'trigger_id', -1)
            if et == 8 and tgt >= 0:
                act_in[tgt].append(t.trigger_id)
            elif et == 9 and tgt >= 0:
                deact_in[tgt].append(t.trigger_id)

    L = ['# 復活接線盤點報表（T6，自動產生）', '',
         f'來源：{src}（觸發 {len(tm.triggers)} 支，退役排除 {len(RETIRED)} 支）', '']

    # ---- 五類數量 ----
    L += ['## 一、五類數量（各職業）', '',
          '| 職業 | family | matrix | shared | death_linked | addressed |', '|---|---|---|---|---|---|']
    for c in range(1, 7):
        L.append(f'| {c} | {len(inv.families.get(c, set()))} | {len(inv.matrix.get(c, set()))} '
                 f'| {len(inv.shared.get(c, set()))} | {len(inv.death_linked.get(c, set()))} '
                 f'| {len(inv.addressed.get(c, set()))} |')
    L += ['', f'全表收集：可追加效果 {len(inv.eff_list_appendable)}、指令型效果 {len(inv.eff_list_command)}、'
          f'條件 ref {len(inv.cond_ref)}、locref {len(inv.locref)}；'
          f'global_init {len(inv.global_init)} 支={sorted(inv.global_init)}；cross {len(inv.cross)} 支', '']

    # ---- 死亡連動分類提案 ----
    L += ['## 二、死亡連動分類提案（§七之二；裁決欄請確認/修改）', '',
          '| tid | 名稱 | 職業 | looping | enabled | 被啟動自 | 被停用自 | 提案 |',
          '|---|---|---|---|---|---|---|---|']
    dl_rows = []
    for c in range(1, 7):
        for tid in sorted(inv.death_linked.get(c, set())):
            t = by_id[tid]
            acts = ','.join(f'T{x}' for x in sorted(set(act_in.get(tid, []))))
            deacts = ','.join(f'T{x}' for x in sorted(set(deact_in.get(tid, []))))
            if t.looping:
                prop = 'b(狀態閘門)'
            elif acts or deacts:
                prop = 'a(事件+旗標閘門)'
            else:
                prop = 'a(事件)'
            dl_rows.append((tid, c))
            L.append(f'| {tid} | {t.name or "(無名)"} | {c} | {t.looping} | {t.enabled} '
                     f'| {acts or "—"} | {deacts or "—"} | {prop} |')
    L.append('')

    # ---- 馬系統 ----
    L += ['## 三、馬系統鏈路（REMOVE 本體與馬網絡，先裁決再接線）', '']
    horse = set()
    for tid, ei, cid, et in inv.eff_list_command:
        if et == 15:
            horse.add(tid)
    for t in tm.triggers:
        if '馬' in (t.name or ''):
            horse.add(t.trigger_id)
    for tid in sorted(horse):
        t = by_id[tid]
        effs = []
        for e in t.effects[:8]:
            et = getattr(e, 'effect_type', None)
            sel = list(getattr(e, 'selected_object_ids', None) or [])
            heroes = [r for r in sel if r in HERO_REFS.values()]
            effs.append(f'e{et}{"!本體" if heroes else ""}'
                        f'{"→T" + str(e.trigger_id) if et in (8, 9) else ""}')
        conds = [f'c{getattr(c, "condition_type", "?")}' for c in t.conditions[:6]]
        L.append(f'- {nm(tid)} loop={t.looping} en={t.enabled} 條件[{" ".join(conds)}] '
                 f'效果[{" ".join(effs)}]')
    L.append('')

    # ---- X死 斷邊 ----
    L += ['## 四、X死退役斷邊清單（指向 12 支退役觸發的啟停效果）', '']
    for tgt in RETIRED:
        srcs = sorted(set(act_in.get(tgt, [])) | set(deact_in.get(tgt, [])))
        if srcs:
            L.append(f'- T{tgt} ← ' + '、'.join(
                f'{nm(s)}({"啟" if tgt in [x for x in [tgt] if s in act_in.get(tgt, [])] else ""}'
                f'{"停" if s in deact_in.get(tgt, []) else ""})' for s in srcs))
    L.append('')

    # ---- const_filtered ----
    L += ['## 五、本體 const 過濾之非家族觸發（逐支裁決）', '']
    for tid, where, cid in sorted(set(inv.const_filtered)):
        t = by_id[tid]
        sps = sorted({getattr(e, 'source_player', -1) for e in t.effects} |
                     {getattr(c, 'source_player', -1) for c in t.conditions})
        L.append(f'- {nm(tid)} [{where}] 職業{cid}(const{HERO_CONSTS[cid]}) '
                 f'loop={t.looping} en={t.enabled} 玩家欄={sps}')
    L.append('')

    # ---- cross ----
    L += ['## 六、跨職業觸發（逐支裁決）', '']
    for tid in sorted(inv.cross):
        L.append(f'- {nm(tid)} en={by_id[tid].enabled} loop={by_id[tid].looping}')
    L.append('')

    # ---- 總量預估 ----
    matrix_total = sum(len(s) for s in inv.matrix.values())
    locref_trigs = len({tid for tid, ei, cid in inv.locref})
    dl_a = sum(1 for tid, c in dl_rows if not by_id[tid].looping)
    L += ['## 七、總量預估與熔斷', '']
    for lives in (3, 10):
        chains = 6 * 6 * (1 + (lives - 1) * 2 + 1)
        est = (len(tm.triggers) + matrix_total * 5 + locref_trigs * (lives - 1)
               + chains + dl_a * 5 + 200)
        verdict = 'OK' if est <= FUSE else f'★超過熔斷 {FUSE}——停線重壓測'
        L.append(f'- lives={lives}: 現有 {len(tm.triggers)} ＋ matrix {matrix_total}×5 '
                 f'＋ locref {locref_trigs}×{lives - 1} ＋ 鏈 {chains} ＋ 連動a型 {dl_a}×5 '
                 f'＋ 啟動器約200 ≈ **{est}** → {verdict}')
    open(out_md, 'w', encoding='utf-8', newline='\n').write('\n'.join(L) + '\n')
    print(f'報表完成: {out_md}（死亡連動 {len(dl_rows)} 行、const過濾 '
          f'{len(set(inv.const_filtered))} 支、cross {len(inv.cross)} 支）')


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])

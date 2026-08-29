# -*- coding: utf-8 -*-
"""盤點報告：圈選前的一次性唯讀分析。build.py --report 的實體。"""
from collections import Counter
from pathlib import Path
from .fingerprint import fingerprint, _COND_FIELDS, _EFFECT_FIELDS
from .pairing import pair_triggers
from .grouping import activation_edges, group_ids, group_label
from .dependency import assess_group, build_unit_index, collect_object_refs

REPORTS = Path(__file__).resolve().parents[1] / 'reports'


def diff_paired(by_id_a, by_id_b, pairing, limit_per_pair=20):
    """method=name 但內容指紋不同的配對 → 逐欄位差異（衝突類型 1 清單）。"""
    rows = []
    for a_id in sorted(pairing.a2b):
        if pairing.method.get(a_id) not in ('name', 'name-dup'):
            continue
        ta, tb = by_id_a[a_id], by_id_b[pairing.a2b[a_id]]
        fa, fb = fingerprint(ta), fingerprint(tb)
        if fa == fb:
            continue
        name = ta.name or f'T{a_id}'
        if len(fa) != len(fb):
            rows.append((name, '條件效果數', str(len(fa)), str(len(fb))))
            continue
        n = 0
        for i, (ra, rb) in enumerate(zip(fa, fb)):
            if ra == rb:
                continue
            fields = _COND_FIELDS if ra[0] == 'c' else _EFFECT_FIELDS
            kind = '條件' if ra[0] == 'c' else '效果'
            for j, f in enumerate(fields):
                if ra[j + 1] != rb[j + 1]:
                    rows.append((name, f'{kind}{i}.{f}', str(ra[j + 1]), str(rb[j + 1])))
                    n += 1
                    if n >= limit_per_pair:
                        break
            if n >= limit_per_pair:
                rows.append((name, '…', '（同觸發其餘差異省略）', ''))
                break
    return rows


def render_report(group_reports, diff_rows, fuzzy_rows, orphans, stats) -> str:
    L = ['# 盤點報告 —— 劍譜5 → 無法無天 合併圈選', '',
         f"劍譜5 觸發 {stats['a_total']}；無法無天觸發 {stats['b_total']}；"
         f"無法無天獨有（不需動作）{stats['unmatched_b']}。", '',
         '圈選方式：在下表「圈選」欄填 auto / patch / skip，我把結果抄進 merge_spec.yaml。', '',
         '## 圈選總表', '',
         '| 群 | 觸發數 | 物件(同/獨有/衝突) | 區域效果 | 判定 | 圈選 |',
         '|---|---|---|---|---|---|']
    for g in group_reports:
        L.append(f'| {g.label} | {len(g.members)} | {g.refs_same}/{len(g.refs_a_only)}'
                 f'/{len(g.refs_collision)} | {g.area_effect_count} | {g.classification} |  |')
    L.append('')
    L.append('## 各群明細')
    for g in group_reports:
        L += ['', f'### {g.label}',
              f'- 成員觸發 id：{sorted(g.members)}',
              f'- 判定：**{g.classification}** —— ' + '；'.join(g.reasons)]
        if g.refs_a_only:
            L.append(f'- 需搬運的獨有物件 ref：{g.refs_a_only}')
        if g.cross_out_edges:
            L.append(f'- 跨群啟動邊（a觸發→基底對應）：{g.cross_out_edges}')
    L += ['', '## 同名不同內容（衝突類型 1，預設以無法無天為準，要改判的告訴我）', '',
          '| 觸發 | 位置.欄位 | 劍譜5 | 無法無天 |', '|---|---|---|---|']
    L += [f'| {n} | {f} | {a} | {b} |' for n, f, a, b in diff_rows]
    L += ['', '## 模糊配對（fuzzy，請人工確認配對正確）', '',
          '| 劍譜5 | 無法無天 |', '|---|---|']
    L += [f'| {a} | {b} |' for a, b in fuzzy_rows]
    L += ['', '## 孤兒物件（劍譜5 獨有且無觸發引用，多為裝飾物）', '',
          '| unit_const | 數量 |', '|---|---|']
    L += [f'| {c} | {n} |' for c, n in sorted(orphans.items())]
    if stats.get('unmatched_b_names'):
        L += ['', '## 附：無法無天獨有觸發（僅供參考，不需動作）', '']
        L += [f'- {x}' for x in stats['unmatched_b_names']]
    return '\n'.join(L) + '\n'


def write_report() -> int:
    from core import scenario_io
    a = scenario_io.load(scenario_io.ORIGIN_SOURCE)   # 劍譜5 = a
    b = scenario_io.load(scenario_io.ORIGIN_BASE)     # 無法無天 = b
    ta, tb = a.trigger_manager.triggers, b.trigger_manager.triggers
    pt = pair_triggers(ta, tb)
    by_id_a = {t.trigger_id: t for t in ta}
    by_id_b = {t.trigger_id: t for t in tb}
    idx_a, idx_b = build_unit_index(a), build_unit_index(b)
    edges = activation_edges(ta)
    groups = group_ids(set(pt.unmatched_a), edges)
    reports = sorted((assess_group(group_label(by_id_a, g), g, by_id_a, idx_a, idx_b, pt)
                      for g in groups), key=lambda r: -len(r.members))
    diff_rows = diff_paired(by_id_a, by_id_b, pt)
    fuzzy_rows = [(by_id_a[i].name, by_id_b[pt.a2b[i]].name)
                  for i, m in sorted(pt.method.items()) if m == 'fuzzy']
    referenced = collect_object_refs(ta)
    orphan_refs = (set(idx_a) - set(idx_b)) - referenced
    orphans = Counter(idx_a[r][1] for r in orphan_refs)
    stats = dict(a_total=len(ta), b_total=len(tb), unmatched_b=len(pt.unmatched_b),
                 unmatched_b_names=[repr(by_id_b[i].name) for i in pt.unmatched_b])
    REPORTS.mkdir(exist_ok=True)
    (REPORTS / '盤點報告.md').write_text(
        render_report(reports, diff_rows, fuzzy_rows, orphans, stats), encoding='utf-8')
    tsv = ['群\t成員id\t判定\t原因']
    tsv += [f'{r.label}\t{sorted(r.members)}\t{r.classification}\t{"；".join(r.reasons)}'
            for r in reports]
    (REPORTS / '盤點明細.tsv').write_text('\n'.join(tsv) + '\n', encoding='utf-8')
    print(f'盤點報告：{REPORTS / "盤點報告.md"}（{len(reports)} 群、'
          f'{len(diff_rows)} 筆同名差異、{len(fuzzy_rows)} 組模糊配對）')
    return 0

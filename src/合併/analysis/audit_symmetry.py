# -*- coding: utf-8 -*-
"""六座位對稱稽核：抓原作 1–6P 複製貼上錯誤（錯家、啟停極性抄反、漏改英雄 ref）。

原作觸發以 6 座位複製（1教頭4～6教頭4、刀3／劍3／…），同組觸發除玩家編號、英雄 ref、
目標觸發外應完全相同。把每座位觸發「正規化」（自己座位→S、自己英雄→HERO、目標觸發→座位無關樣式）
後互比，少數派即嫌疑。三層檢查：
  A. 外座位引用（sp/tp/unit_object/sel 指到別座位）計數多於多數 → HIGH（不看位置）
  B. 每個目標觸發樣式的啟/停極性投票，少數派 → HIGH；多數座位有邊而此座位沒有 → MED（不看位置）
  C. 結構孿生（型別序列相同，啟/停視為同類）的多數座位逐欄比對：sp/tp/uo/sel/type HIGH、數值 MED
     — 效果順序對調（多重集相同）不算；兩邊皆外座位的 sp 不算（A 已涵蓋）
只跑**基底原檔**（無法無天）：合併產物的 ◇位/◇命 變體會把座位語意打亂。
2026-08-30 陽性對照：s37 七條裁決＋2P/3P 教頭4 極性抄反，全數命中。

用法：python -m analysis.audit_symmetry <scenario> [out_md]
"""
import re
import sys
import collections

CLASS = {'刀': 1, '劍': 2, '槍': 3, '棍': 4, '拳': 5, '箭': 6, '暗': 6}
CLASS_CHARS = {1: '刀', 2: '劍', 3: '槍', 4: '棍', 5: '拳', 6: '箭暗'}
NEUTRAL_P = {-1, 0, 7, 8}
ACT, DEACT = 8, 9
SEV = {'type': 'HIGH', 'sp': 'HIGH', 'tp': 'HIGH', 'uo': 'HIGH', 'sel': 'HIGH',
       'qty': 'MED', 'timer': 'MED', 'olu': 'MED', 'attr': 'MED', 'var': 'MED', 'nsel': 'MED',
       'area': 'LOW', 'msg': 'LOW'}
Finding = collections.namedtuple('Finding', 'sev pattern occ seat tid name where field value majority')


def seat_pattern(name):
    """'3教頭4'→(3,'X教頭4')；'2劍3'→(2,'XC3')；'槍1'→(3,'C1')；'首  劍1'→(2,'~首  C1')；其他→(None,None)。"""
    if not name:
        return None, None
    m = re.match(r'^([1-6])(.*)$', name)
    if m:
        seat, rest = int(m.group(1)), m.group(2)
        return seat, 'X' + _cls(rest, seat)
    if name[0] in CLASS:
        seat = CLASS[name[0]]
        return seat, 'C' + _cls(name[1:], seat)
    seats = {CLASS[ch] for ch in name if ch in CLASS}
    if len(seats) == 1:
        seat = seats.pop()
        return seat, '~' + _cls(name, seat)
    m = re.match(r'^(.*[^\d])([1-6])$', name)          # 尾數編號：「觸發事件 3」「草草5」「魂移6」
    if m:
        return int(m.group(2)), '$' + m.group(1) + 'N'
    return None, None


def _cls(s, seat):
    for ch in CLASS_CHARS[seat]:
        s = s.replace(ch, 'C')
    return s


def majority(vals):
    cnt = collections.Counter(repr(v) for v in vals.values())
    top, n = cnt.most_common(1)[0]
    return top, n


def hero_refs(triggers):
    """英雄 ref→座位：T「名」E0–E5 的 selected_object_ids（每位一組）。"""
    hero = {}
    for t in triggers:
        if t.name == '名':
            for i, e in enumerate(t.effects[:6]):
                for r in getattr(e, 'selected_object_ids', None) or []:
                    hero[r] = i + 1
            break
    return hero


def audit(triggers, hero=None):
    """回傳 (findings, stats)。triggers 需有 trigger_id/name/conditions/effects。"""
    hero = hero if hero is not None else hero_refs(triggers)
    by_id = {t.trigger_id: t for t in triggers}
    seat_of = {t.trigger_id: seat_pattern(t.name) for t in triggers}
    groups = collections.defaultdict(lambda: collections.defaultdict(list))
    for t in triggers:
        s, pat = seat_of[t.trigger_id]
        if s:
            groups[pat][s].append(t)

    def np_(p, seat):
        return 'S' if p == seat else (p if p in NEUTRAL_P else f'P{p}!')

    def nref(r, seat):
        h = hero.get(r)
        return 'HERO' if h == seat else (f'HERO{h}!' if h else 'REF')

    def edge(tid, seat):
        t2 = by_id.get(tid)
        if t2 is None:
            return f'T{tid}?', f'T{tid}?'
        s2, pat2 = seat_of[tid]
        rel = (t2.name or f'T{tid}') if s2 is None else (pat2 if s2 == seat else f'{pat2}@P{s2}!')
        return rel, f'T{tid}'

    def g(o, k, d=-1):
        v = getattr(o, k, d)
        return d if v is None else v

    def norm(t, seat):
        cs, es = [], []
        for c in t.conditions:
            uo = g(c, 'unit_object')
            cs.append(dict(type=g(c, 'condition_type'), sp=np_(g(c, 'source_player'), seat),
                           qty=g(c, 'quantity'), timer=g(c, 'timer'), attr=g(c, 'attribute'),
                           olu=g(c, 'object_list'), uo=nref(uo, seat) if uo != -1 else -1,
                           var=g(c, 'variable'),
                           area=(g(c, 'area_x1'), g(c, 'area_y1'), g(c, 'area_x2'), g(c, 'area_y2'))))
        for e in t.effects:
            et = g(e, 'effect_type')
            sel = g(e, 'selected_object_ids', []) or []
            tp = g(e, 'target_player')
            es.append(dict(type=et, sp=np_(g(e, 'source_player'), seat),
                           tp=np_(tp, seat) if tp != -1 else -1,
                           qty=g(e, 'quantity'), olu=g(e, 'object_list_unit_id'),
                           edge=edge(g(e, 'trigger_id'), seat) if et in (ACT, DEACT) else None,
                           pol='ACT' if et == ACT else ('DEACT' if et == DEACT else None),
                           nsel=len(sel), sel=tuple(sorted(set(nref(r, seat) for r in sel))),
                           var=g(e, 'variable'),
                           area=(g(e, 'area_x1'), g(e, 'area_y1'), g(e, 'area_x2'), g(e, 'area_y2')),
                           msg=g(e, 'message', '')))
        return cs, es

    def seat_bound(n):
        return any(d.get('sp') == 'S' or d.get('tp') == 'S' or d.get('uo') == 'HERO'
                   or 'HERO' in d.get('sel', ()) for part in n for d in part)

    def foreign(n):
        out = []
        for tag, part in (('C', n[0]), ('E', n[1])):
            for i, d in enumerate(part):
                for f in ('sp', 'tp', 'uo'):
                    if '!' in str(d.get(f, '')):
                        out.append(f'{tag}#{i}.{f}={d[f]}')
                out += [f'{tag}#{i}.sel={r}' for r in d.get('sel', ()) if '!' in r]
                if d.get('edge') and '!' in d['edge'][0]:          # 啟停指到別座位的觸發
                    out.append(f'{tag}#{i}.edge={d["edge"][0]}')
        return out

    def struct(n):
        return (tuple(d['type'] for d in n[0]),
                tuple('EDGE' if d['pol'] else d['type'] for d in n[1]))

    def bag(n, part, f):
        return collections.Counter(repr(d[f]) for d in n[part])

    findings, stats = [], collections.Counter()
    F = findings.append
    for pat, seats in sorted(groups.items()):
        if len(seats) < 3:
            continue
        stats['groups'] += 1
        counts = {s: len(v) for s, v in seats.items()}
        top, n = majority(counts)
        if n < len(counts):
            for s, c in counts.items():
                if repr(c) != top:
                    F(Finding('MED', pat, 0, s, None, '', '組', 'count', f'{c} 支', f'{top} 支'))
        for k in range(min(counts.values())):
            row = {s: seats[s][k] for s in seats}
            normed = {s: norm(t, s) for s, t in row.items()}
            if not any(seat_bound(n_) for n_ in normed.values()):
                continue
            # A0. enabled / looping 少數派
            flags = {s: (int(getattr(row[s], 'enabled', 0) or 0), int(getattr(row[s], 'looping', 0) or 0))
                     for s in row}
            top, n = majority(flags)
            if n * 2 > len(flags):
                for s, v in flags.items():
                    if repr(v) != top:
                        F(Finding('HIGH', pat, k, s, row[s].trigger_id, row[s].name, '整支', 'enabled/looping',
                                  f'en={v[0]} loop={v[1]}', top))
            # A. 外座位引用計數
            fr = {s: foreign(n_) for s, n_ in normed.items()}
            cnts = {s: len(v) for s, v in fr.items()}
            top, n = majority(cnts)
            if n * 2 > len(cnts):
                for s, c in cnts.items():
                    if c > int(top):
                        F(Finding('HIGH', pat, k, s, row[s].trigger_id, row[s].name, '整支', 'foreign',
                                  '；'.join(fr[s]), f'多數 {top} 個外座位引用'))
            # B. 邊極性投票
            pol = collections.defaultdict(dict)
            for s, n_ in normed.items():
                for d in n_[1]:
                    if d['edge']:
                        pol[d['edge'][0]].setdefault(s, set()).add(d['pol'])
            for rel, per in pol.items():
                if '!' in rel:
                    continue
                if len(per) >= 3:
                    vals = {s: tuple(sorted(v)) for s, v in per.items()}
                    top, n = majority(vals)
                    if n * 2 > len(vals):
                        for s, v in vals.items():
                            if repr(v) != top:
                                F(Finding('HIGH', pat, k, s, row[s].trigger_id, row[s].name, f'→{rel}',
                                          'edge_pol', v, top))
                if len(per) >= 4:
                    for s in normed:
                        if s not in per:
                            F(Finding('MED', pat, k, s, row[s].trigger_id, row[s].name, f'→{rel}',
                                      'edge_missing', '無此邊', f'{len(per)} 座位有'))
            # C. 結構孿生逐欄
            structs = {s: struct(n_) for s, n_ in normed.items()}
            top, n = majority(structs)
            if n < 3 or n * 2 <= len(structs):
                stats['struct_skipped'] += 1
                continue
            twins = {s for s, v in structs.items() if repr(v) == top}
            top_struct = structs[next(iter(twins))]
            for s in structs:
                if s not in twins:
                    # 長度相同且只差一格 → 單一效果/條件型別抄錯，HIGH 指名位置
                    diffs = [(part, i) for part, tag in ((0, 'C'), (1, 'E'))
                             if len(structs[s][part]) == len(top_struct[part])
                             for i in range(len(top_struct[part])) if structs[s][part][i] != top_struct[part][i]]
                    same_len = all(len(structs[s][p]) == len(top_struct[p]) for p in (0, 1))
                    if same_len and len(diffs) == 1:
                        part, i = diffs[0]
                        F(Finding('HIGH', pat, k, s, row[s].trigger_id, row[s].name,
                                  f'{"C" if part == 0 else "E"}#{i}', 'type',
                                  structs[s][part][i], top_struct[part][i]))
                        continue
                    F(Finding('MED', pat, k, s, row[s].trigger_id, row[s].name, '整支', 'struct',
                              f'{len(structs[s][0])}條件/{len(structs[s][1])}效果 型別序列異於他座', ''))
            stats['twin_groups'] += 1
            ref_seat = next(iter(twins))
            ref = normed[ref_seat]
            for part, tag in ((0, 'C'), (1, 'E')):
                for i in range(len(ref[part])):
                    for f in SEV:
                        if f not in ref[part][i]:
                            continue
                        vals = {s: normed[s][part][i][f] for s in twins}
                        top, n = majority(vals)
                        if n == len(vals) or n * 2 <= len(vals):
                            continue
                        if SEV[f] != 'HIGH' and n < len(vals) - 1 and len(vals) >= 5:
                            continue
                        top_seat = next(s for s, v in vals.items() if repr(v) == top)
                        for s, v in vals.items():
                            if repr(v) == top:
                                continue
                            if f == 'type' and {v, vals[top_seat]} <= {ACT, DEACT}:
                                continue                       # 極性交 B 判
                            if f == 'sp' and '!' in str(v) and '!' in str(vals[top_seat]):
                                continue                       # 兩邊皆外座位，交 A 判
                            if f in ('sel', 'sp', 'tp', 'uo', 'qty') and \
                                    bag(normed[s], part, f) == bag(normed[top_seat], part, f):
                                continue                       # 只是順序對調
                            F(Finding(SEV[f], pat, k, s, row[s].trigger_id, row[s].name, f'{tag}#{i}', f, v, top))
    order = {'HIGH': 0, 'MED': 1, 'LOW': 2}
    findings.sort(key=lambda r: (order[r.sev], r.pattern, r.occ, r.seat))
    for r in findings:
        stats[r.sev] += 1
    return findings, stats


def render_md(path, findings, stats, type_names=None):
    tn = type_names or (lambda kind, v: str(v))
    lines = [f'# 六座位對稱稽核 — {path}', '',
             f'座位樣式 {stats["groups"]} 組（≥3 座位）；孿生逐欄比對 {stats["twin_groups"]} 次；'
             f'結構各異略過 {stats["struct_skipped"]} 次；'
             f'HIGH {stats["HIGH"]}、MED {stats["MED"]}、LOW {stats["LOW"]}（LOW 不列）', '',
             '規則：A 外座位引用多於多數；B 對同一目標的啟/停極性少數派；C 結構孿生逐欄少數派。'
             'HIGH＝疑似錯家/抄反/漏改，需人工裁決入 merge_spec.trigger_fixes。', '',
             '| 嚴重 | 樣式 | 第n支 | 座位 | 觸發 | 位置 | 欄位 | 此座位值 | 多數值 |',
             '|---|---|---|---|---|---|---|---|---|']
    for r in findings:
        if r.sev == 'LOW':
            continue
        v, m = r.value, r.majority
        if r.field == 'type':
            kind = 'cond' if r.where.startswith('C') else 'eff'
            v, m = tn(kind, v), tn(kind, m)
        lines.append(f'| {r.sev} | {r.pattern} | {r.occ + 1} | {r.seat}P | T{r.tid}「{r.name}」 | {r.where} | '
                     f'{r.field} | `{v}` | `{m}` |')
    return '\n'.join(lines) + '\n'


def main(argv):
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    from core.scenario_io import load
    from AoE2ScenarioParser.datasets.effects import EffectId
    from AoE2ScenarioParser.datasets.conditions import ConditionId

    def tn(kind, v):
        try:
            v = int(v.strip("'")) if isinstance(v, str) else v
            return (EffectId if kind == 'eff' else ConditionId)(v).name
        except Exception:
            return str(v)
    path = argv[1]
    sc = load(path)                       # 需留住參考：parser 以 uuid 回查 scenario，被回收會炸
    findings, stats = audit(sc.trigger_manager.triggers)
    md = render_md(path, findings, stats, tn)
    if len(argv) > 2:
        open(argv[2], 'w', encoding='utf-8').write(md)
    print(md.split('\n')[2])
    for r in findings:
        if r.sev == 'HIGH':
            print(f'{r.pattern}\tT{r.tid}「{r.name}」\t{r.where}\t{r.field}\t{r.value}\t{r.majority}')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))

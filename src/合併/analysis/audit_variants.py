# -*- coding: utf-8 -*-
"""變體鏈路完整性稽核（跑在合併產物上）。

2026-08-30 起因：T543「5教頭2」中繼沒被矩陣複製，座位 1 的變體鏈啟動的是原版 T209（sp=5）→提示被吞。
這類「變體鏈裡還指著原版座位」的回歸只會在玩到那條線時才被發現，故改成靜態不變量：

  A. 變體的啟停邊不得指到「已有變體的原版」（該重指到同座位變體）——即 T543 型
  B. 變體的啟停邊不得指到「別座位的變體」
  C. 變體的玩家欄位（條件 sp／效果 sp、tp）若原版寫的是本職業座位，變體必須改成自己座位
  D. 未矩陣化、且非變體的觸發若有啟停邊指進「已有變體的原版」→ 列出複核
     （原版已被 s39 停用，這條邊等於斃掉；中性中繼併入後應為 0，殘留者多為跨職業/全域觸發）

用法：python -m analysis.audit_variants <產物.aoe2scenario> <logs/39_復活與選職業.tsv> [out_md]
"""
import re
import sys
import collections

from analysis.audit_symmetry import seat_pattern

ACT, DEACT = 8, 9
Finding = collections.namedtuple('Finding', 'kind variant vname base bname where target tname detail')
_ROW = re.compile(r'\ttrigger_add\tT(\d+)→位(\d)\t\S*\t\S*\tT(\d+)\t')


def load_var_map(tsv_path):
    """s39 日誌 → {(base_tid, seat): variant_tid}。"""
    m = {}
    for line in open(tsv_path, encoding='utf-8'):
        r = _ROW.search(line)
        if r:
            m[(int(r.group(1)), int(r.group(2)))] = int(r.group(3))
    return m


def seat_of_name(name):
    """座位推定：seat_pattern 優先；否則字尾數字 1–6（容許尾綴 p，如 成成6p／草草5／魂移6）。"""
    s, _ = seat_pattern(name or '')
    if s:
        return s
    m = re.search(r'([1-6])p?$', name or '')
    return int(m.group(1)) if m else None


_ACT_SRC = re.compile(r'^啟動(\d)位(\d)')


def _g(o, k, d=-1):
    v = getattr(o, k, d)
    return d if v is None else v


def audit(triggers, var_map):
    by_id = {t.trigger_id: t for t in triggers}
    base_of = {v: (b, s) for (b, s), v in var_map.items()}
    matrixed = {b for (b, _s) in var_map}
    F = []

    def name(tid):
        t = by_id.get(tid)
        return (t.name or '') if t is not None else '?'

    for v, (b, s) in sorted(base_of.items()):
        t, bt = by_id.get(v), by_id.get(b)
        if t is None or bt is None:
            continue
        cls_seat = seat_of_name(bt.name)
        eff_cls = cls_seat or 1                       # 無編號原版＝座位 1 版（南宮尾葉／南宮尾葉2…6 慣例）
        for i, e in enumerate(t.effects):
            et = _g(e, 'effect_type')
            if et in (ACT, DEACT):
                tgt = _g(e, 'trigger_id')
                if tgt in matrixed:
                    tseat = seat_of_name(name(tgt)) or 1
                    if tseat != eff_cls:
                        F.append(Finding('A2 跨職業廣播邊', v, t.name, b, bt.name, f'E#{i}', tgt, name(tgt),
                                         f'職業{eff_cls} 通知職業{tseat} 的原版（單人無害；多人需扇出）'))
                    else:
                        F.append(Finding('A1 同職業邊指原版', v, t.name, b, bt.name, f'E#{i}', tgt, name(tgt),
                                         '應重指同座位變體（T543 型）'))
                elif tgt in base_of and base_of[tgt][1] != s:
                    F.append(Finding('B 邊指他座位變體', v, t.name, b, bt.name, f'E#{i}', tgt, name(tgt),
                                     f'目標是位{base_of[tgt][1]} 的變體'))
            if cls_seat and i < len(bt.effects):
                for fld in ('source_player', 'target_player'):
                    bv, vv = _g(bt.effects[i], fld), _g(e, fld)
                    if bv == cls_seat and 1 <= vv <= 6 and vv != s:
                        F.append(Finding('C 玩家欄未改座位', v, t.name, b, bt.name, f'E#{i}.{fld}', vv, '', f'原版 {bv}→應為 {s}'))
        if cls_seat:
            for i, c in enumerate(t.conditions):
                if i < len(bt.conditions):
                    bv, vv = _g(bt.conditions[i], 'source_player'), _g(c, 'source_player')
                    if bv == cls_seat and 1 <= vv <= 6 and vv != s:
                        F.append(Finding('C 玩家欄未改座位', v, t.name, b, bt.name, f'C#{i}.sp', vv, '', f'原版 {bv}→應為 {s}'))
    for t in triggers:
        tid = t.trigger_id
        if tid in matrixed or tid in base_of:
            continue
        nm = t.name or ''
        if nm.startswith('退役_') or not _g(t, 'enabled', 0) and nm.startswith('退役'):
            continue                                   # 退役原版
        m = _ACT_SRC.match(nm)
        if m and m.group(1) == m.group(2):
            continue                                   # 啟動c位c：職業在自己座位，用原版合法
        if '◇命' in nm and '◇位' not in nm:
            continue                                   # 原版的逐命副本（座位＝職業）
        mv = re.match(r'^(.*?)◇位(\d)', nm)
        src_cls = (seat_of_name(mv.group(1)) or 1) if mv else None
        if mv and src_cls == int(mv.group(2)):
            continue                                   # 連動變體在自己職業座位：用原版合法
        for i, e in enumerate(t.effects):
            if _g(e, 'effect_type') in (ACT, DEACT) and _g(e, 'trigger_id') in matrixed:
                tgt = _g(e, 'trigger_id')
                if src_cls and (seat_of_name(name(tgt)) or 1) != src_cls:
                    continue                           # 變體副本鏡射的跨職業廣播邊（同 A2）
                tseats = {seat_of_name(name(_g(x, 'trigger_id'))) or 1 for x in t.effects
                          if _g(x, 'effect_type') in (ACT, DEACT) and _g(x, 'trigger_id') in matrixed}
                kind = 'D2 跨座位廣播（多人需扇出）' if len(tseats) >= 2 else 'D1 外部邊指入已停用原版'
                F.append(Finding(kind, tid, t.name, -1, '', f'E#{i}', tgt, name(tgt),
                                 f'來源 en={_g(t, "enabled", 0)}'))
    return F


def render_md(path, findings, n_var):
    cnt = collections.Counter(f.kind for f in findings)
    d_src = collections.Counter(re.sub(r'\d+$', 'N', f.vname or '(無名)') for f in findings if f.kind.startswith('D'))
    a2_src = collections.Counter(f.bname for f in findings if f.kind.startswith('A2'))
    lines = [f'# 變體鏈路完整性稽核 — {path}', '',
             f'變體 {n_var} 支；A1 同職業邊指原版 {cnt["A1 同職業邊指原版"]}、A2 跨職業廣播邊 {cnt["A2 跨職業廣播邊"]}、'
             f'B {cnt["B 邊指他座位變體"]}、C {cnt["C 玩家欄未改座位"]}、D1 外部邊指入原版 {cnt["D1 外部邊指入已停用原版"]}、'
             f'D2 跨座位廣播 {cnt["D2 跨座位廣播（多人需扇出）"]}', '',
             'A2 來源原版分佈（前 20）：' + '；'.join(f'{k} ×{v}' for k, v in a2_src.most_common(20)), '',
             'D 來源名稱分佈（前 30，數字尾正規化）：' + '；'.join(f'{k} ×{v}' for k, v in d_src.most_common(30)), '',
             '| 類 | 觸發 | 原版 | 位置 | 目標 | 說明 |', '|---|---|---|---|---|---|']
    for f in findings:
        if f.kind.startswith('A2') or f.kind.startswith('D2'):
            continue                                   # 表格只列需處理者；A2/D2 看分佈
        lines.append(f'| {f.kind} | T{f.variant}「{f.vname}」 | T{f.base}「{f.bname}」 | {f.where} | '
                     f'T{f.target}「{f.tname}」 | {f.detail} |')
    return '\n'.join(lines) + '\n'


def main(argv):
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    from core.scenario_io import load
    sc = load(argv[1])
    var_map = load_var_map(argv[2])
    findings = audit(sc.trigger_manager.triggers, var_map)
    md = render_md(argv[1], findings, len(var_map))
    if len(argv) > 3:
        open(argv[3], 'w', encoding='utf-8', newline='\n').write(md)
    print(md.split('\n')[2])
    shown = [x for x in findings if not (x.kind.startswith('A2') or x.kind.startswith('D2'))]
    parts = md.split('\n')
    print(parts[4]); print(parts[6])
    for f in shown[:60]:
        print(f'{f.kind}\tT{f.variant}「{f.vname}」\t{f.where}\t→T{f.target}「{f.tname}」\t{f.detail}')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))

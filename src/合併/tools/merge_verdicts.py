# -*- coding: utf-8 -*-
"""把 verdicts/*.yaml（裁決代理的產出）併回 audit_ledger.yaml，並自動對帳 merge_spec。

為什麼要自動對帳：帳本是 2026-08-31 才建的，但歷次 session 早就修過一批原作 bug——
那些 finding 在帳本裡仍是 pending，實際上 `merge_spec.params.trigger_fixes` 已有對應條目。
第一批裁決代理回報 54 條「建議修」裡有 53 條屬於此類。與其人工重判，不如**位置對位置**比對：
finding 的 (觸發 id, 位置, 欄位) 若能在 spec 找到同一處的修正 → 直接記 `fixed`。

保守原則：只在**明確對得上**時才自動改判 fixed，其餘一律尊重代理的裁決：
  - `E#n` / `C#n` ＋ 欄位對得上 spec 的 effect/condition 條目（同 index、同欄位）
  - `整支|enabled/looping` ＋ spec 有該 tid 的 `kind: trigger` 條目
  - `整支|foreign` ＋ spec 有該 tid 的玩家欄／ref 欄修正（規則 A 與 C 常是同一 bug 的兩份報告）
用法（在 src/合併 下）：python tools/merge_verdicts.py [--dry-run]
"""
import io
import sys
from pathlib import Path

sys.path.insert(0, __file__.rsplit('tools', 1)[0])

# 稽核欄位名 → merge_spec 欄位名
FIELD_MAP = {'sp': ('source_player',), 'tp': ('target_player',), 'uo': ('unit_object',),
             'sel': ('selected_object_ids',), 'nsel': ('selected_object_ids',),
             # 改攻效果在 s30 之後量值走 armour_attack_quantity，spec 條目會寫那個欄位
             'qty': ('quantity', 'armour_attack_quantity'),
             'timer': ('timer',), 'olu': ('object_list_unit_id',),
             'type': ('effect_type', 'condition_type'), 'attr': ('attribute',), 'var': ('variable',)}
REF_FIELDS = {'source_player', 'target_player', 'unit_object', 'selected_object_ids'}
STRUCTURAL_FIELDS = REF_FIELDS | {'trigger_id', 'effect_type', 'condition_type', 'enabled', 'looping'}


def spec_index(entries):
    """→ {tid: [條目…]}。"""
    out = {}
    for e in entries:
        tid = e.get('trigger_id')
        if tid is not None:
            out.setdefault(int(tid), []).append(e)
    return out


def spec_covers(key, idx):
    """這條 finding 是否已被 merge_spec 修掉（保守比對）。回傳 (是否, 說明)。"""
    parts = key.split('|')
    if len(parts) != 5:
        return False, ''
    _, _, tid_s, where, field = parts
    if not tid_s.startswith('T') or not tid_s[1:].isdigit():
        return False, ''
    fixes = idx.get(int(tid_s[1:]))
    if not fixes:
        return False, ''
    if where == '整支' and field == 'enabled/looping':
        hit = [e for e in fixes if e.get('kind') == 'trigger']
        if hit:
            return True, f'spec 已改整支旗標（{hit[0].get("field")}: {hit[0].get("old")}→{hit[0].get("new")}）'
    if where == '整支' and field in ('foreign', 'struct', 'absent'):
        # 整支層級的 finding 說的是「這支與兄弟座位不一樣」，spec 只要在這支做過結構性修正就算已處理。
        # （foreign 也可能是「指錯目標」＝改 trigger_id；struct／absent 的修法多半是 effect_add。）
        hit = [e for e in fixes if e.get('kind') in ('effect_add', 'condition_add')
               or e.get('field') in STRUCTURAL_FIELDS]
        if hit:
            k = hit[0]
            desc = {'effect_add': 'effect_add 補效果', 'condition_add': 'condition_add 補條件'}.get(
                k.get('kind'), f'{k.get("kind")} #{k.get("index")} 的 {k.get("field")}')
            return True, f'spec 已在該支做結構性修正（{desc}）'
    if where.startswith('→') and field in ('edge_pol', 'edge_missing'):
        # 邊類 finding 的「位置」是目標樣式不是 E#n，無法逐位比對；
        # spec 若在該支改過 effect_type（啟停極性抄反）或 trigger_id（指錯目標）或補過啟停效果，即視為已修。
        hit = [e for e in fixes if (e.get('kind') == 'effect' and e.get('field') in ('effect_type', 'trigger_id'))
               or e.get('kind') == 'effect_add']
        if hit:
            k = hit[0]
            desc = (f'{k.get("kind")} #{k.get("index")} 的 {k.get("field")}'
                    if k.get('kind') == 'effect' else 'effect_add 補啟停效果')
            return True, f'spec 已改該支的啟停邊（{desc}）'
    if where[:2] in ('E#', 'C#') and where[2:].isdigit():
        want_kind = 'effect' if where[0] == 'E' else 'condition'
        want_fields = FIELD_MAP.get(field)
        i = int(where[2:])
        hit = [e for e in fixes if e.get('kind') == want_kind and e.get('index') == i
               and (want_fields is None or e.get('field') in want_fields)]
        if hit:
            return True, f'spec 已改 {where} 的 {hit[0].get("field")}（{hit[0].get("old")}→{hit[0].get("new")}）'
    return False, ''


def merge(ledger, verdict_files, spec_entries):
    """回傳 (新帳本, 統計)。"""
    from analysis.ledger import load as lload
    idx = spec_index(spec_entries)
    out = dict(ledger)
    stats = {'verdict_files': 0, 'from_agents': 0, 'auto_fixed': 0, 'unknown_key': 0,
             'kept_resolved': 0}
    for p in sorted(verdict_files):
        stats['verdict_files'] += 1
        for key, rec in lload(p).items():
            if key not in out:
                stats['unknown_key'] += 1
                continue
            if out[key]['verdict'] in ('fixed', 'wontfix') and rec['verdict'] == 'pending':
                stats['kept_resolved'] += 1     # 帳本已結案者不被代理檔的 pending 蓋回去（2026-09-01）
                continue
            out[key] = dict(rec)
            stats['from_agents'] += 1
    for key, rec in out.items():
        if rec['verdict'] != 'pending':
            continue
        if '需裁決' in rec.get('reason', ''):
            continue        # 代理明說要人判的，不准被 spec 對帳自動結案（2026-09-01）
        ok, why = spec_covers(key, idx)
        if ok:
            out[key] = {'verdict': 'fixed',
                        'reason': f'{why}；原裁決：{rec["reason"][:80]}' if rec['reason'] else why}
            stats['auto_fixed'] += 1
    return out, stats


def main(argv):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    from analysis.ledger import load as lload, save as lsave
    import yaml
    led = lload('audit_ledger.yaml')
    files = sorted(Path('verdicts').glob('*.yaml')) if Path('verdicts').exists() else []
    spec = yaml.safe_load(open('merge_spec.yaml', encoding='utf-8'))['params'].get('trigger_fixes') or []
    new, stats = merge(led, files, spec)
    import collections
    tally = collections.Counter(v['verdict'] for v in new.values())
    print(f'裁決檔 {stats["verdict_files"]} 份；代理裁決 {stats["from_agents"]} 條；'
          f'對帳 spec 自動改判 fixed {stats["auto_fixed"]} 條；帳本沒有的 key {stats["unknown_key"]} 條')
    print('合併後帳本：' + '、'.join(f'{k} {v}' for k, v in sorted(tally.items())))
    if '--dry-run' not in argv:
        lsave('audit_ledger.yaml', new,
              header='六座位對稱稽核裁決帳本（analysis/ledger.py；不是建置輸入，真要修寫進 merge_spec）')
        print('已寫回 audit_ledger.yaml')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))

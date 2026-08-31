# -*- coding: utf-8 -*-
"""稽核裁決帳本（2026-08-31）。

問題：`audit_symmetry` 每次印 715 組、HIGH 118 條，人不可能每次看完——這次西碼頭
「只有座位 1 有等級門檻」的線索早就在報告裡，就是被埋掉的。**檢測能力夠，缺的是記帳。**

帳本記下每條 finding 的裁決，稽核改印差異：
    新增 N 條（要看）／待裁決 M 條（還沒判）／已裁決 K 條（摺疊）／消失 G 條（**也要看**）
「消失」同樣重要：本來報的異常突然不報了，可能是我們把它的前提改壞了。

**帳本不是建置輸入**——`merge_spec.yaml` 才是裁決權威（真要修就寫成 trigger_fixes）。
帳本只是複核記錄，記「看過了、判定如何」。

檔案格式（`audit_ledger.yaml`）：
    entries:
      - {key: 'X船|1|T3685|absent', verdict: wontfix, reason: 原作廢棄路線，2026-08-31 裁決}
verdict ∈ fixed（已在 spec 修掉）／wontfix（判定不修，reason 必填）／pending（尚未裁決）
"""
from pathlib import Path

VERDICTS = ('fixed', 'wontfix', 'pending')


def load(path):
    """→ {key: {'verdict': str, 'reason': str}}；檔案不存在＝空帳本。"""
    p = Path(path)
    if not p.exists():
        return {}
    import yaml
    raw = yaml.safe_load(p.read_text(encoding='utf-8')) or {}
    out = {}
    for e in raw.get('entries') or []:
        v = e.get('verdict', 'pending')
        out[e['key']] = {'verdict': v if v in VERDICTS else 'pending',
                         'reason': e.get('reason', '')}
    return out


def save(path, entries, header=''):
    """穩定排序寫回，方便 git diff 看出「這次多了哪幾條待裁決」。"""
    lines = [f'# {header}' if header else '# 稽核裁決帳本（見 analysis/ledger.py）', 'entries:']
    for key in sorted(entries):
        e = entries[key]
        reason = str(e.get('reason', '')).replace('"', "'")
        lines.append(f'  - {{key: "{key}", verdict: {e.get("verdict", "pending")}, reason: "{reason}"}}')
    Path(path).write_text('\n'.join(lines) + '\n', encoding='utf-8')


def classify(keyed_findings, ledger):
    """keyed_findings: [(key, 任意物件)]。回傳 dict(new/pending/resolved/gone)。
    gone＝帳本有、這次沒報（前提被改壞的訊號）。"""
    seen = {}
    for key, item in keyed_findings:
        seen.setdefault(key, item)
    out = {'new': [], 'pending': [], 'resolved': [], 'gone': []}
    for key, item in seen.items():
        rec = ledger.get(key)
        if rec is None:
            out['new'].append((key, item))
        elif rec['verdict'] == 'pending':
            out['pending'].append((key, item))
        else:
            out['resolved'].append((key, item))
    for key, rec in ledger.items():
        if key not in seen:
            out['gone'].append((key, rec))
    return out


def summary(cls):
    return (f'新增 {len(cls["new"])} 條（要看）／待裁決 {len(cls["pending"])}／'
            f'已裁決 {len(cls["resolved"])}（摺疊）／消失 {len(cls["gone"])}'
            + ('（消失要看：本來報的異常不報了，可能是前提被改壞）' if cls['gone'] else ''))


def merge_pending(ledger, cls):
    """把新增條目以 pending 併入帳本（供 --record 一次建檔）。回傳新帳本。"""
    out = dict(ledger)
    for key, _ in cls['new']:
        out.setdefault(key, {'verdict': 'pending', 'reason': ''})
    return out

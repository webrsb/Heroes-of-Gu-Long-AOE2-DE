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


def _esc(s):
    """雙引號 YAML 純量的跳脫。控制字元／DEL 必須寫成 \\xHH——原作觸發名含 DEL（如 `\\x7f少林寺`），
    原樣寫進 YAML 會讓整份檔案讀不回來（2026-09-01 踩過；merge_spec.yaml 也有同款教訓）。"""
    out = []
    for ch in str(s):
        if ch == '\\':
            out.append('\\\\')
        elif ch == '"':
            out.append("'")
        elif ord(ch) < 0x20 or ord(ch) == 0x7f:
            out.append(f'\\x{ord(ch):02X}')
        else:
            out.append(ch)
    return ''.join(out)


def load(path):
    """→ {key: {'verdict': str, 'reason': str}}；檔案不存在＝空帳本。"""
    p = Path(path)
    if not p.exists():
        return {}
    import yaml
    text = p.read_text(encoding='utf-8')
    if '\x7f' in text:                      # 舊檔可能有原樣寫入的 DEL，容錯轉成跳脫再解析
        text = text.replace('\x7f', '\\x7F')
    raw = yaml.safe_load(text) or {}
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
        lines.append(f'  - {{key: "{_esc(key)}", verdict: {e.get("verdict", "pending")}, '
                     f'reason: "{_esc(e.get("reason", ""))}"}}')
    Path(path).write_text('\n'.join(lines) + '\n', encoding='utf-8', newline='\n')


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

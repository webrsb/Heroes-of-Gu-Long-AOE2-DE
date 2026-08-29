# -*- coding: utf-8 -*-
"""統一異動資料結構。所有 step 的產出、log 與測試指引的唯一來源。"""
from dataclasses import dataclass

TSV_HEADER = 'step\tkind\ttarget\tfield\told\tnew\treason'

@dataclass
class Change:
    step: str    # 's10'
    kind: str    # trigger_add / remap / effect / unit_add / unit_field / param / audit
    target: str  # 'T5599「幫眾」效果3' / 'ref31245 聚魂塔'
    field: str   # 'trigger_id' / 'quantity' / '—'
    old: str
    new: str
    reason: str  # 規格出處或 merge_spec 條目

def _esc(s: str) -> str:
    return str(s).replace('\t', '␉').replace('\n', '␊')

def to_tsv_row(c: Change) -> str:
    return '\t'.join(_esc(v) for v in (c.step, c.kind, c.target, c.field, c.old, c.new, c.reason))

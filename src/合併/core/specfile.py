# -*- coding: utf-8 -*-
"""merge_spec.yaml —— 圈選與裁決的唯一權威。"""
from dataclasses import dataclass
from pathlib import Path
import yaml

class SpecError(Exception):
    pass

@dataclass
class Group:
    name: str
    action: str          # auto / patch / skip
    trigger_ids: list

@dataclass
class Override:
    target: str
    field: str
    value: str
    reason: str

@dataclass
class MergeSpec:
    groups: list
    overrides: list
    params: dict

_ACTIONS = {'auto', 'patch', 'skip'}

def load_spec(path: Path) -> MergeSpec:
    raw = yaml.safe_load(Path(path).read_text(encoding='utf-8')) or {}
    groups = []
    for g in raw.get('groups') or []:
        if g.get('action') not in _ACTIONS:
            raise SpecError(f"群組「{g.get('name')}」的 action={g.get('action')!r} 不合法，"
                            f"必須是 {sorted(_ACTIONS)}")
        groups.append(Group(g['name'], g['action'], list(g.get('trigger_ids') or [])))
    overrides = [Override(o['target'], o['field'], str(o['value']), o.get('reason', ''))
                 for o in (raw.get('overrides') or [])]
    return MergeSpec(groups, overrides, raw.get('params') or {})

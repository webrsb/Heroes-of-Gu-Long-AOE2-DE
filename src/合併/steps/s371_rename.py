# -*- coding: utf-8 -*-
"""s371 觸發重命名（params.renames）。

原作 168 支「觸發事件 N」／「觸發事件 X僧」等無語意名稱，改成「座位數字開頭＋家族字根＋階段字尾」
（如 `3客棧8罰`、`5拳氣起`、`6當僧`），讓 `audit_symmetry.seat_pattern` 的首碼規則直接成組；無座位者用角色＋原編號。
排在 s37 之後：s37 的名稱防呆仍以舊名比對。每條帶 old 舊名防呆（不符→BuildError）。
`analysis.audit_symmetry` 在基底原檔上套同一份對照表，稽核與產物名稱一致。
"""
from core.change import Change
from .base import Step, BuildError, trig_by_id


def apply_renames(tm, rows):
    changes, seen = [], set()
    for r in rows:
        tid = int(r['tid'])
        if tid in seen:
            raise BuildError(f'缺裁決：renames T{tid} 重複')
        seen.add(tid)
        t = trig_by_id(tm, tid)
        if t is None:
            raise BuildError(f'缺裁決：renames T{tid} 不存在')
        if (t.name or '') != r['old']:
            raise BuildError(f'缺裁決：renames T{tid} 現名 {t.name!r} ≠ spec 舊名 {r["old"]!r}，請重查')
        t.name = r['new']
        changes.append(Change('s371', 'rename', f'T{tid}', 'name', r['old'], r['new'], r.get('reason', '座位首碼命名')))
    return changes


class RenameStep(Step):
    id = 's371'
    title = '觸發重命名'
    intro = '依 params.renames 把無語意的「觸發事件 N」改為座位首碼＋家族字根（帶舊名防呆）。'

    def apply(self, ctx):
        rows = ctx.spec.params.get('renames')
        if not rows:
            return []
        return apply_renames(ctx.base.trigger_manager, rows)

    def test_guide(self, changes):
        if not changes:
            return None
        return f'重命名 {len(changes)} 支；純名稱、不影響遊戲行為。編輯器（只看不存）可見「1客棧5扣」等新名。'


STEP = RenameStep()

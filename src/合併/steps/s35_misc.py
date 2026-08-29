# -*- coding: utf-8 -*-
"""s35 雜項 const 替換（436→2353 這類「DE 無外觀」的物件換皮）。
expect_count 防呆：合併版找到的數量與預期不符 → BuildError 要求重新裁決。"""
from core.change import Change
from .base import Step, BuildError


def apply_replacement(units, spec_entry) -> list:
    find_const = spec_entry['find']['unit_const']
    hits = [u for u in units if u.unit_const == find_const]
    if len(hits) != spec_entry['expect_count']:
        raise BuildError(f'缺裁決：「{spec_entry["label"]}」在基底找到 {len(hits)} 個 '
                         f'const {find_const}，spec 預期 {spec_entry["expect_count"]}，'
                         f'請重查後更新 expect_count 或撤此條')
    changes = []
    for u in hits:
        u.unit_const = spec_entry['to_const']
        changes.append(Change('s35', 'unit_field',
                              f'ref{u.reference_id} ({u.x},{u.y})', 'unit_const',
                              str(find_const), str(spec_entry['to_const']),
                              spec_entry.get('reason', '')))
        deg = spec_entry.get('rotate_deg')
        if deg:
            import math
            old = u.rotation
            u.rotation = (u.rotation + math.radians(deg)) % (2 * math.pi)
            changes.append(Change('s35', 'unit_field',
                                  f'ref{u.reference_id} ({u.x},{u.y})', 'rotation',
                                  f'{old:.3f}', f'{u.rotation:.3f}（+{deg}°）',
                                  spec_entry.get('reason', '')))
    return changes


class MiscStep(Step):
    id = 's35'
    title = '雜項替換'
    intro = '依 params.misc.const_replacements 執行物件 const 換皮。'

    def apply(self, ctx):
        changes = []
        entries = ((ctx.spec.params.get('misc') or {}).get('const_replacements')) or []
        if not entries:
            return changes
        all_units = [u for p in range(9) for u in ctx.base.unit_manager.units[p]]
        for entry in entries:
            changes.extend(apply_replacement(all_units, entry))
        return changes

    def test_guide(self, changes):
        spots = [f'{c.target}（{c.old}→{c.new}）' for c in changes]
        return ('const 替換：' + '；'.join(spots) + '\n'
                '怎麼測：到上列座標看物件。\n'
                '預期：有外觀、模型正確、小地圖與實景一致。\n'
                '異常判讀：隱形或問號模型＝新 const 也無外觀，回報座標。')


STEP = MiscStep()

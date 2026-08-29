# -*- coding: utf-8 -*-
"""s35 雜項 const 替換（436→2353 這類「DE 無外觀」的物件換皮）＋城門特例＋換皮碰撞稽核。
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


def apply_gate_fix(um, entry) -> list:
    """拆 remove_const 構件、於構件包絡中點置一座 gate_const 城門（spec §二 95 城門）。"""
    rc = entry['remove_const']
    hits = [u for p in range(9) for u in um.units[p] if u.unit_const == rc]
    if len(hits) != entry['expect_count']:
        raise BuildError(f'缺裁決：gate_fix 找到 {len(hits)} 個 const {rc}，'
                         f'spec 預期 {entry["expect_count"]}，請重查')
    xs = [u.x for u in hits]
    ys = [u.y for u in hits]
    cx = (min(xs) + max(xs)) / 2
    cy = (min(ys) + max(ys)) / 2
    changes = []
    for u in hits:
        um.remove_unit(reference_id=u.reference_id)
        changes.append(Change('s35', 'unit_remove',
                              f'ref{u.reference_id} ({u.x},{u.y})', 'unit_const',
                              str(rc), '（移除）', '城門構件拆除'))
    g = um.add_unit(player=entry['player'], unit_const=entry['gate_const'], x=cx, y=cy)
    changes.append(Change('s35', 'unit_add',
                          f'ref{g.reference_id} ({cx},{cy})', 'unit_const',
                          '（新增）', str(entry['gate_const']), '置換石門（包絡中點）'))
    return changes


def _area_covers(x1, y1, x2, y2, ux, uy):
    if x1 in (-1, None) or x2 in (-1, None):
        return True                      # 無區域＝全圖
    return x1 <= ux <= x2 + 1 and y1 <= uy <= y2 + 1


def audit_const_collision(tm, um, new_consts) -> list:
    """換皮碰撞稽核：觸發以新 const 過濾（條件 object_list／效果 object_list_unit_id）
    且區域涵蓋任一換皮後單位座標 → 告警清單（條件與效果雙側都掃）。"""
    targets = {}
    for p in range(9):
        for u in um.units[p]:
            if u.unit_const in new_consts:
                targets.setdefault(u.unit_const, []).append((u.x, u.y))
    hits = []
    for t in tm.triggers:
        for i, c in enumerate(t.conditions):
            ol = getattr(c, 'object_list', -1)
            if ol in targets:
                for ux, uy in targets[ol]:
                    if _area_covers(c.area_x1, c.area_y1, c.area_x2, c.area_y2, ux, uy):
                        hits.append(f'T{t.trigger_id}「{t.name or "(無名)"}」C{i} '
                                    f'object_list={ol} 涵蓋換皮單位 ({ux},{uy})')
                        break
        for i, e in enumerate(t.effects):
            ol = getattr(e, 'object_list_unit_id', -1)
            if ol in targets and not (getattr(e, 'selected_object_ids', None) or []):
                for ux, uy in targets[ol]:
                    if _area_covers(e.area_x1, e.area_y1, e.area_x2, e.area_y2, ux, uy):
                        hits.append(f'T{t.trigger_id}「{t.name or "(無名)"}」E{i} '
                                    f'object_list_unit_id={ol} 涵蓋換皮單位 ({ux},{uy})')
                        break
    return hits


class MiscStep(Step):
    id = 's35'
    title = '雜項替換'
    intro = '依 params.misc.const_replacements 執行物件 const 換皮；gate_fix 城門特例。'

    def apply(self, ctx):
        changes = []
        misc = (ctx.spec.params.get('misc') or {})
        entries = misc.get('const_replacements') or []
        all_units = [u for p in range(9) for u in ctx.base.unit_manager.units[p]]
        for entry in entries:
            changes.extend(apply_replacement(all_units, entry))
        gate = misc.get('gate_fix')
        if gate:
            changes.extend(apply_gate_fix(ctx.base.unit_manager, gate))
        # 換皮碰撞稽核：新 const 的既有過濾與換皮單位交集 → 無豁免即 BuildError
        new_consts = sorted({e['to_const'] for e in entries} |
                            ({gate['gate_const']} if gate else set()))
        if new_consts:
            waivers = set(misc.get('collision_waivers') or [])
            collisions = [h for h in audit_const_collision(
                ctx.base.trigger_manager, ctx.base.unit_manager, new_consts)
                if not any(w in h for w in waivers)]
            if collisions:
                raise BuildError('缺裁決：換皮碰撞未豁免——\n' + '\n'.join(collisions[:20]))
        ctx.notes['misc_new_consts'] = new_consts
        return changes

    def test_guide(self, changes):
        spots = [f'{c.target}（{c.old}→{c.new}）' for c in changes if c.kind == 'unit_field']
        adds = [c.target for c in changes if c.kind == 'unit_add']
        lines = ['const 替換：' + '；'.join(spots) if spots else 'const 替換：無']
        if adds:
            lines.append('城門重建：' + '；'.join(adds) + '——到場看門有外觀、開關正常、堵住牆缺口。')
        lines.append('怎麼測：到上列座標看物件。預期：有外觀、模型正確、小地圖與實景一致。\n'
                     '異常判讀：隱形或問號模型＝新 const 也無外觀，回報座標。')
        return '\n'.join(lines)


STEP = MiscStep()

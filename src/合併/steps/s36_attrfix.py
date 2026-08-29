# -*- coding: utf-8 -*-
"""s36 換皮單位屬性校正（spec §二）：MODIFY_ATTRIBUTE 於 t=0 初始化觸發，
校正回 1.21z 原版值。整數屬性一條 SET；分數屬性 SET＋DIVIDE 兩段式
（quantity 是 int32，0.88=SET 88÷100）。屬性名走映射表（parser 實名）。"""
from core.change import Change
from .base import Step, BuildError

SET, DIVIDE = 1, 5
# 屬性名 → (ObjectAttribute id, 是否用 armour 欄位, armour class)
_SIMPLE = {'hit_points': 0, 'movement_speed': 5, 'attack_reload_time': 10}


def _attr_map(name):
    if name in _SIMPLE:
        return _SIMPLE[name], None
    if name.startswith('attack_c'):
        return 9, int(name[len('attack_c'):])
    if name.startswith('armor_c'):
        return 8, int(name[len('armor_c'):])
    raise BuildError(f'缺裁決：attr_fixes 不認得屬性「{name}」（映射表：'
                     f'{sorted(_SIMPLE)} / attack_cN / armor_cN）')


def expand_attr_entries(entries) -> list:
    """展開為逐效果列：[{unit_const, player, attribute, operation, quantity, aaq, aac}]。
    分數屬性（[分子, 分母]）展開為 SET＋DIVIDE 相鄰兩列。"""
    rows = []
    for e in entries:
        for player in e['players']:
            for name, val in e['attrs'].items():
                attr, aac = _attr_map(name)
                steps = ([(SET, val)] if not isinstance(val, (list, tuple))
                         else [(SET, val[0]), (DIVIDE, val[1])])
                for op, q in steps:
                    if aac is None:
                        rows.append(dict(unit_const=e['unit_const'], player=player,
                                         attribute=attr, operation=op,
                                         quantity=q, aaq=None, aac=None))
                    else:
                        rows.append(dict(unit_const=e['unit_const'], player=player,
                                         attribute=attr, operation=op,
                                         quantity=None, aaq=q, aac=aac))
    return rows


def apply_attr_fixes(tm, entries, gate=None) -> list:
    rows = expand_attr_entries(entries)
    t = tm.add_trigger('屬性校正', enabled=True, looping=False)
    t.new_condition.timer(timer=0)
    changes = []
    for r in rows:
        t.new_effect.modify_attribute(
            quantity=r['quantity'], armour_attack_quantity=r['aaq'],
            armour_attack_class=r['aac'], object_list_unit_id=r['unit_const'],
            source_player=r['player'], operation=r['operation'],
            object_attributes=r['attribute'])
        val = r['quantity'] if r['quantity'] is not None else f"c{r['aac']}:{r['aaq']}"
        changes.append(Change('s36', 'attr_fix',
                              f"P{r['player']} const{r['unit_const']}",
                              f"attr{r['attribute']}",
                              f"op{r['operation']}", str(val), '換皮屬性校正'))
    if gate:
        ref, hp = gate
        t.new_effect.change_object_hp(quantity=hp, selected_object_ids=[ref],
                                      source_player=8, operation=SET)
        changes.append(Change('s36', 'gate_hp', f'ref{ref}', 'hit_points',
                              '（dat 1650）', str(hp), '城門血逐ref校正（防波及既有c88）'))
    return changes


class AttrFixStep(Step):
    id = 's36'
    title = '換皮屬性校正'
    intro = '依 params.attr_fixes 以 MODIFY_ATTRIBUTE 校正換皮單位到 1.21z 原版值。'

    def apply(self, ctx):
        entries = ctx.spec.params.get('attr_fixes') or []
        gate_ref = ctx.notes.get('gate_ref')
        gate_hp = ((ctx.spec.params.get('misc') or {}).get('gate_fix') or {}).get('hp')
        if not entries and gate_ref is None:
            return []
        changes = apply_attr_fixes(ctx.base.trigger_manager, entries,
                                   gate=(gate_ref, gate_hp) if gate_ref is not None and gate_hp else None)
        return changes

    def test_guide(self, changes):
        consts = sorted({c.target.split('const')[1] for c in changes})
        return ('屬性校正：const ' + '、'.join(consts) + '\n'
                '怎麼測：點選換皮單位看 tooltip（拳 HP75/攻10；37怪 HP110/攻7；'
                '573民兵 HP45/攻0；城門 HP2750）。攻擊顯示為基礎+加成、合計正確即過。\n'
                '陽性對照：任一未校正單位數值照舊。')


STEP = AttrFixStep()

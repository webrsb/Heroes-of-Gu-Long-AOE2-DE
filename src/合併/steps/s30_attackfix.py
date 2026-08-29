# -*- coding: utf-8 -*-
"""s30 攻擊力修復。變換核心逐行移植自 src/新負血劍譜/fix_attack.py
（遷移記錄 §3.3c/§3.3d/§3.3e，ZZ_test02d 實測傷害驗證）：

    DE 轉檔把 AoC 的攻擊力數值當「護甲類型打包值」在 ×256 邊界重新切分。
    還原兩層：
      1. 撤銷切分：M = (|DE現值| >> 16) * 256 + (|DE現值| & 0xFFFF)
      2. int16 解讀：S = as_int16(±M)（作者用回繞表達負值，如 65036 = −500）
    寫回：class=0, amount=|S|, operation=ADD/SUBTRACT。

放在合併之後（s10 < s30），搬入的劍譜5 觸發與基底一次修完。
"""
from AoE2ScenarioParser.datasets.effects import EffectId
from AoE2ScenarioParser.datasets.trigger_lists import Operation
from core.change import Change
from .base import Step

ADD = int(Operation.ADD)
SUB = int(Operation.SUBTRACT)
_ATK = int(EffectId.CHANGE_OBJECT_ATTACK)


def as_int16(v):
    v &= 0xFFFF
    return v - 65536 if v >= 32768 else v


def restore(de_raw):
    """DE 現值 -> (原值絕對量, operation)。None = 不需修改。"""
    sign = -1 if de_raw < 0 else 1
    v = abs(de_raw)
    cls = v >> 16
    amt = v & 0xFFFF
    if sign > 0 and cls == 0:
        return None                       # 原值 < 256，DE 已正確處理
    M = cls * 256 + amt
    S = as_int16(M) if sign > 0 else as_int16(-M)
    if S == 0:
        return None
    return abs(S), (ADD if S > 0 else SUB)


def needs_fix(e) -> bool:
    return (int(e.effect_type) == _ATK and e.quantity is not None
            and restore(e.quantity) is not None)


class AttackFixStep(Step):
    id = 's30'
    title = '攻擊力修復'
    intro = '對合併後全檔還原被 DE 轉檔切壞的 Change Object Attack 效果（§3.3e 公式）。'

    def apply(self, ctx):
        changes = []
        for t in ctx.base.trigger_manager.triggers:
            for i, e in enumerate(t.effects):
                if int(e.effect_type) != _ATK or e.quantity is None:
                    continue
                r = restore(e.quantity)
                if r is None:
                    continue
                V, op = r
                old = e.quantity
                e.operation = op
                e.armour_attack_class = 0
                e.armour_attack_quantity = V
                changes.append(Change(
                    self.id, 'effect', f'T{t.trigger_id}「{t.name}」效果{i}',
                    'quantity', str(old),
                    f'class0 {"＋" if op == ADD else "−"}{V}', '§3.3e 還原公式'))
        return changes

    def test_guide(self, changes):
        return (f'修復 {len(changes)} 個攻擊力效果。\n'
                '怎麼測：記下角色目前打怪的單下傷害 → 買一次神兵（任一職業）→ 再打同種怪。\n'
                '預期：買後單下傷害明顯上升。\n'
                '異常判讀：買後傷害不變＝修復未生效，回報職業與神兵名。')


STEP = AttackFixStep()

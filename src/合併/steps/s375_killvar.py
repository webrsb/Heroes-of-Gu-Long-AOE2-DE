# -*- coding: utf-8 -*-
"""s375 擊殺獎勵變數化（2026-08-30 死亡後獎勵停擺回歸修復）。

原作獎勵條件 Accumulate Attribute 屬性44(Kill Ratio=擊殺−損失)≥1，領獎後 X升級 觸發
「建立 Joan→Kill→Remove」製造一次損失扣回 0。英雄死亡亦算損失 → 復活後 KR 負值 →
獎勵停擺。DE 屬性44 唯讀（spike_killratio），改以屬性20（純擊殺）＋DE 變數重建同語意：
  V_K[s]    ← 屬性20  （共用迴圈每 tick 寫入，s=玩家位）
  獎勵條件   CompareVariables(V_K[p] > V_BASE[p])
  X升級      V_BASE[p] += 1（等價原作 KR−1，多殺多領語意保留）
變數編號以玩家位為索引；s39 矩陣改寫時 variable/variable2 隨 cid→slot 一起換
（見 var_slot_rewrite）。必在 s39 之前執行。"""
from core.change import Change
from .base import trig_by_id, Step, BuildError
from .revive_mount import neutralize_effect

COMPARE_VARIABLES, VARIABLE_VALUE = 78, 22
CHANGE_VARIABLE, MODIFY_VAR_BY_RESOURCE, MODIFY_VAR_BY_VAR = 56, 86, 100
LARGER, SET, ADD = 2, 1, 2
KR_ATTR = 44


def var_slot_rewrite(obj, cid, slot, offsets):
    """條件/效果的 variable/variable2 若 == off+cid → off+slot。回傳是否有改。"""
    hit = False
    for fld in ('variable', 'variable2'):
        v = getattr(obj, fld, -1)
        if v in (-1, None):
            continue
        for off in offsets:
            if v == off + cid:
                setattr(obj, fld, off + slot)
                hit = True
                break
    return hit


def apply_killvar(tm, params):
    reset_tids = [int(x) for x in params['reset_tids']]
    kills_attr = int(params['kills_attr'])
    vk, vb = int(params['v_kills_offset']), int(params['v_base_offset'])
    changes = []

    used = sum(1 for t in tm.triggers for c in t.conditions
               if getattr(c, 'condition_type', None) in (VARIABLE_VALUE, COMPARE_VARIABLES))
    used += sum(1 for t in tm.triggers for e in t.effects
                if getattr(e, 'effect_type', None) in (CHANGE_VARIABLE, MODIFY_VAR_BY_RESOURCE,
                                                       MODIFY_VAR_BY_VAR))
    if used:
        raise BuildError(f'缺裁決：基底已有 {used} 處 DE 變數用法，變數編號需先裁決避撞')

    for s in range(1, 7):
        tm.add_variable(f'擊殺數P{s}', variable_id=vk + s)
        tm.add_variable(f'領獎基準P{s}', variable_id=vb + s)

    # ---- 條件轉換：KR≥1 → V_K[p] > V_BASE[p] ----
    n_cond = 0
    for t in tm.triggers:
        for ci, c in enumerate(t.conditions):
            if getattr(c, 'condition_type', None) != 8 or getattr(c, 'attribute', -1) != KR_ATTR:
                continue
            p = getattr(c, 'source_player', -1)
            if getattr(c, 'quantity', -1) != 1 or p not in range(1, 7):
                raise BuildError(f'缺裁決：T{t.trigger_id}C{ci} KR 條件 qty={c.quantity} '
                                 f'sp={p} 非標準型（qty=1, sp∈1..6）')
            c.condition_type = COMPARE_VARIABLES
            c.variable, c.variable2, c.comparison = vk + p, vb + p, LARGER
            c.attribute, c.quantity = -1, -1
            n_cond += 1
            changes.append(Change('s375', 'cond_convert', f'T{t.trigger_id}C{ci}', 'type',
                                  'KR≥1', f'V{vk + p}>V{vb + p}', '擊殺變數化'))

    # ---- 重置觸發：Joan 建立/殺/移除 → V_BASE[p] += 1 ----
    for tid in reset_tids:
        t = trig_by_id(tm, tid)
        if t is None:
            raise BuildError(f'缺裁決：killvar reset T{tid} 不存在')
        types = [getattr(e, 'effect_type', None) for e in t.effects]
        if not {11, 14, 15} <= set(types):
            raise BuildError(f'缺裁決：T{tid} 非 Joan 重置型（效果 {types}）')
        ps = {getattr(c, 'source_player', -1) for c in t.conditions
              if getattr(c, 'condition_type', None) == COMPARE_VARIABLES}
        if len(ps) != 1:
            raise BuildError(f'缺裁決：T{tid} 重置觸發玩家判定異常 {ps}')
        p = ps.pop()
        for ei, e in enumerate(t.effects):
            if getattr(e, 'effect_type', None) in (11, 14, 15):
                neutralize_effect(e)
                changes.append(Change('s375', 'eff_neutralize', f'T{tid}E{ei}', 'effect_type',
                                      str(types[ei]), '0', 'Joan 重置法抽除'))
        t.new_effect.change_variable(quantity=1, operation=ADD, variable=vb + p)
        changes.append(Change('s375', 'eff_add', f'T{tid}', 'change_variable', '',
                              f'V{vb + p}+=1', '領獎基準遞增（等價 KR−1）'))

    # ---- 共用計數迴圈 ----
    loop = tm.add_trigger('擊殺計數迴圈', enabled=True, looping=True)
    for s in range(1, 7):
        loop.new_effect.modify_variable_by_resource(tribute_list=kills_attr, source_player=s,
                                                    operation=SET, variable=vk + s)
    changes.append(Change('s375', 'trigger_add', '擊殺計數迴圈', 'trigger', '',
                          f'T{loop.trigger_id}', f'{n_cond} 條件變數化的計數來源'))
    return changes


class KillVarStep(Step):
    id = 's375'
    title = '擊殺獎勵變數化'
    intro = 'Kill Ratio 條件→比較變數；X升級 Joan 重置→基準遞增；共用擊殺計數迴圈。無 killvar 參數時跳過。'

    def apply(self, ctx):
        params = ctx.spec.params.get('killvar')
        if not params:
            return []
        return apply_killvar(ctx.base.trigger_manager, params)

    def test_guide(self, changes):
        n = sum(1 for c in changes if c.kind == 'cond_convert')
        return (f'擊殺變數化：{n} 個獎勵條件改讀擊殺變數。單人驗：殺一隻野怪領獎一次且不刷屏；'
                '死亡復活後再殺照常領獎（回歸點）。\n陽性對照：Pikeman 區領獎訊息照舊。')


STEP = KillVarStep()

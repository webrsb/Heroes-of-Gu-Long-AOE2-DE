# -*- coding: utf-8 -*-
"""s372 野怪一般獎勵補回（params.mob_rewards；reports/野怪獎勵盤點.md）。

無法無天把三個一般野怪區改成計時道具任務並拿掉一般獎勵，另把兩區的啟動觸發關掉忘了開。
裁決：任務原封不動、一般獎勵依來源數值補回。
  enable_triggers：X獅頭人2 / X魔2 設回啟用（內容與來源一字未改）。
  zones：每位玩家新增「X{key}獎」（KR≥1＋timer 2 → 負進貢閱歷/銀＋啟動 X升級＋訊息）
        與每個區域一支「X{key}獎2」常開啟動器；出口＝停用該區任務獎勵者（排除節流觸發），
        各追加一個停用新獎勵的效果。
必在 s375（KR 條件變數化）之前執行；sp=玩家 → s39 矩陣自動 ×6 槽位。"""
from core.change import Change
from .base import trig_by_id, Step, BuildError

KR_ATTR, STONE, GOLD = 44, 2, 3


def _named(tm, tid, expect_name):
    t = trig_by_id(tm, tid)
    if t is None or (t.name or '') != expect_name:
        raise BuildError(f'缺裁決：T{tid} 名稱「{getattr(t, "name", None)}」≠ 預期「{expect_name}」，'
                         f'基底觸發編號可能位移')
    return t


def apply_mob_rewards(tm, params):
    changes = []
    for ent in params.get('enable_triggers') or []:
        t = _named(tm, int(ent['trigger_id']), ent['name'])
        if t.enabled:
            raise BuildError(f'缺裁決：T{t.trigger_id}「{t.name}」已是啟用，裁決過時')
        t.enabled = 1
        changes.append(Change('s372', 'trigger_field', f'T{t.trigger_id}「{t.name}」', 'enabled',
                              '0', '1', '區域啟動觸發設回啟用（來源即啟用）'))

    upgrade = {int(k): int(v) for k, v in params['upgrade'].items()}
    for p, tid in upgrade.items():
        _named(tm, tid, f'{p}升級')

    deact_by_target = {}
    for t in tm.triggers:
        for e in t.effects:
            if getattr(e, 'effect_type', None) == 9:
                deact_by_target.setdefault(getattr(e, 'trigger_id', -1), []).append(t.trigger_id)

    for z in params['zones']:
        key, xp, silver = z['key'], int(z['xp']), int(z['silver'])
        areas = [tuple(int(v) for v in a) for a in z['areas']]
        quest = {int(k): int(v) for k, v in z['quest_reward'].items()}
        excl_suffix = z.get('exclude_exit_suffix')
        for p in range(1, 7):
            q = _named(tm, quest[p], f'{p}{z["quest_name_suffix"]}')
            if not any(getattr(c, 'condition_type', None) == 8 and getattr(c, 'attribute', -1) == KR_ATTR
                       for c in q.conditions):
                raise BuildError(f'缺裁決：任務獎勵 T{q.trigger_id} 無 KR 條件，非預期型')
            exits = [x for x in deact_by_target.get(q.trigger_id, [])
                     if not (excl_suffix and (trig_by_id(tm, x).name or '') == f'{p}{excl_suffix}')]
            if not exits:
                raise BuildError(f'缺裁決：{key} 區 P{p} 找不到出口（停用 T{q.trigger_id} 者）')

            r = tm.add_trigger(f'{p}{key}獎', enabled=False, looping=False)
            r.new_condition.accumulate_attribute(quantity=1, attribute=KR_ATTR, source_player=p)
            r.new_condition.timer(timer=2)
            r.new_effect.tribute(quantity=-xp, tribute_list=STONE, source_player=p, target_player=0)
            r.new_effect.tribute(quantity=-silver, tribute_list=GOLD, source_player=p, target_player=0)
            r.new_effect.activate_trigger(trigger_id=upgrade[p])
            r.new_effect.send_chat(source_player=p, message=f'<AQUA>最後一擊得到了　{xp}　點江湖閱歷')
            r.new_effect.send_chat(source_player=p, message=f'<GREEN>得到了　{silver}　兩銀')
            changes.append(Change('s372', 'trigger_add', f'{p}{key}獎', 'trigger', '',
                                  f'T{r.trigger_id}', f'一般獎勵 {xp}/{silver}（來源數值）'))
            for i, (x1, y1, x2, y2) in enumerate(areas):
                a = tm.add_trigger(f'{p}{key}獎{i + 2}', enabled=True, looping=True)
                a.new_condition.objects_in_area(quantity=1, source_player=p,
                                                area_x1=x1, area_y1=y1, area_x2=x2, area_y2=y2)
                a.new_effect.activate_trigger(trigger_id=r.trigger_id)
                changes.append(Change('s372', 'trigger_add', f'{p}{key}獎{i + 2}', 'trigger', '',
                                      f'T{a.trigger_id}', f'區 ({x1},{y1})-({x2},{y2}) 常開啟動'))
            for x in exits:
                trig_by_id(tm, x).new_effect.deactivate_trigger(trigger_id=r.trigger_id)
                changes.append(Change('s372', 'eff_add', f'T{x}', 'deactivate', '',
                                      f'→T{r.trigger_id}', f'{key} 區出口追加停用一般獎勵'))
    return changes


class MobRewardStep(Step):
    id = 's372'
    title = '野怪獎勵補回'
    intro = '獅頭人2/魔2 設回啟用；狼窟/石區補回來源一般獎勵（任務不動）。無 mob_rewards 參數時跳過。'

    def apply(self, ctx):
        params = ctx.spec.params.get('mob_rewards')
        if not params:
            return []
        return apply_mob_rewards(ctx.base.trigger_manager, params)

    def test_guide(self, changes):
        return ('野怪獎勵補回：鷹眼偵察兵（獅頭人區）、獅頭魔（魔區）殺了應領獎；'
                '狼窟每殺一狼 16/15、石獅/斬狂區每殺一隻 207/100；碧海藍圖/毀滅之魂任務照舊。\n'
                '陽性對照：Pikeman 區領獎照舊。')


STEP = MobRewardStep()

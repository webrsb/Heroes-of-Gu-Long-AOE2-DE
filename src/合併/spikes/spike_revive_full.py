# -*- coding: utf-8 -*-
"""復活全流程整合 demo：點選選職業 → 10秒自殺 → 從P8同盟帳棚重生（3條命）。
兩職業：騎士A=先換家再卸載（定案順序）；弓兵B=先卸載再換家（對照，A壞掉時的備案）。
每職業 3 條命：展示單位本身=第1命，帳棚預駐 2 隻（Gaia）=第2、3命。命用完出訊息。
用法: python spike_revive_full.py <template> <輸出>"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from AoE2ScenarioParser.scenarios.aoe2_de_scenario import AoE2DEScenario
from AoE2ScenarioParser.datasets.players import PlayerId

KNIGHT, ARCHER, FLAG, TENT = 38, 4, 252, 1097

def main(src, out):
    scn = AoE2DEScenario.from_file(src)
    um, tm = scn.unit_manager, scn.trigger_manager
    cx = scn.map_manager.map_width // 2
    y0 = cx

    def add(player, const, x, yy, **kw):
        return um.add_unit(player=player, unit_const=const, x=x + .5, y=yy + .5, **kw).reference_id

    um.add_unit(player=PlayerId.ONE, unit_const=FLAG, x=cx + .5, y=y0 + .5)
    classes = {}
    for key, const, dx, label in (('A', KNIGHT, -6, '騎士A(先換家再卸載)'),
                                  ('B', ARCHER, +6, '弓兵B(先卸載再換家)')):
        disp = add(PlayerId.GAIA, const, cx + dx, y0)                      # 第1命=展示單位
        tent = add(PlayerId.EIGHT, TENT, cx + dx + (2 if dx > 0 else -2), y0 + 4)
        lives = [disp] + [add(PlayerId.GAIA, const, cx + dx, y0 + 4, garrisoned_in_id=tent)
                          for _ in range(2)]                                # 第2、3命預駐
        classes[key] = dict(tent=tent, lives=lives, label=label)

    def trig(name, enabled=True, timer=None):
        t = tm.add_trigger(name, enabled=enabled, looping=False)
        if timer is not None:
            t.new_condition.timer(timer=timer)
        return t
    def chat(t, m):
        t.new_effect.send_chat(source_player=PlayerId.ONE, message=m)
    def own(t, ref, cur_owner=PlayerId.GAIA):
        t.new_effect.change_ownership(source_player=cur_owner, target_player=PlayerId.ONE,
                                      selected_object_ids=[ref])
    def unload(t, tent_ref):
        t.new_effect.unload(source_player=PlayerId.EIGHT, selected_object_ids=[tent_ref])

    t = trig('開場', timer=0)
    t.new_effect.change_diplomacy(diplomacy=0, source_player=PlayerId.ONE, target_player=PlayerId.EIGHT)
    t.new_effect.change_diplomacy(diplomacy=0, source_player=PlayerId.EIGHT, target_player=PlayerId.ONE)
    for c in classes.values():
        t.new_effect.change_object_name(source_player=PlayerId.EIGHT,
                                        selected_object_ids=[c['tent']], message=c['label'])
    chat(t, '全流程demo: 點選 騎士 或 弓兵 選職業。選定後每10秒自動死一次，共3條命，看帳棚重生')

    for key, c in classes.items():
        L, tent, label = c['lives'], c['tent'], c['label']
        # 自殺鏈（停用，由選角/重生逐條啟動；timer 從啟動起算）
        suicides = []
        for i in range(3):
            s = trig(f'{key}自殺{i+1}', enabled=False, timer=10)
            s.new_effect.kill_object(source_player=PlayerId.ONE, selected_object_ids=[L[i]])
            chat(s, f'{label}: 第{i+1}命 模擬死亡（自殺）')
            suicides.append(s)
        # 選角
        sel = trig(f'{key}選角')
        sel.new_condition.object_selected(unit_object=L[0])
        own(sel, L[0])
        chat(sel, f'你選擇了{label}！第1命就位，10秒後模擬死亡')
        sel.new_effect.activate_trigger(trigger_id=suicides[0].trigger_id)
        # 重生鏈：死第i命 → 放第i+1命
        for i in (0, 1):
            w = trig(f'{key}重生{i+2}')
            w.new_condition.destroy_object(unit_object=L[i])
            if key == 'A':
                own(w, L[i + 1]); unload(w, tent)      # 定案順序：先換家再卸載
            else:
                unload(w, tent); own(w, L[i + 1])      # 對照：先卸載再換家
            chat(w, f'{label}: 復活！第{i+2}命從帳棚出來（剩{1-i}次重生）')
            w.new_effect.activate_trigger(trigger_id=suicides[i + 1].trigger_id)
        # 命用完
        w = trig(f'{key}命盡')
        w.new_condition.destroy_object(unit_object=L[2])
        chat(w, f'{label}: 3條命用完——真死亡')

    tm.legacy_execution_order = True
    scn.write_to_file(out)
    print(f'完成: {out}（觸發 {len(tm.triggers)} 支）')

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])

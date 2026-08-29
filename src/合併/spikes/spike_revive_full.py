# -*- coding: utf-8 -*-
"""復活全流程整合 demo v2：點選選職業 → 10秒自殺 → 從P8同盟帳棚重生（3條命）。
v2 修正：
- 展示單位建檔掛P8、t=0轉Gaia（防Gaia軍事單位開場被自動歸順成1P）
- 重生=換家→傳送到帳棚門口（卸載對跨家組合無效，實測放棄；傳送已證實可從駐軍中拉人）
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
    for key, const, dx, label in (('A', KNIGHT, -6, '騎士A'), ('B', ARCHER, +6, '弓兵B')):
        disp = add(PlayerId.EIGHT, const, cx + dx, y0)     # 展示=第1命，P8→t0轉Gaia
        tx = cx + dx + (2 if dx > 0 else -2)
        tent = add(PlayerId.EIGHT, TENT, tx, y0 + 4)
        lives = [disp] + [add(PlayerId.GAIA, const, tx, y0 + 4, garrisoned_in_id=tent)
                          for _ in range(2)]
        classes[key] = dict(tent=tent, lives=lives, label=label, door=(tx, y0 + 6))
    def trig(name, enabled=True, timer=None):
        t = tm.add_trigger(name, enabled=enabled, looping=False)
        if timer is not None:
            t.new_condition.timer(timer=timer)
        return t
    def chat(t, m):
        t.new_effect.send_chat(source_player=PlayerId.ONE, message=m)

    t = trig('開場', timer=0)
    t.new_effect.change_diplomacy(diplomacy=0, source_player=PlayerId.ONE, target_player=PlayerId.EIGHT)
    t.new_effect.change_diplomacy(diplomacy=0, source_player=PlayerId.EIGHT, target_player=PlayerId.ONE)
    for c in classes.values():
        t.new_effect.change_ownership(source_player=PlayerId.EIGHT, target_player=PlayerId.GAIA,
                                      selected_object_ids=[c['lives'][0]])   # 展示轉Gaia防自動歸順
        t.new_effect.change_object_name(source_player=PlayerId.EIGHT,
                                        selected_object_ids=[c['tent']], message=c['label'] + '重生棚')
    chat(t, 'demo v2: 點選 騎士 或 弓兵 選職業。每10秒自動死一次，3條命，重生於帳棚門口')

    for key, c in classes.items():
        L, label = c['lives'], c['label']
        dx_, dy_ = c['door']
        suicides = []
        for i in range(3):
            s = trig(f'{key}自殺{i+1}', enabled=False, timer=10)
            s.new_effect.kill_object(source_player=PlayerId.ONE, selected_object_ids=[L[i]])
            chat(s, f'{label}: 第{i+1}命 模擬死亡')
            suicides.append(s)
        sel = trig(f'{key}選角')
        sel.new_condition.object_selected(unit_object=L[0])
        sel.new_effect.change_ownership(source_player=PlayerId.GAIA, target_player=PlayerId.ONE,
                                        selected_object_ids=[L[0]])
        chat(sel, f'你選擇了{label}！第1命就位，10秒後模擬死亡')
        sel.new_effect.activate_trigger(trigger_id=suicides[0].trigger_id)
        for i in (0, 1):
            w = trig(f'{key}重生{i+2}')
            w.new_condition.destroy_object(unit_object=L[i])
            w.new_effect.change_ownership(source_player=PlayerId.GAIA, target_player=PlayerId.ONE,
                                          selected_object_ids=[L[i + 1]])          # 先換家
            w.new_effect.teleport_object(source_player=PlayerId.ONE,               # 再傳送出棚
                                         selected_object_ids=[L[i + 1]],
                                         location_x=dx_, location_y=dy_)
            chat(w, f'{label}: 復活！第{i+2}命於帳棚門口（剩{1-i}次重生）')
            w.new_effect.activate_trigger(trigger_id=suicides[i + 1].trigger_id)
        w = trig(f'{key}命盡')
        w.new_condition.destroy_object(unit_object=L[2])
        chat(w, f'{label}: 3條命用完——真死亡')

    tm.legacy_execution_order = True
    scn.write_to_file(out)
    print(f'完成: {out}（觸發 {len(tm.triggers)} 支）')

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])

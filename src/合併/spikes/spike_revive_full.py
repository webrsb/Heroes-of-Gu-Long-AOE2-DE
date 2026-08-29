# -*- coding: utf-8 -*-
"""復活全流程整合 demo v3（定案機制版）：
藏兵艙=隱形物件(1291)，一命一容器；重生=先把備身轉給玩家(駐軍中)→再移除容器彈出。
兵/展示單位一律 P8 建檔→t0 轉 Gaia（無歸順旗標）。
流程: 點選展示單位選職業(=第1命) → 每10秒自殺 → 容器彈出下一命 → 3命用盡訊息。
用法: python spike_revive_full.py <template> <輸出>"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from AoE2ScenarioParser.scenarios.aoe2_de_scenario import AoE2DEScenario
from AoE2ScenarioParser.datasets.players import PlayerId

KNIGHT, ARCHER, FLAG, INVIS = 38, 4, 252, 1291
P0, P1, P8 = PlayerId.GAIA, PlayerId.ONE, PlayerId.EIGHT

def main(src, out):
    scn = AoE2DEScenario.from_file(src)
    um, tm = scn.unit_manager, scn.trigger_manager
    cx = scn.map_manager.map_width // 2
    y0 = cx

    def add(player, const, x, yy, **kw):
        return um.add_unit(player=player, unit_const=const, x=x + .5, y=yy + .5, **kw).reference_id

    um.add_unit(player=P1, unit_const=FLAG, x=cx + .5, y=y0 - 6 + .5)
    classes = {}
    for key, const, dx, label in (('A', KNIGHT, -6, '騎士'), ('B', ARCHER, +6, '弓兵')):
        disp = add(P8, const, cx + dx, y0)                       # 第1命=展示單位
        boxes, lives = [], [disp]
        for i in range(2):                                       # 第2、3命各一個隱形容器
            b = add(P0, INVIS, cx + dx + i + 1, y0 + 3)
            g = add(P8, const, cx + dx + i + 1, y0 + 3, garrisoned_in_id=b)
            boxes.append(b); lives.append(g)
        classes[key] = dict(lives=lives, boxes=boxes, label=label)

    def trig(name, enabled=True, timer=None):
        t = tm.add_trigger(name, enabled=enabled, looping=False)
        if timer is not None:
            t.new_condition.timer(timer=timer)
        return t
    def chat(t, m):
        t.new_effect.send_chat(source_player=P1, message=m)

    t = trig('開場', timer=0)
    for c in classes.values():
        for ref in c['lives']:
            t.new_effect.change_ownership(source_player=P8, target_player=P0, selected_object_ids=[ref])
    chat(t, 'demo v3: 點選 騎士 或 弓兵 選職業。每10秒自動死一次，3條命，備身自隱形容器彈出')

    for key, c in classes.items():
        L, B, label = c['lives'], c['boxes'], c['label']
        suicides = []
        for i in range(3):
            s = trig(f'{key}自殺{i+1}', enabled=False, timer=10)
            s.new_effect.kill_object(source_player=P1, selected_object_ids=[L[i]])
            chat(s, f'{label}: 第{i+1}命 模擬死亡')
            suicides.append(s)
        sel = trig(f'{key}選角')
        sel.new_condition.object_selected(unit_object=L[0])
        sel.new_effect.change_ownership(source_player=P0, target_player=P1, selected_object_ids=[L[0]])
        chat(sel, f'你選擇了{label}！第1命就位，10秒後模擬死亡')
        sel.new_effect.activate_trigger(trigger_id=suicides[0].trigger_id)
        for i in (0, 1):
            w = trig(f'{key}重生{i+2}')
            w.new_condition.destroy_object(unit_object=L[i])
            w.new_effect.change_ownership(source_player=P0, target_player=P1,      # 先轉1P(駐軍中)
                                          selected_object_ids=[L[i + 1]])
            w.new_effect.remove_object(source_player=P0, selected_object_ids=[B[i]])  # 再移除容器
            chat(w, f'{label}: 復活！第{i+2}命於出生點（剩{1-i}次重生）')
            w.new_effect.activate_trigger(trigger_id=suicides[i + 1].trigger_id)
        w = trig(f'{key}命盡')
        w.new_condition.destroy_object(unit_object=L[2])
        chat(w, f'{label}: 3條命用完——真死亡')

    tm.legacy_execution_order = True
    scn.write_to_file(out)
    print(f'完成: {out}（觸發 {len(tm.triggers)} 支）')

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])

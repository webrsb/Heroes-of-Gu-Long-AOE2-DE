# -*- coding: utf-8 -*-
"""B 組 v2：帳棚類建築駐軍測試。四種帳棚＋城堡對照，各配一隻 Gaia 民兵貼牆站，
t=1 下令進駐（≒開場即駐軍）→ t=20 換家 → t=25 傳送拉出。
用法: python spike_revive_b2.py <template> <輸出>"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from AoE2ScenarioParser.scenarios.aoe2_de_scenario import AoE2DEScenario
from AoE2ScenarioParser.datasets.players import PlayerId

MILITIA, FLAG, CASTLE = 74, 252, 82
CANDIDATES = [('帳棚', 1097), ('軍帳', 1196), ('蒙古包', 712), ('小屋', 1082), ('城堡對照', CASTLE)]

def main(src, out):
    scn = AoE2DEScenario.from_file(src)
    um, tm = scn.unit_manager, scn.trigger_manager
    cx = scn.map_manager.map_width // 2
    y = cx - 10

    def add(player, const, x, yy):
        return um.add_unit(player=player, unit_const=const, x=x + .5, y=yy + .5).reference_id

    rows = []   # (label, 建物ref, 民兵ref, x)
    for i, (label, const) in enumerate(CANDIDATES):
        x = cx - 16 + i * 7
        b = add(PlayerId.GAIA, const, x, y)
        g = add(PlayerId.GAIA, MILITIA, x + 1, y + 1)   # 緊貼建築
        rows.append((label, b, g, x))
    F = add(PlayerId.GAIA, FLAG, cx, y + 8)

    t = tm.add_trigger('說明', enabled=True)
    t.new_condition.timer(timer=1)
    t.new_effect.send_chat(source_player=PlayerId.ONE,
                           message='B2: 左起 帳棚/軍帳/蒙古包/小屋/城堡 各一隻民兵，t=1下令進駐')
    for label, b, g, x in rows:
        t.new_effect.change_object_name(source_player=PlayerId.GAIA, selected_object_ids=[b], message=label)
        t.new_effect.task_object(source_player=PlayerId.GAIA, selected_object_ids=[g],
                                 location_x=x, location_y=y)
    t = tm.add_trigger('觀察', enabled=True)
    t.new_condition.timer(timer=8)
    t.new_effect.send_chat(source_player=PlayerId.ONE,
                           message='B2: 現在哪幾隻民兵消失了？消失=該建築可駐軍')
    t = tm.add_trigger('換家', enabled=True)
    t.new_condition.timer(timer=20)
    for label, b, g, x in rows:
        t.new_effect.change_ownership(source_player=PlayerId.GAIA, target_player=PlayerId.ONE,
                                      selected_object_ids=[g])
    t.new_effect.send_chat(source_player=PlayerId.ONE, message='B2: 五隻民兵已轉給你（含駐軍中的）')
    t = tm.add_trigger('拉出', enabled=True)
    t.new_condition.timer(timer=25)
    for label, b, g, x in rows:
        t.new_effect.teleport_object(source_player=PlayerId.ONE, selected_object_ids=[g],
                                     location_x=cx, location_y=y + 8)
    t.new_effect.send_chat(source_player=PlayerId.ONE,
                           message='B2: 旗幟旁出現幾隻？（幾隻=幾種建築全流程成功）')

    tm.legacy_execution_order = True
    scn.write_to_file(out)
    print(f'完成: {out}（觸發 {len(tm.triggers)} 支）')

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])

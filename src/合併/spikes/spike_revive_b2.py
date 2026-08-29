# -*- coding: utf-8 -*-
"""B 組 v3：建檔時直接用 unit.garrisoned_in_id 預駐軍（t=0 就在建築裡，零觸發）。
四種帳棚＋城堡對照，各預駐一隻 Gaia 民兵 → t=20 換家 → t=25 傳送拉出。
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

    rows = []
    for i, (label, const) in enumerate(CANDIDATES):
        x = cx - 16 + i * 7
        b = um.add_unit(player=PlayerId.GAIA, unit_const=const, x=x + .5, y=y + .5)
        g = um.add_unit(player=PlayerId.GAIA, unit_const=MILITIA, x=x + .5, y=y + .5,
                        garrisoned_in_id=b.reference_id)
        rows.append((label, b.reference_id, g.reference_id))
    um.add_unit(player=PlayerId.GAIA, unit_const=FLAG, x=cx + .5, y=y + 8.5)

    t = tm.add_trigger('說明', enabled=True)
    t.new_condition.timer(timer=1)
    t.new_effect.send_chat(source_player=PlayerId.ONE,
                           message='B3: 五棟建築各預駐一隻Gaia民兵(garrisoned_in_id)。'
                                   '現在地面應該一隻民兵都沒有；點建築看駐軍圖示')
    for label, b, g in rows:
        t.new_effect.change_object_name(source_player=PlayerId.GAIA, selected_object_ids=[b], message=label)
    t = tm.add_trigger('換家', enabled=True)
    t.new_condition.timer(timer=20)
    for label, b, g in rows:
        t.new_effect.change_ownership(source_player=PlayerId.GAIA, target_player=PlayerId.ONE,
                                      selected_object_ids=[g])
    t.new_effect.send_chat(source_player=PlayerId.ONE, message='B3: 駐軍中五隻民兵已轉給你')
    t = tm.add_trigger('拉出', enabled=True)
    t.new_condition.timer(timer=25)
    for label, b, g in rows:
        t.new_effect.teleport_object(source_player=PlayerId.ONE, selected_object_ids=[g],
                                     location_x=cx, location_y=y + 8)
    t.new_effect.send_chat(source_player=PlayerId.ONE,
                           message='B3: 旗幟旁出現幾隻？（幾隻=幾種建築預駐軍+拉出全成功）')

    tm.legacy_execution_order = True
    scn.write_to_file(out)
    print(f'完成: {out}（觸發 {len(tm.triggers)} 支）')

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])

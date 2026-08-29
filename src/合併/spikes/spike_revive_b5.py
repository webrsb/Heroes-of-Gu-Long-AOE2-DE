# -*- coding: utf-8 -*-
"""B 組 v5：實戰配置——P8（與玩家同盟）的帳棚，預駐藏兵，死亡時用「卸載」(effect 17)放兵。
帳1: P8帳棚+Gaia民兵預駐；帳2: P8帳棚+P8民兵預駐（兩種駐兵歸屬並排驗）。
流程: t=0 P1↔P8 結盟 → t=20 卸載兩棚 → t=30 換家+傳送到旗幟。
用法: python spike_revive_b5.py <template> <輸出>"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from AoE2ScenarioParser.scenarios.aoe2_de_scenario import AoE2DEScenario
from AoE2ScenarioParser.datasets.players import PlayerId

MILITIA, FLAG, TENT = 74, 252, 1097

def main(src, out):
    scn = AoE2DEScenario.from_file(src)
    um, tm = scn.unit_manager, scn.trigger_manager
    cx = scn.map_manager.map_width // 2
    y = cx - 10
    fx, fy = cx, y + 8

    um.add_unit(player=PlayerId.ONE, unit_const=FLAG, x=fx + .5, y=fy + .5)
    b1 = um.add_unit(player=PlayerId.EIGHT, unit_const=TENT, x=cx - 12 + .5, y=y + .5)
    g1 = um.add_unit(player=PlayerId.GAIA, unit_const=MILITIA, x=cx - 12 + .5, y=y + .5,
                     garrisoned_in_id=b1.reference_id)
    b2 = um.add_unit(player=PlayerId.EIGHT, unit_const=TENT, x=cx - 4 + .5, y=y + .5)
    g2 = um.add_unit(player=PlayerId.EIGHT, unit_const=MILITIA, x=cx - 4 + .5, y=y + .5,
                     garrisoned_in_id=b2.reference_id)

    def trig(name, timer=None):
        t = tm.add_trigger(name, enabled=True, looping=False)
        if timer is not None:
            t.new_condition.timer(timer=timer)
        return t
    def chat(t, m):
        t.new_effect.send_chat(source_player=PlayerId.ONE, message=m)

    t = trig('結盟', None)
    t.new_condition.timer(timer=0)
    t.new_effect.change_diplomacy(diplomacy=0, source_player=PlayerId.ONE, target_player=PlayerId.EIGHT)
    t.new_effect.change_diplomacy(diplomacy=0, source_player=PlayerId.EIGHT, target_player=PlayerId.ONE)
    t.new_effect.change_object_name(source_player=PlayerId.EIGHT, selected_object_ids=[b1.reference_id],
                                    message='帳1(藏Gaia兵)')
    t.new_effect.change_object_name(source_player=PlayerId.EIGHT, selected_object_ids=[b2.reference_id],
                                    message='帳2(藏8P兵)')
    chat(t, 'B5: P1已與P8結盟。兩座P8帳棚各預駐一兵(帳1=Gaia兵, 帳2=8P兵)，地面應無兵')

    # 自動歸屬驗證
    t = tm.add_trigger('驗1', enabled=True, looping=False)
    t.new_condition.own_objects(quantity=1, object_list=MILITIA, source_player=PlayerId.ONE)
    chat(t, '★驗證: P1 已擁有 1 隻民兵')
    t = tm.add_trigger('驗2', enabled=True, looping=False)
    t.new_condition.own_objects(quantity=2, object_list=MILITIA, source_player=PlayerId.ONE)
    chat(t, '★驗證: P1 已擁有 2 隻民兵')

    t = trig('卸載', 20)
    t.new_effect.unload(source_player=PlayerId.EIGHT, selected_object_ids=[b1.reference_id],
                        location_x=cx - 12, location_y=y + 3)
    t.new_effect.unload(source_player=PlayerId.EIGHT, selected_object_ids=[b2.reference_id],
                        location_x=cx - 4, location_y=y + 3)
    chat(t, 't20: 兩棚已下卸載令。回報: 帳1的Gaia兵/帳2的8P兵 各有沒有出來？')

    t = trig('換家傳送', 30)
    t.new_effect.change_ownership(source_player=PlayerId.GAIA, target_player=PlayerId.ONE,
                                  selected_object_ids=[g1.reference_id])
    t.new_effect.change_ownership(source_player=PlayerId.EIGHT, target_player=PlayerId.ONE,
                                  selected_object_ids=[g2.reference_id])
    for g in (g1, g2):
        t.new_effect.teleport_object(source_player=PlayerId.ONE, selected_object_ids=[g.reference_id],
                                     location_x=fx, location_y=fy)
    chat(t, 't30: 換家+傳送。回報: 旗幟旁幾隻? ★驗證訊息時間點?')

    tm.legacy_execution_order = True
    scn.write_to_file(out)
    print(f'完成: {out}（觸發 {len(tm.triggers)} 支）')

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])

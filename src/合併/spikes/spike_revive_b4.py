# -*- coding: utf-8 -*-
"""B 組 v4：診斷「駐軍中的兵拿不出來」卡在哪一步，並排四種拉出手段。
五棟預駐建築：A換家(帳棚) / B殺棚(軍帳) / C移除棚(蒙古包) / D任務拉(小屋) / E城堡換家對照。
OWN_OBJECTS 條件觸發自動回報 P1 是否真的拿到兵（不靠肉眼）。
用法: python spike_revive_b4.py <template> <輸出>"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from AoE2ScenarioParser.scenarios.aoe2_de_scenario import AoE2DEScenario
from AoE2ScenarioParser.datasets.players import PlayerId

MILITIA, FLAG, CASTLE = 74, 252, 82
PLAN = [('A換家帳棚', 1097), ('B殺棚軍帳', 1196), ('C移除蒙古包', 712), ('D任務小屋', 1082), ('E城堡換家', CASTLE)]

def main(src, out):
    scn = AoE2DEScenario.from_file(src)
    um, tm = scn.unit_manager, scn.trigger_manager
    cx = scn.map_manager.map_width // 2
    y = cx - 10
    fx, fy = cx, y + 8

    um.add_unit(player=PlayerId.ONE, unit_const=FLAG, x=fx + .5, y=fy + .5)  # P1有物防判負,兼傳送地標
    R = {}
    for i, (label, const) in enumerate(PLAN):
        x = cx - 16 + i * 7
        b = um.add_unit(player=PlayerId.GAIA, unit_const=const, x=x + .5, y=y + .5)
        g = um.add_unit(player=PlayerId.GAIA, unit_const=MILITIA, x=x + .5, y=y + .5,
                        garrisoned_in_id=b.reference_id)
        R[label[0]] = (b.reference_id, g.reference_id)

    def trig(name, timer=None):
        t = tm.add_trigger(name, enabled=True, looping=False)
        if timer is not None:
            t.new_condition.timer(timer=timer)
        return t
    def chat(t, m):
        t.new_effect.send_chat(source_player=PlayerId.ONE, message=m)
    def own_check(name, qty, msg):
        t = tm.add_trigger(name, enabled=True, looping=False)
        t.new_condition.own_objects(quantity=qty, object_list=MILITIA, source_player=PlayerId.ONE)
        chat(t, msg)

    t = trig('說明', 1)
    chat(t, 'B4: 左起 A換家/B殺棚/C移除/D任務/E城堡，各預駐一隻Gaia民兵')
    for label, const in PLAN:
        t.new_effect.change_object_name(source_player=PlayerId.GAIA,
                                        selected_object_ids=[R[label[0]][0]], message=label)

    # 自動歸屬偵測（一掛好就待命，P1拿到第1/2隻民兵時各報一次）
    own_check('驗1', 1, '★驗證: P1 已擁有 1 隻民兵（駐軍中換家其實有效）')
    own_check('驗2', 2, '★驗證: P1 已擁有 2 隻民兵')

    t = trig('A換家_E城堡換家', 20)
    for k in ('A', 'E'):
        t.new_effect.change_ownership(source_player=PlayerId.GAIA, target_player=PlayerId.ONE,
                                      selected_object_ids=[R[k][1]])
    chat(t, 't20: A帳棚與E城堡內的民兵下了換家令。看★驗證訊息有沒有出現')
    t = trig('B殺棚', 30)
    t.new_effect.kill_object(source_player=PlayerId.GAIA, selected_object_ids=[R['B'][0]])
    chat(t, 't30: 殺B軍帳——民兵有沒有彈出來站在原地？')
    t = trig('C移除棚', 35)
    t.new_effect.remove_object(source_player=PlayerId.GAIA, selected_object_ids=[R['C'][0]])
    chat(t, 't35: 移除C蒙古包——民兵是彈出還是跟著消失？')
    t = trig('D任務拉', 40)
    t.new_effect.task_object(source_player=PlayerId.GAIA, selected_object_ids=[R['D'][1]],
                             location_x=fx, location_y=fy)
    chat(t, 't40: 對D小屋內民兵下走路令——有沒有自己走出來？')
    t = trig('總拉出', 45)
    for k in 'ABCDE':
        t.new_effect.change_ownership(source_player=PlayerId.GAIA, target_player=PlayerId.ONE,
                                      selected_object_ids=[R[k][1]])
        t.new_effect.teleport_object(source_player=PlayerId.ONE, selected_object_ids=[R[k][1]],
                                     location_x=fx, location_y=fy)
    chat(t, 't45: 全員換家+傳送到旗幟。回報: 旗幟旁幾隻? ★驗證何時出現? B彈出/C消失/D走出?')

    tm.legacy_execution_order = True
    scn.write_to_file(out)
    print(f'完成: {out}（觸發 {len(tm.triggers)} 支）')

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])

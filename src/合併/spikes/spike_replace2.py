# -*- coding: utf-8 -*-
"""REPLACE_OBJECT 條件側驗證（裁決代理爭議①）：替換後三種條件沿舊 ref 是否繼續追蹤。
C1 BRING_OBJECT_TO_OBJECT（帶到物件——暗刁/收馬型）
C2 BRING_OBJECT_TO_AREA（帶到區域——技能觸發主力）
C3 OBJECT_HAS_TARGET（有目標——攻擊偵測技能）
對照：未替換單位同三條件。
用法: python spike_replace2.py <template> <輸出>"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from AoE2ScenarioParser.scenarios.aoe2_de_scenario import AoE2DEScenario
from AoE2ScenarioParser.datasets.players import PlayerId

MILITIA, KNIGHT, FLAG, KING = 74, 38, 252, 434
P0, P1, P8 = PlayerId.GAIA, PlayerId.ONE, PlayerId.EIGHT


def main(src, out):
    scn = AoE2DEScenario.from_file(src)
    um, tm = scn.unit_manager, scn.trigger_manager
    cx = scn.map_manager.map_width // 2

    def add(player, const, x, y):
        return um.add_unit(player=player, unit_const=const, x=x + .5, y=y + .5).reference_id

    X = add(P1, MILITIA, cx - 6, cx)          # t=5 被替換成騎士
    Z = add(P1, MILITIA, cx - 4, cx)          # 對照（不替換）
    NPC = add(P0, KING, cx + 6, cx)           # 帶到物件目標
    add(P0, FLAG, cx + 6, cx - 4)             # 帶到區域地標（區: cx+5..7, cx-5..-3）
    TGT = add(P8, MILITIA, cx + 6, cx + 4)    # 攻擊目標（P8 敵對）

    def watch(name, msg):
        t = tm.add_trigger(name, enabled=True, looping=False)
        t.new_effect.send_chat(source_player=P1, message=msg)
        return t

    t = watch('C1X', '★C1: 替換後帶到物件仍追蹤（騎士走到國王旁出現=PASS）')
    t.new_condition.bring_object_to_object(unit_object=X, next_object=NPC)
    t = watch('C1Z', 'C1對照: 未替換民兵帶到物件正常')
    t.new_condition.bring_object_to_object(unit_object=Z, next_object=NPC)
    t = watch('C2X', '★C2: 替換後帶到區域仍追蹤（騎士走進旗區出現=PASS）')
    t.new_condition.bring_object_to_area(unit_object=X, area_x1=cx + 5, area_y1=cx - 5,
                                         area_x2=cx + 7, area_y2=cx - 3)
    t = watch('C2Z', 'C2對照: 未替換民兵帶到區域正常')
    t.new_condition.bring_object_to_area(unit_object=Z, area_x1=cx + 5, area_y1=cx - 5,
                                         area_x2=cx + 7, area_y2=cx - 3)
    t = watch('C3X', '★C3: 替換後有目標仍追蹤（命令騎士攻擊敵民兵時出現=PASS）')
    t.new_condition.object_has_target(unit_object=X, next_object=TGT)
    t = watch('C3Z', 'C3對照: 未替換民兵攻擊偵測正常')
    t.new_condition.object_has_target(unit_object=Z, next_object=TGT)

    t = tm.add_trigger('替換', enabled=True, looping=False)
    t.new_condition.timer(timer=5)
    t.new_effect.replace_object(selected_object_ids=[X], object_list_unit_id_2=KNIGHT,
                                source_player=P1, target_player=P1)
    t.new_effect.send_chat(source_player=P1,
                           message='t5: 左民兵已變騎士。指揮它: 走到國王旁→旗區→攻擊敵民兵；'
                                   '再用對照民兵重做一輪。三組★訊息各自出現與否即結果')

    scn.option_manager.legacy_execution_order = True
    scn.write_to_file(out)
    print(f'完成: {out}（觸發 {len(tm.triggers)} 支）')


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])

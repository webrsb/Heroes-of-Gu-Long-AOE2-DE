# -*- coding: utf-8 -*-
"""駐軍中替換驗證（§七之三 v4 備身連換前提）：
容器內 Gaia 民兵被 REPLACE 成騎士 → 彈出時是不是騎士、血量/駐軍狀態是否正常。
對照：另一容器民兵不替換、地面民兵替換（已證）。
用法: python spike_garrison_replace.py <template> <輸出>"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from AoE2ScenarioParser.scenarios.aoe2_de_scenario import AoE2DEScenario
from AoE2ScenarioParser.datasets.players import PlayerId

MILITIA, KNIGHT, INVIS, FLAG = 74, 38, 1291, 252
P0, P1, P8 = PlayerId.GAIA, PlayerId.ONE, PlayerId.EIGHT


def main(src, out):
    scn = AoE2DEScenario.from_file(src)
    um, tm = scn.unit_manager, scn.trigger_manager
    cx = scn.map_manager.map_width // 2

    def add(player, const, x, y, **kw):
        return um.add_unit(player=player, unit_const=const, x=x + .5, y=y + .5, **kw).reference_id

    B1 = add(P0, INVIS, cx - 4, cx)
    G1 = add(P8, MILITIA, cx - 4, cx, garrisoned_in_id=B1)      # 替換目標
    B2 = add(P0, INVIS, cx, cx)
    G2 = add(P8, MILITIA, cx, cx, garrisoned_in_id=B2)          # 對照不替換
    GD = add(P8, MILITIA, cx + 4, cx)                           # 地面對照（替換已證）
    add(P0, FLAG, cx - 4, cx + 4)

    def trig(name, timer):
        t = tm.add_trigger(name, enabled=True, looping=False)
        t.new_condition.timer(timer=timer)
        return t

    def chat(t, m):
        t.new_effect.send_chat(source_player=P1, message=m)

    t = trig('轉Gaia', 0)
    for g in (G1, G2, GD):
        t.new_effect.change_ownership(source_player=P8, target_player=P0, selected_object_ids=[g])
    chat(t, '駐軍替換測試: 兩容器各駐1兵+地面1兵。t=5 替換容器1與地面兵為騎士')
    t = trig('替換', 5)
    for g in (G1, GD):
        t.new_effect.replace_object(selected_object_ids=[g], object_list_unit_id_2=KNIGHT,
                                    source_player=P0, target_player=P0)
    chat(t, 't5: 已對容器1駐兵與地面兵下替換令（地面應立刻變騎士=陽性對照）')
    t = trig('放兵', 15)
    for g, b in ((G1, B1), (G2, B2)):
        t.new_effect.change_ownership(source_player=P0, target_player=P1, selected_object_ids=[g])
        t.new_effect.remove_object(source_player=P0, selected_object_ids=[b])
    t.new_effect.change_ownership(source_player=P0, target_player=P1, selected_object_ids=[GD])
    chat(t, 't15: 兩容器已拆、三兵轉你。回報: 容器1彈出的是騎士還是民兵? 容器2=民兵(對照)? 地面=騎士?')

    scn.option_manager.legacy_execution_order = True
    scn.write_to_file(out)
    print(f'完成: {out}（觸發 {len(tm.triggers)} 支）')


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])

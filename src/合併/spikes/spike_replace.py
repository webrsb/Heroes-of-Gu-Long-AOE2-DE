# -*- coding: utf-8 -*-
"""REPLACE_OBJECT 語意驗證（馬系統遷移候選，spec §七之三）：
R1 替換是否觸發 DESTROY 條件（不觸發＝死亡監視不用動）
R2 替換後 reference_id 是否延續（延續＝全部 ref 接線在馬形態照常工作）
R3 血量/效果通道是否照舊（對舊 ref 灌血）
對照：另一隻被 kill 的兵其 destroy watch 應正常觸發。
用法: python spike_replace.py <template> <輸出>"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from AoE2ScenarioParser.scenarios.aoe2_de_scenario import AoE2DEScenario
from AoE2ScenarioParser.datasets.players import PlayerId

MILITIA, KNIGHT, FLAG = 74, 38, 252
P0, P1 = PlayerId.GAIA, PlayerId.ONE


def main(src, out):
    scn = AoE2DEScenario.from_file(src)
    um, tm = scn.unit_manager, scn.trigger_manager
    cx = scn.map_manager.map_width // 2

    def add(player, const, x, y):
        return um.add_unit(player=player, unit_const=const, x=x + .5, y=y + .5).reference_id

    X = add(P1, MILITIA, cx - 4, cx)
    Y = add(P1, MILITIA, cx - 2, cx)
    add(P0, FLAG, cx, cx)

    def trig(name, timer=None):
        t = tm.add_trigger(name, enabled=True, looping=False)
        if timer is not None:
            t.new_condition.timer(timer=timer)
        return t

    def chat(t, m):
        t.new_effect.send_chat(source_player=P1, message=m)

    t = trig('說明', 1)
    chat(t, '替換驗證: 左=X(將被替換成騎士) 右=Y(對照,將被擊殺)')

    t = tm.add_trigger('R1監視X', enabled=True, looping=False)
    t.new_condition.destroy_object(unit_object=X)
    chat(t, '★R1: 替換觸發了摧毀條件（此訊息若在t10~12間出現=替換算死亡=壞消息）')
    t = tm.add_trigger('對照監視Y', enabled=True, looping=False)
    t.new_condition.destroy_object(unit_object=Y)
    chat(t, 'R對照: Y被殺觸發摧毀正常（應在t12後出現）')

    t = trig('R替換', 10)
    t.new_effect.replace_object(selected_object_ids=[X], object_list_unit_id_2=KNIGHT,
                                source_player=P1, target_player=P1)
    chat(t, 't10: 已把X替換成騎士——觀察★R1有沒有跳')
    t = trig('R殺Y', 12)
    t.new_effect.kill_object(source_player=P1, selected_object_ids=[Y])
    chat(t, 't12: 已擊殺Y（對照）')
    t = trig('R2改名', 15)
    t.new_effect.change_object_name(source_player=-1, selected_object_ids=[X],
                                    message='R_ref延續OK')
    chat(t, 't15: 對「舊ref」下改名令——點騎士看名字是否=R_ref延續OK（是=ref延續）')
    t = trig('R3灌血', 20)
    t.new_effect.damage_object(source_player=-1, selected_object_ids=[X], quantity=-55)
    chat(t, 't20: 對舊ref灌血55——點騎士看血量是否超上限（是=效果通道照舊）')

    scn.option_manager.legacy_execution_order = True
    scn.write_to_file(out)
    print(f'完成: {out}（觸發 {len(tm.triggers)} 支）')


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])

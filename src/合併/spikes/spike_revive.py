# -*- coding: utf-8 -*-
"""復活/選職業 最小實現 spike 注入器。
用法: python spike_revive.py <空白template.aoe2scenario> <輸出.aoe2scenario>
六組測試（A~E 遊戲內驗證、各含陽性對照），詳見同目錄 spike_revive_指引.md。
絕不覆寫輸入檔；輸出為新檔。"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from AoE2ScenarioParser.scenarios.aoe2_de_scenario import AoE2DEScenario
from AoE2ScenarioParser.datasets.players import PlayerId

MILITIA, CASTLE, FLAG = 74, 82, 252   # 民兵/城堡/旗幟A

def chat(t, text):
    t.new_effect.send_chat(source_player=PlayerId.ONE, message=text)

def main(src, out):
    scn = AoE2DEScenario.from_file(src)
    um, tm = scn.unit_manager, scn.trigger_manager
    W = scn.map_manager.map_width
    cx = W // 2

    def add(player, const, x, y):
        u = um.add_unit(player=player, unit_const=const, x=x + .5, y=y + .5)
        return u.reference_id

    # ---- 佈點（以地圖中央為基準，各組隔 6 格）----
    y0 = cx - 15
    # A 組: 死ref混活ref
    A1 = add(PlayerId.ONE, MILITIA, cx - 8, y0)
    A2 = add(PlayerId.ONE, MILITIA, cx - 6, y0)
    A3 = add(PlayerId.ONE, MILITIA, cx - 4, y0)          # 對照
    # B 組: Gaia+駐軍+換家+傳送
    CA = add(PlayerId.GAIA, CASTLE, cx - 8, y0 + 8)
    G1 = add(PlayerId.GAIA, MILITIA, cx - 2, y0 + 8)
    G2 = add(PlayerId.GAIA, MILITIA, cx, y0 + 8)          # 不駐軍對照
    FB = add(PlayerId.GAIA, FLAG, cx + 6, y0 + 8)         # 傳送目的旗
    # C 組: sp=-1 + ref清單（每型一隻 + sp=1 對照一隻）
    Cs = {k: (add(PlayerId.ONE, MILITIA, cx - 8 + 2 * i, y0 + 16),
              add(PlayerId.ONE, MILITIA, cx - 8 + 2 * i, y0 + 18))
          for i, k in enumerate(('名', '傷', '血', '攻', '走'))}
    CF = add(PlayerId.GAIA, FLAG, cx + 6, y0 + 16)        # C走 目的旗
    # D 組: 點選選角
    D1 = add(PlayerId.GAIA, MILITIA, cx - 8, y0 + 24)     # 點我(條件sp=1)
    D1b = add(PlayerId.GAIA, MILITIA, cx - 5, y0 + 24)    # 點我(條件sp=-1)
    D2 = add(PlayerId.ONE, MILITIA, cx - 2, y0 + 24)      # 對照: 點自家
    # E 組: OR 條件
    E1 = add(PlayerId.ONE, MILITIA, cx - 8, y0 + 30)
    E2 = add(PlayerId.ONE, MILITIA, cx - 6, y0 + 30)

    def trig(name, timer=None):
        t = tm.add_trigger(name, enabled=True, looping=False)
        if timer is not None:
            t.new_condition.timer(timer=timer)
        return t

    # ---- 開場說明 ----
    t = trig('說明', 1)
    chat(t, 'SPIKE 測試開始：A混列/B藏兵/C玩家-1/D點選/E或條件，照指引觀察')
    # A
    t = trig('A殺A1', 5)
    t.new_effect.kill_object(source_player=PlayerId.ONE, selected_object_ids=[A1])
    chat(t, 'A: A1已擊殺(左1)。10秒時對[死A1,活A2]清單改名')
    t = trig('A混列', 10)
    t.new_effect.change_object_name(source_player=PlayerId.ONE, selected_object_ids=[A1, A2], message='A混列OK')
    t.new_effect.change_object_name(source_player=PlayerId.ONE, selected_object_ids=[A3], message='A對照OK')
    chat(t, 'A: 請點 A2(左2) 看名字是否=A混列OK；A3(左3)=A對照OK')
    # B
    t = trig('B駐軍', 3)
    t.new_effect.task_object(source_player=PlayerId.GAIA, selected_object_ids=[G1],
                             location_x=int(CA and (cx - 8)), location_y=y0 + 8)
    chat(t, 'B: 已命令Gaia民兵G1進駐城堡，請觀察它是否消失進駐')
    t = trig('B換家', 20)
    for r in (G1, G2):
        t.new_effect.change_ownership(source_player=PlayerId.GAIA, target_player=PlayerId.ONE, selected_object_ids=[r])
    chat(t, 'B: G1(駐軍中?)與G2(站著)已轉給你')
    t = trig('B傳送', 25)
    for r in (G1, G2):
        t.new_effect.teleport_object(source_player=PlayerId.ONE, selected_object_ids=[r],
                                     location_x=cx + 6, location_y=y0 + 8)
    chat(t, 'B: G1/G2 應出現在旗幟旁且可操作（G1若沒出來=駐軍中不可傳送）')
    # C
    t = trig('C玩家負一', 15)
    ne = t.new_effect
    ne.change_object_name(source_player=-1, selected_object_ids=[Cs['名'][0]], message='C名OK')
    ne.damage_object(source_player=-1, selected_object_ids=[Cs['傷'][0]], quantity=20)
    ne.change_object_hp(source_player=-1, selected_object_ids=[Cs['血'][0]], quantity=100, operation=2)
    ne.change_object_attack(source_player=-1, selected_object_ids=[Cs['攻'][0]], armour_attack_quantity=50, armour_attack_class=4, operation=2)
    ne.task_object(source_player=-1, selected_object_ids=[Cs['走'][0]], location_x=cx + 6, location_y=y0 + 16)
    # sp=1 陽性對照（第二排）
    ne.change_object_name(source_player=PlayerId.ONE, selected_object_ids=[Cs['名'][1]], message='C名對照OK')
    ne.damage_object(source_player=PlayerId.ONE, selected_object_ids=[Cs['傷'][1]], quantity=20)
    ne.change_object_hp(source_player=PlayerId.ONE, selected_object_ids=[Cs['血'][1]], quantity=100, operation=2)
    ne.change_object_attack(source_player=PlayerId.ONE, selected_object_ids=[Cs['攻'][1]], armour_attack_quantity=50, armour_attack_class=4, operation=2)
    ne.task_object(source_player=PlayerId.ONE, selected_object_ids=[Cs['走'][1]], location_x=cx + 6, location_y=y0 + 18)
    chat(t, 'C: 第三區兩排各5隻：上排sp=-1 下排sp=1對照。逐隻比對名/血/攻/走路')
    # D
    t = tm.add_trigger('D點選sp1', enabled=True, looping=False)
    t.new_condition.object_selected(unit_object=D1)
    t.new_effect.change_ownership(source_player=PlayerId.GAIA, target_player=PlayerId.ONE, selected_object_ids=[D1])
    chat(t, 'D: 選角OK(sp=1)——D1已轉給你')
    t = tm.add_trigger('D點選sp負1', enabled=True, looping=False)
    t.new_condition.object_selected(unit_object=D1b)  # 單人版條件無選取者欄位，sp維度留給多人版驗
    t.new_effect.change_ownership(source_player=PlayerId.GAIA, target_player=PlayerId.ONE, selected_object_ids=[D1b])
    chat(t, 'D: 選角OK(sp=-1)——D1b已轉給你')
    t = tm.add_trigger('D對照', enabled=True, looping=False)
    t.new_condition.object_selected(unit_object=D2)
    chat(t, 'D對照: 點自家單位條件有效')
    # E
    t = tm.add_trigger('E或條件', enabled=True, looping=False)
    t.new_condition.destroy_object(unit_object=E1)
    t.new_condition.or_()
    t.new_condition.destroy_object(unit_object=E2)
    chat(t, 'E: OR條件觸發（E2還活著就出現=正確）')
    t = tm.add_trigger('E且對照', enabled=True, looping=False)
    t.new_condition.destroy_object(unit_object=E1)
    t.new_condition.destroy_object(unit_object=E2)
    chat(t, 'E異常: AND也觸發了（E2活著不該出現）')
    t = trig('E殺E1', 30)
    t.new_effect.kill_object(source_player=PlayerId.ONE, selected_object_ids=[E1])
    chat(t, 'E: 已擊殺E1（E2保留），觀察OR訊息是否出現')

    tm.legacy_execution_order = True
    scn.write_to_file(out)
    print(f'完成: {out}（觸發 {len(tm.triggers)} 支）')

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])

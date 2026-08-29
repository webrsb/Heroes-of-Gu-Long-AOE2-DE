# -*- coding: utf-8 -*-
"""六組最終驗證檔（Phase 0 閘門，plan v2 Task 1）。
A OR混排鑑別 / B P8點選 / B2 多人條件單機 / C 屬性修改SET+DIVIDE /
D 駐軍吃效果 / E 移除vs摧毀 / F 駐軍算不算區域物件。各組含陽性對照。
用法: python spike_final2.py <template> <輸出>"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from AoE2ScenarioParser.scenarios.aoe2_de_scenario import AoE2DEScenario
from AoE2ScenarioParser.datasets.players import PlayerId
from AoE2ScenarioParser.datasets.trigger_lists import ObjectAttribute, Operation

MILITIA, SPEARMAN, FLAG, INVIS, KNIGHT = 74, 93, 252, 1291, 38
P0, P1, P8 = PlayerId.GAIA, PlayerId.ONE, PlayerId.EIGHT


def main(src, out):
    scn = AoE2DEScenario.from_file(src)
    um, tm = scn.unit_manager, scn.trigger_manager
    cx = scn.map_manager.map_width // 2
    y0 = cx - 18

    def add(player, const, x, yy, **kw):
        return um.add_unit(player=player, unit_const=const, x=x + .5, y=yy + .5, **kw).reference_id

    def trig(name, timer=None, enabled=True, looping=False):
        t = tm.add_trigger(name, enabled=enabled, looping=looping)
        if timer is not None:
            t.new_condition.timer(timer=timer)
        return t

    def chat(t, m):
        t.new_effect.send_chat(source_player=P1, message=m)

    # ================= A 組: OR 混排鑑別 =================
    AX = add(P1, MILITIA, cx - 10, y0)
    AY = add(P1, MILITIA, cx - 8, y0)
    AM = add(P1, MILITIA, cx - 6, y0)          # 走進旗區用
    add(P0, FLAG, cx, y0)                      # 旗區地標 (zone: cx-1..cx+1, y0-1..y0+1)
    t = tm.add_trigger('A混排', enabled=True, looping=False)
    t.new_condition.objects_in_area(quantity=1, source_player=P1, object_list=MILITIA,
                                    area_x1=cx - 1, area_y1=y0 - 1, area_x2=cx + 1, area_y2=y0 + 1)
    t.new_condition.destroy_object(unit_object=AX)
    t.new_condition.or_()
    t.new_condition.destroy_object(unit_object=AY)
    chat(t, '★A混排觸發了——出現時間點決定 PASS/FAIL（t25 後=PASS，t15~25 間=FAIL）')
    t = tm.add_trigger('A純OR對照', enabled=True, looping=False)
    t.new_condition.destroy_object(unit_object=AX)
    t.new_condition.or_()
    t.new_condition.destroy_object(unit_object=AY)
    chat(t, 'A對照: 純OR已觸發（應在 t=10 出現）')
    t = tm.add_trigger('A純AND對照', enabled=True, looping=False)
    t.new_condition.destroy_object(unit_object=AX)
    t.new_condition.destroy_object(unit_object=AY)
    chat(t, 'A對照: 純AND已觸發（應在 t=15 出現）')
    t = trig('A殺X', 10)
    t.new_effect.kill_object(source_player=P1, selected_object_ids=[AX])
    chat(t, 't10: 殺X。此時「A混排」不應出現')
    t = trig('A殺Y', 15)
    t.new_effect.kill_object(source_player=P1, selected_object_ids=[AY])
    chat(t, 't15: 殺Y（兵仍在旗區外）。若接下來「A混排」出現＝OR分組錯誤=FAIL')
    t = trig('A進區', 25)
    t.new_effect.task_object(source_player=P1, selected_object_ids=[AM], location_x=cx, location_y=y0)
    chat(t, 't25: 兵走進旗區。之後「A混排」出現＝分組正確=PASS')

    # ================= B / B2 組: P8 點選 =================
    B1 = add(P8, KNIGHT, cx - 10, y0 + 6)
    B2u = add(P8, KNIGHT, cx - 7, y0 + 6)
    BG = add(P8, KNIGHT, cx - 4, y0 + 6)       # t0 轉 Gaia 對照
    t = tm.add_trigger('B_P8點選', enabled=True, looping=False)
    t.new_condition.object_selected(unit_object=B1)
    chat(t, '★B: P8單位點選觸發 OK')
    t = tm.add_trigger('B2_多人條件', enabled=True, looping=False)
    t.new_condition.object_selected_multiplayer(unit_object=B2u, source_player=P1)
    chat(t, '★B2: OBJECT_SELECTED_MULTIPLAYER 單機觸發 OK')
    t = tm.add_trigger('B對照_Gaia點選', enabled=True, looping=False)
    t.new_condition.object_selected(unit_object=BG)
    chat(t, 'B對照: Gaia單位點選 OK（已證機制，此為對照）')

    # ================= C 組: 屬性修改 SET+DIVIDE =================
    C1 = add(P1, SPEARMAN, cx - 10, y0 + 12)
    add(P0, SPEARMAN, cx - 7, y0 + 12)         # 對照: Gaia 長槍兵原值(HP45/攻3)
    t = trig('C屬性', 5)
    ne = t.new_effect
    ne.modify_attribute(quantity=75, object_list_unit_id=SPEARMAN, source_player=P1,
                        operation=Operation.SET, object_attributes=ObjectAttribute.HIT_POINTS)
    ne.modify_attribute(armour_attack_quantity=10, armour_attack_class=4,
                        object_list_unit_id=SPEARMAN, source_player=P1,
                        operation=Operation.SET, object_attributes=ObjectAttribute.ATTACK)
    ne.modify_attribute(quantity=88, object_list_unit_id=SPEARMAN, source_player=P1,
                        operation=Operation.SET, object_attributes=ObjectAttribute.MOVEMENT_SPEED)
    ne.modify_attribute(quantity=100, object_list_unit_id=SPEARMAN, source_player=P1,
                        operation=Operation.DIVIDE, object_attributes=ObjectAttribute.MOVEMENT_SPEED)
    ne.modify_attribute(quantity=3, object_list_unit_id=SPEARMAN, source_player=P1,
                        operation=Operation.SET, object_attributes=ObjectAttribute.ATTACK_RELOAD_TIME)
    ne.modify_attribute(quantity=2, object_list_unit_id=SPEARMAN, source_player=P1,
                        operation=Operation.DIVIDE, object_attributes=ObjectAttribute.ATTACK_RELOAD_TIME)
    chat(t, 't5 C: 你的長槍兵已改 HP75/攻10/速0.88/攻速1.5。點選看 tooltip，與旁邊Gaia長槍兵(45/3)比')

    # ================= D 組: 駐軍吃效果 =================
    DBOX = add(P0, INVIS, cx + 6, y0)
    D = [add(P8, MILITIA, cx + 6, y0, garrisoned_in_id=DBOX) for _ in range(4)]
    DG = [add(P8, MILITIA, cx + 10 + i * 2, y0) for i in range(4)]   # 地面對照
    t = trig('D轉Gaia', 0)
    for r in D + DG:
        t.new_effect.change_ownership(source_player=P8, target_player=P0, selected_object_ids=[r])
    t = trig('D施效', 5)
    ne = t.new_effect
    ne.change_object_name(source_player=-1, selected_object_ids=[D[0]], message='D改名OK')
    ne.change_object_attack(source_player=-1, selected_object_ids=[D[1]],
                            armour_attack_quantity=50, armour_attack_class=4, operation=2)
    ne.change_object_hp(source_player=-1, selected_object_ids=[D[2]], quantity=100, operation=2)
    ne.damage_object(source_player=-1, selected_object_ids=[D[3]], quantity=-60)
    ne.change_object_name(source_player=-1, selected_object_ids=[DG[0]], message='D地面對照OK')
    ne.change_object_attack(source_player=-1, selected_object_ids=[DG[1]],
                            armour_attack_quantity=50, armour_attack_class=4, operation=2)
    ne.change_object_hp(source_player=-1, selected_object_ids=[DG[2]], quantity=100, operation=2)
    ne.damage_object(source_player=-1, selected_object_ids=[DG[3]], quantity=-60)
    chat(t, 't5 D: 已對容器內4隻與地面4隻施改名/加攻/加血/灌血')
    t = trig('D放兵', 15)
    for r in D:
        t.new_effect.change_ownership(source_player=P0, target_player=P1, selected_object_ids=[r])
    t.new_effect.remove_object(source_player=P0, selected_object_ids=[DBOX])
    chat(t, 't15 D: 容器兵已放出轉你。逐隻驗: 名=D改名OK / 攻4+50 / HP上限140 / 血100超上限40')

    # ================= E 組: 移除 vs 摧毀 =================
    EX = add(P1, MILITIA, cx + 6, y0 + 6)
    EY = add(P1, MILITIA, cx + 8, y0 + 6)
    t = tm.add_trigger('E移除監視', enabled=True, looping=False)
    t.new_condition.destroy_object(unit_object=EX)
    chat(t, '★E: REMOVE滿足DESTROY（此訊息在t10後出現=移除算死亡）')
    t = tm.add_trigger('E對照監視', enabled=True, looping=False)
    t.new_condition.destroy_object(unit_object=EY)
    chat(t, 'E對照: KILL觸發DESTROY正常（應在t12後出現）')
    t = trig('E移除', 10)
    t.new_effect.remove_object(source_player=P1, selected_object_ids=[EX])
    chat(t, 't10 E: 已移除EX（無屍體消失）')
    t = trig('E擊殺', 12)
    t.new_effect.kill_object(source_player=P1, selected_object_ids=[EY])
    chat(t, 't12 E: 已擊殺EY（對照）')

    # ================= F 組: 駐軍算不算區域物件 =================
    fx, fy = cx + 6, y0 + 12
    FBOX = add(P0, INVIS, fx, fy)
    FU = add(P8, MILITIA, fx, fy, garrisoned_in_id=FBOX)
    add(P0, FLAG, fx + 1, fy)
    gx = fx + 6
    FG = add(P8, MILITIA, gx, fy)              # 地面對照
    add(P0, FLAG, gx + 1, fy)
    t = trig('F轉Gaia', 0)
    for r in (FU, FG):
        t.new_effect.change_ownership(source_player=P8, target_player=P0, selected_object_ids=[r])
    t = tm.add_trigger('F駐軍區域', enabled=True, looping=False)
    t.new_condition.timer(timer=3)
    t.new_condition.objects_in_area(quantity=1, source_player=P0, object_list=MILITIA,
                                    area_x1=fx - 1, area_y1=fy - 1, area_x2=fx + 1, area_y2=fy + 1)
    chat(t, '★F: 駐軍中單位計入區域條件（左旗區）')
    t = tm.add_trigger('F對照', enabled=True, looping=False)
    t.new_condition.timer(timer=3)
    t.new_condition.objects_in_area(quantity=1, source_player=P0, object_list=MILITIA,
                                    area_x1=gx - 1, area_y1=fy - 1, area_x2=gx + 1, area_y2=fy + 1)
    chat(t, 'F對照: 地面單位計入區域條件（右旗區）')

    # ================= 總說明 =================
    t = trig('說明', 1)
    t.new_effect.change_diplomacy(diplomacy=0, source_player=P1, target_player=P8)
    t.new_effect.change_diplomacy(diplomacy=0, source_player=P8, target_player=P1)
    chat(t, '六項驗證: A看訊息時間點 / B,B2點選兩隻P8騎士+Gaia對照 / C點長槍兵看tooltip / '
            'D t15後驗四隻 / E看兩則監視訊息 / F開場3秒看兩則')

    scn.option_manager.legacy_execution_order = True
    scn.write_to_file(out)
    print(f'完成: {out}（觸發 {len(tm.triggers)} 支）')


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])

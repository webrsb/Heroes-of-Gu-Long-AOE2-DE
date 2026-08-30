# -*- coding: utf-8 -*-
"""渡船 spike（2026-08-30，船夫搭船 B 方案前置驗證）。三件事同檔驗：
① UNLOAD（效果 17）能否把盟友（P1）乘客從 P8 運輸船卸到指定岸格——原作「task 到陸地格」在 DE 對盟友不卸貨；
② 乘客在船上時「該玩家物件在區域內」是否觸發（登船水域 ②a、水道中段 ②b＝頭暈觸發點）；
③ TELEPORT_OBJECT 用區域選取一次傳多隻（踩旗出港）。
陽性對照：地面單位計入區域條件（t=3 應出「對照 OK」）；備援 t=40 自動開船（②a 失敗時流程仍走完）。
用法: python spikes/spike_ferry.py <template> <輸出>   （在 src/合併 下執行）"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, __file__.rsplit('spikes', 1)[0])
from core.scenario_io import load, write_out, deploy

WATER, DIRT = 1, 6
TRANSPORT, KNIGHT, MILITIA, FLAG = 545, 38, 74, 252
P0, P1, P8 = 0, 1, 8


def main(src, out):
    scn = load(src)
    um, tm, mm = scn.unit_manager, scn.trigger_manager, scn.map_manager
    cx = mm.map_width // 2
    cy = cx - 10
    # 水道：x∈[cx-10, cx+10] × y∈[cy-3, cy+3]；西岸 x≤cx-11、東岸 x≥cx+11
    for x in range(cx - 10, cx + 11):
        for y in range(cy - 3, cy + 4):
            mm.get_tile(x, y).terrain_id = WATER
    W_LAND = (cx - 14, cy - 3, cx - 11, cy + 3)
    E_LAND = (cx + 11, cy - 3, cx + 14, cy + 3)
    BOARD = (cx - 10, cy - 3, cx - 6, cy + 3)      # 船起點水域
    MID = (cx - 3, cy - 3, cx + 3, cy + 3)         # 水道中段（頭暈觸發點）
    E_DOCK = (cx + 8, cy - 3, cx + 10, cy + 3)     # 東岸停船水域
    LAND_E = (cx + 11, cy)                         # 東岸卸貨格
    FLAG_E = (cx + 13, cy + 2)                     # 踩旗出港格
    FAR = (cx + 20, cy)                            # 傳送落點

    def add(p, const, x, y):
        return um.add_unit(player=p, unit_const=const, x=x + .5, y=y + .5).reference_id
    ship = add(P8, TRANSPORT, cx - 9, cy)
    add(P1, KNIGHT, cx - 13, cy)
    add(P1, MILITIA, cx - 13, cy + 1)
    add(P0, FLAG, *FLAG_E)
    add(P1, FLAG, *FAR)

    def trig(name, enabled=True, looping=False):
        return tm.add_trigger(name, enabled=enabled, looping=looping)
    def chat(t, m):
        t.new_effect.send_chat(source_player=P1, message=m)
    def in_area(t, sp, area, olu=None):
        kw = dict(quantity=1, source_player=sp, area_x1=area[0], area_y1=area[1], area_x2=area[2], area_y2=area[3])
        if olu is not None:
            kw['object_list'] = olu
        t.new_condition.objects_in_area(**kw)

    t = trig('開場'); t.new_condition.timer(timer=0)
    t.new_effect.change_diplomacy(diplomacy=0, source_player=P1, target_player=P8)
    t.new_effect.change_diplomacy(diplomacy=0, source_player=P8, target_player=P1)
    t.new_effect.change_object_name(source_player=P8, selected_object_ids=[ship], message='畫舫')
    chat(t, '渡船spike: 右鍵點畫舫讓騎士+民兵登船。登船後船自動開往東岸；t40 沒登也會備援開船')

    t = trig('地面對照'); t.new_condition.timer(timer=3); in_area(t, P1, W_LAND)
    chat(t, '對照 OK: 地面單位計入區域條件（此行沒出=測試檔壞掉）')

    backup = trig('備援開船'); backup.new_condition.timer(timer=40)
    backup.new_effect.task_object(source_player=P8, selected_object_ids=[ship], location_x=LAND_E[0], location_y=LAND_E[1])
    chat(backup, '備援 t40: 船自動開往東岸（若②a沒出現＝船上單位不計入區域條件）')

    t = trig('登船偵測'); in_area(t, P1, BOARD)
    chat(t, '★②a 登船: 船上單位被區域條件偵測到 → 開船')
    t.new_effect.task_object(source_player=P8, selected_object_ids=[ship], location_x=LAND_E[0], location_y=LAND_E[1])
    t.new_effect.deactivate_trigger(trigger_id=backup.trigger_id)

    t = trig('水道偵測'); in_area(t, P1, MID)
    chat(t, '★②b 水道中段偵測到乘客（頭暈可在此觸發）')

    t = trig('抵岸'); in_area(t, P8, E_DOCK, olu=TRANSPORT)
    chat(t, '船抵東岸。等 8 秒看原作 task 法會不會自動卸貨…')
    unload_t = trig('抵岸卸載', enabled=False)
    t.new_effect.activate_trigger(trigger_id=unload_t.trigger_id)
    unload_t.new_condition.timer(timer=8)
    unload_t.new_effect.unload(source_player=P8, selected_object_ids=[ship], location_x=LAND_E[0], location_y=LAND_E[1])
    chat(unload_t, 't+8 已下 UNLOAD 令 ★① 乘客這時才出現＝UNLOAD 有效；早就出現＝task 法本來就會卸')

    t = trig('東岸偵測'); in_area(t, P1, E_LAND)
    chat(t, '★ 乘客已站在東岸陸地（記下：在 UNLOAD 訊息之前或之後？）→ 走去踩東岸旗子')

    t = trig('踩旗傳送'); in_area(t, P1, (FLAG_E[0], FLAG_E[1], FLAG_E[0], FLAG_E[1]))
    t.new_effect.teleport_object(source_player=P1, area_x1=E_LAND[0], area_y1=E_LAND[1],
                                 area_x2=E_LAND[2], area_y2=E_LAND[3], location_x=FAR[0], location_y=FAR[1])
    chat(t, '★③ 踩旗: 東岸你的單位應全部瞬移到遠處旗旁——回報到了幾隻（應 2）')

    write_out(scn, out)
    print(f'完成: {out}（觸發 {len(tm.triggers)} 支）')
    print('部署:', deploy(out))


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])

# -*- coding: utf-8 -*-
"""渡船 spike v4（2026-08-30，審查致命項的修法驗證）：`船卸` 實戰形狀——一次性、區域選船、TIMER 8、
由派船觸發武裝。驗：① 派船當下船仍在水域內，剛登船的人**不會**被卸回（TIMER 8 保護）；② 對岸抵達時區域選船 UNLOAD 能卸；
③ 回程再登船、再卸。陽性對照：t=3 地面單位計入區域；t=25 若西岸仍有你的單位＝被卸回或沒登船（負向對照訊息）。
用法: python spikes/spike_ferry4.py <template> <輸出>"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, __file__.rsplit('spikes', 1)[0])
from core.scenario_io import load, write_out, deploy

WATER = 1
TRANSPORT, KNIGHT, MILITIA = 545, 38, 74
P1, P8 = 1, 8


def main(src, out):
    scn = load(src)
    um, tm, mm = scn.unit_manager, scn.trigger_manager, scn.map_manager
    cx = mm.map_width // 2
    cy = cx - 10
    for x in range(cx - 10, cx + 11):
        for y in range(cy - 3, cy + 4):
            mm.get_tile(x, y).terrain_id = WATER
    W_LAND = (cx - 14, cy - 3, cx - 11, cy + 3)
    E_LAND = (cx + 11, cy - 3, cx + 14, cy + 3)
    W_DOCK = (cx - 10, cy - 3, cx - 8, cy + 3)     # 西岸停船水域（船起點在內）
    E_DOCK = (cx + 8, cy - 3, cx + 10, cy + 3)     # 東岸停船水域
    LAND_E, LAND_W = (cx + 11, cy), (cx - 11, cy)

    def add(p, const, x, y):
        return um.add_unit(player=p, unit_const=const, x=x + .5, y=y + .5).reference_id
    ship = add(P8, TRANSPORT, cx - 9, cy)
    add(P1, KNIGHT, cx - 13, cy)
    add(P1, MILITIA, cx - 13, cy + 1)

    def trig(name, enabled=True, looping=False):
        return tm.add_trigger(name, enabled=enabled, looping=looping)
    def chat(t, m):
        t.new_effect.send_chat(source_player=P1, message=m)
    def in_area(t, sp, area, olu=None):
        kw = dict(quantity=1, source_player=sp, area_x1=area[0], area_y1=area[1], area_x2=area[2], area_y2=area[3])
        if olu is not None:
            kw['object_list'] = olu
        t.new_condition.objects_in_area(**kw)
    def unload_trig(name, dock, land):
        t = trig(name, enabled=False)
        t.new_condition.timer(timer=8)
        in_area(t, P8, dock, olu=TRANSPORT)
        t.new_effect.unload(source_player=P8, object_list_unit_id=TRANSPORT,
                            area_x1=dock[0], area_y1=dock[1], area_x2=dock[2], area_y2=dock[3],
                            location_x=land[0], location_y=land[1])
        return t

    t = trig('開場'); t.new_condition.timer(timer=0)
    t.new_effect.change_diplomacy(diplomacy=0, source_player=P1, target_player=P8)
    t.new_effect.change_diplomacy(diplomacy=0, source_player=P8, target_player=P1)
    t.new_effect.change_object_name(source_player=P8, selected_object_ids=[ship], message='畫舫')
    chat(t, '卸貨v4: 20 秒內讓騎士+民兵登上畫舫。t20 派船去東岸，t45 派回西岸；到東岸後 20 秒內再上船回程')

    t = trig('地面對照'); t.new_condition.timer(timer=3); in_area(t, P1, W_LAND)
    chat(t, '對照 OK: 地面單位計入區域條件（此行沒出=測試檔壞掉）')

    unload_e = unload_trig('船卸東', E_DOCK, LAND_E)
    chat(unload_e, '★② 東岸：區域選船 UNLOAD 已下令（一次性，之後不再卸）')
    unload_w = unload_trig('船卸西', W_DOCK, LAND_W)
    chat(unload_w, '★③ 西岸：區域選船 UNLOAD 已下令')

    t = trig('船'); t.new_condition.timer(timer=20)
    t.new_effect.task_object(source_player=P8, selected_object_ids=[ship], location_x=LAND_E[0], location_y=LAND_E[1])
    t.new_effect.activate_trigger(trigger_id=unload_e.trigger_id)
    t.new_effect.activate_trigger(trigger_id=unload_w.trigger_id)
    chat(t, 't20 派船去東岸，同時武裝兩岸卸貨（TIMER 8）。★① 船上的人此刻不該被卸回西岸')

    t = trig('船2'); t.new_condition.timer(timer=45)
    t.new_effect.task_object(source_player=P8, selected_object_ids=[ship], location_x=LAND_W[0], location_y=LAND_W[1])
    t.new_effect.activate_trigger(trigger_id=unload_e.trigger_id)
    t.new_effect.activate_trigger(trigger_id=unload_w.trigger_id)
    chat(t, 't45 派船回西岸，再武裝兩岸卸貨')

    t = trig('負向對照'); t.new_condition.timer(timer=25); in_area(t, P1, W_LAND)
    chat(t, '✗ t25 西岸陸地仍有你的單位：沒登船，或派船時被卸回（①FAIL）')

    t = trig('東岸偵測'); in_area(t, P1, E_LAND)
    chat(t, '★ 乘客已站在東岸陸地（應在「②已下令」之後）→ 20 秒內再上船回程')
    t = trig('西岸回到'); t.new_condition.timer(timer=50); in_area(t, P1, W_LAND)
    chat(t, '★ 乘客回到西岸陸地（③ PASS）')

    write_out(scn, out)
    print(f'完成: {out}（觸發 {len(tm.triggers)} 支）')
    print('部署:', deploy(out))


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])

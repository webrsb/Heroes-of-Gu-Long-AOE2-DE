# -*- coding: utf-8 -*-
"""渡船 spike v2（2026-08-30）：spike_ferry ③ 區域傳送只搬到 1 隻 → 並排三種多隻寫法。
A 單一效果、區域選取（重現 v1，對照）；B 同區域連下 3 個傳送效果、各給相鄰不同落點；
C 單一效果 + max_units_affected=10。三組各 3 隻（騎士/民兵/斥候）站在旗旁，踩該組旗子即傳送。
用法: python spikes/spike_ferry2.py <template> <輸出>"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, __file__.rsplit('spikes', 1)[0])
from core.scenario_io import load, write_out, deploy

KNIGHT, MILITIA, SCOUT, FLAG = 38, 74, 448, 252
P0, P1 = 0, 1


def main(src, out):
    scn = load(src)
    um, tm, mm = scn.unit_manager, scn.trigger_manager, scn.map_manager
    cx = mm.map_width // 2
    y0 = cx - 12

    def add(p, const, x, y):
        return um.add_unit(player=p, unit_const=const, x=x + .5, y=y + .5).reference_id
    def chat(t, m):
        t.new_effect.send_chat(source_player=P1, message=m)

    t = tm.add_trigger('開場', enabled=True, looping=False); t.new_condition.timer(timer=0)
    chat(t, '傳送v2: 三組(A上/B中/C下)各3隻站旗左側。逐組踩旗，回報每組有幾隻到右邊你的旗旁')

    for i, (label, mode) in enumerate((('A單一效果', 'single'), ('B三效果三落點', 'chain'), ('C單一+max10', 'max'))):
        y = y0 + i * 6
        zone = (cx - 6, y - 1, cx - 3, y + 1)            # 三隻站這區
        flag = (cx - 2, y)                               # 踩旗格
        dest = (cx + 8, y)                               # 落點（你的旗）
        add(P1, KNIGHT, cx - 6, y); add(P1, MILITIA, cx - 5, y); add(P1, SCOUT, cx - 4, y)
        add(P0, FLAG, *flag); add(P1, FLAG, *dest)
        t = tm.add_trigger(label, enabled=True, looping=False)
        t.new_condition.objects_in_area(quantity=1, source_player=P1,
                                        area_x1=flag[0], area_y1=flag[1], area_x2=flag[0], area_y2=flag[1])
        zone_all = (cx - 6, y - 1, cx - 2, y + 1)         # 含旗格（踩旗那隻也要走）
        kw = dict(source_player=P1, area_x1=zone_all[0], area_y1=zone_all[1], area_x2=zone_all[2], area_y2=zone_all[3])
        if mode == 'single':
            t.new_effect.teleport_object(location_x=dest[0], location_y=dest[1], **kw)
        elif mode == 'chain':
            for k, (dx, dy) in enumerate(((0, 0), (0, 1), (1, 0))):
                t.new_effect.teleport_object(location_x=dest[0] + dx, location_y=dest[1] + dy, **kw)
        else:
            t.new_effect.teleport_object(location_x=dest[0], location_y=dest[1], max_units_affected=10, **kw)
        chat(t, f'★{label}: 踩旗了，右邊旗旁到了幾隻？（3 隻才算 PASS）')

    write_out(scn, out)
    print(f'完成: {out}（觸發 {len(tm.triggers)} 支）')
    print('部署:', deploy(out))


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])

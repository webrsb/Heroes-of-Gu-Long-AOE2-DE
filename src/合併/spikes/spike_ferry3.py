# -*- coding: utf-8 -*-
"""渡船 spike v3（2026-08-30）：售票窗情境——同一支迴圈觸發把「踩旗格上的那一隻」傳到**同一落點格**，
連續三隻踩旗，第二、三隻會不會因落點被前一隻佔住而失敗／被推開。
落點周圍 3×3 放三支計數觸發（1/2/3 隻）即時回報。陽性對照＝第一隻必到（v1/v2 已證）。
用法: python spikes/spike_ferry3.py <template> <輸出>"""
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
    y = cx - 10

    def add(p, const, x, yy):
        return um.add_unit(player=p, unit_const=const, x=x + .5, y=yy + .5).reference_id
    def chat(t, m):
        t.new_effect.send_chat(source_player=P1, message=m)

    flag = (cx - 3, y)
    dest = (cx + 8, y)
    add(P1, KNIGHT, cx - 8, y - 1); add(P1, MILITIA, cx - 8, y); add(P1, SCOUT, cx - 8, y + 1)
    add(P0, FLAG, *flag); add(P1, FLAG, cx + 8, y - 2)   # 落點北 2 格放你的旗當地標，落點本格留空

    t = tm.add_trigger('開場', enabled=True, looping=False); t.new_condition.timer(timer=0)
    chat(t, '同落點v3: 三隻逐一踩 Gaia 旗，每隻都傳到右邊你的旗南方 2 格的同一格。看計數訊息到幾隻')

    t = tm.add_trigger('踩旗傳送', enabled=True, looping=True)
    t.new_condition.objects_in_area(quantity=1, source_player=P1,
                                    area_x1=flag[0], area_y1=flag[1], area_x2=flag[0], area_y2=flag[1])
    t.new_effect.teleport_object(source_player=P1, area_x1=flag[0], area_y1=flag[1], area_x2=flag[0], area_y2=flag[1],
                                 location_x=dest[0], location_y=dest[1])

    for n in (1, 2, 3):
        t = tm.add_trigger(f'計數{n}', enabled=True, looping=False)
        t.new_condition.objects_in_area(quantity=n, source_player=P1,
                                        area_x1=dest[0] - 1, area_y1=dest[1] - 1, area_x2=dest[0] + 1, area_y2=dest[1] + 1)
        chat(t, f'★落點 3×3 內已有 {n} 隻' + ('（3 隻＝PASS：同落點連傳可行）' if n == 3 else ''))

    write_out(scn, out)
    print(f'完成: {out}（觸發 {len(tm.triggers)} 支）')
    print('部署:', deploy(out))


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])

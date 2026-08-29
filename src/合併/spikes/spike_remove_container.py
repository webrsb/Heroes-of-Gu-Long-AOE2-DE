# -*- coding: utf-8 -*-
"""容器移除放兵測試：拆掉容器，駐軍必彈出（卸載可能因落點被壓住而失敗，移除不受此限）。
三組：毯1=毛毯+移除；毯2=毛毯+擊殺；隱1=隱形物件(1291)+移除（量產目標）。
兵一律 P8 建檔→t0 轉 Gaia（無歸順旗標）→彈出後換家 P1（★驗證自動報數）。
用法: python spike_remove_container.py <template> <輸出>"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from AoE2ScenarioParser.scenarios.aoe2_de_scenario import AoE2DEScenario
from AoE2ScenarioParser.datasets.players import PlayerId

MILITIA, FLAG, RUG, INVIS = 74, 252, 711, 1291
P0, P1, P8 = PlayerId.GAIA, PlayerId.ONE, PlayerId.EIGHT

def main(src, out):
    scn = AoE2DEScenario.from_file(src)
    um, tm = scn.unit_manager, scn.trigger_manager
    cx = scn.map_manager.map_width // 2

    def add(player, const, x, yy, **kw):
        return um.add_unit(player=player, unit_const=const, x=x + .5, y=yy + .5, **kw).reference_id

    um.add_unit(player=P1, unit_const=FLAG, x=cx + .5, y=cx - 6 + .5)
    plan = [('毯1移除', RUG, cx - 8), ('毯2擊殺', RUG, cx), ('隱1移除', INVIS, cx + 8)]
    C = []
    for label, const, x in plan:
        b = add(P0, const, x, cx)
        g = add(P8, MILITIA, x, cx, garrisoned_in_id=b)
        C.append(dict(label=label, b=b, g=g, x=x))

    def trig(name, timer):
        t = tm.add_trigger(name, enabled=True, looping=False)
        t.new_condition.timer(timer=timer)
        return t
    def chat(t, m):
        t.new_effect.send_chat(source_player=P1, message=m)

    t = trig('開場', 0)
    for c in C:
        t.new_effect.change_ownership(source_player=P8, target_player=P0, selected_object_ids=[c['g']])
    chat(t, '容器移除測試: 左=毛毯(移除) 中=毛毯(擊殺) 右=隱形物件(移除)，各藏1隻Gaia兵')

    for n in (1, 2, 3):
        t = tm.add_trigger(f'驗{n}', enabled=True, looping=False)
        t.new_condition.own_objects(quantity=n, object_list=MILITIA, source_player=P1)
        chat(t, f'★驗證: P1 已擁有 {n} 隻民兵')

    t = trig('拆毯1', 10)
    t.new_effect.remove_object(source_player=P0, selected_object_ids=[C[0]['b']])
    chat(t, 't10: 移除毛毯1——兵有沒有彈出(灰色Gaia)?')
    t = trig('收兵1', 14)
    t.new_effect.change_ownership(source_player=P0, target_player=P1, selected_object_ids=[C[0]['g']])
    chat(t, 't14: 兵1轉P1(看★驗證)')
    t = trig('殺毯2', 18)
    t.new_effect.kill_object(source_player=P0, selected_object_ids=[C[1]['b']])
    chat(t, 't18: 擊殺毛毯2——兵有沒有彈出?')
    t = trig('收兵2', 22)
    t.new_effect.change_ownership(source_player=P0, target_player=P1, selected_object_ids=[C[1]['g']])
    chat(t, 't22: 兵2轉P1')
    t = trig('拆隱1', 26)
    t.new_effect.remove_object(source_player=P0, selected_object_ids=[C[2]['b']])
    chat(t, 't26: 移除隱形物件——兵有沒有彈出?(量產目標)')
    t = trig('收兵3', 30)
    t.new_effect.change_ownership(source_player=P0, target_player=P1, selected_object_ids=[C[2]['g']])
    chat(t, 't30: 兵3轉P1。總結回報: 三組各自彈兵與否+★驗證到幾')

    tm.legacy_execution_order = True
    scn.write_to_file(out)
    print(f'完成: {out}（觸發 {len(tm.triggers)} 支）')

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])

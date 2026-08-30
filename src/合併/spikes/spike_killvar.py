# -*- coding: utf-8 -*-
"""擊殺差值變數 spike（2026-08-30，接 spike_killratio：Modify Resource 對屬性44 無效）。
以 DE 變數重建 Kill Ratio 語意（擊殺增量、可歸零、不受死亡影響）：
  A 比較變數法：kills=屬性20 每tick寫入 V_K；獎勵條件 V_K > V_BASE_A；領獎後 V_BASE_A=屬性20
  B 差值法：V_DIFF=屬性20−V_BASE_B；獎勵條件 V_DIFF≥1；領獎後 V_BASE_B=屬性20
用法: python spike_killvar.py <template> <輸出>"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from AoE2ScenarioParser.scenarios.aoe2_de_scenario import AoE2DEScenario
from AoE2ScenarioParser.datasets.players import PlayerId

KNIGHT, MILITIA, VILLAGER = 38, 74, 83
KILLS, GOLD = 20, 3
SET, SUB = 1, 3
LARGER, GE = 2, 4
V_K, V_BASE_A, V_DIFF, V_BASE_B = 1, 2, 3, 4
P0, P1, P2 = PlayerId.GAIA, PlayerId.ONE, PlayerId.TWO


def main(src, out):
    scn = AoE2DEScenario.from_file(src)
    um, tm = scn.unit_manager, scn.trigger_manager
    cx = scn.map_manager.map_width // 2

    def add(player, const, x, y):
        return um.add_unit(player=player, unit_const=const, x=x + .5, y=y + .5).reference_id

    def trig(name, timer=None, enabled=True, looping=False):
        t = tm.add_trigger(name, enabled=enabled, looping=looping)
        if timer is not None:
            t.new_condition.timer(timer=timer)
        return t

    def chat(t, m):
        t.new_effect.send_chat(source_player=P1, message=m)

    add(P1, KNIGHT, cx, cx)
    victim = add(P1, VILLAGER, cx - 12, cx - 12)
    for i in range(8):
        add(P2, MILITIA, cx + 4 + (i % 4) * 2, cx + 4 + (i // 4) * 2)

    t = trig('t0設定', 0)
    t.new_effect.change_diplomacy(diplomacy=3, source_player=P1, target_player=P2)
    t.new_effect.change_diplomacy(diplomacy=3, source_player=P2, target_player=P1)
    t.new_effect.change_object_stance(source_player=P2, object_list_unit_id=MILITIA,
                                      attack_stance=3, area_x1=0, area_y1=0,
                                      area_x2=cx * 2, area_y2=cx * 2)
    chat(t, '★變數 spike：殺 P2 民兵。每殺 1 隻應恰出現 [RA] 與 [RB] 各 1 行；t40 死亡後亦然')

    k = trig('計數迴圈', looping=True)
    k.new_effect.modify_variable_by_resource(tribute_list=KILLS, source_player=P1,
                                             operation=SET, variable=V_K)
    k.new_effect.modify_variable_by_resource(tribute_list=KILLS, source_player=P1,
                                             operation=SET, variable=V_DIFF)
    k.new_effect.modify_variable_by_variable(variable=V_DIFF, operation=SUB, variable2=V_BASE_B)

    ra = trig('RA比較變數', looping=True)
    ra.new_condition.compare_variables(variable=V_K, comparison=LARGER, variable2=V_BASE_A)
    ra.new_condition.timer(timer=1)
    ra.new_effect.tribute(quantity=-10, tribute_list=GOLD, source_player=P1, target_player=P0)
    chat(ra, '[RA] 比較變數法 獎勵 +10金（base←屬性20）')
    ra.new_effect.modify_variable_by_resource(tribute_list=KILLS, source_player=P1,
                                              operation=SET, variable=V_BASE_A)

    rb = trig('RB差值', looping=True)
    rb.new_condition.variable_value(variable=V_DIFF, quantity=1, comparison=GE)
    rb.new_condition.timer(timer=1)
    rb.new_effect.tribute(quantity=-10, tribute_list=GOLD, source_player=P1, target_player=P0)
    chat(rb, '[RB] 差值法 獎勵 +10金（base←屬性20）')
    rb.new_effect.modify_variable_by_resource(tribute_list=KILLS, source_player=P1,
                                              operation=SET, variable=V_BASE_B)

    for n in (1, 2, 3):
        p = trig(f'P{n}')
        p.new_condition.accumulate_attribute(quantity=n, attribute=KILLS, source_player=P1)
        chat(p, f'[P{n}] 陽性對照：屬性20 累計擊殺≥{n}')

    d = trig('D模擬死亡', 40)
    d.new_effect.kill_object(source_player=P1, selected_object_ids=[victim])
    chat(d, '[D] t40 己方村民陣亡＝模擬英雄死亡。之後每殺 1 隻仍應各出 1 行 [RA]/[RB]')

    for s in (20, 40, 60, 80):
        chat(trig(f'心跳{s}', s), f'--- t{s} ---')

    tm.legacy_execution_order = True
    scn.write_to_file(out)
    print('已寫出', out)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])

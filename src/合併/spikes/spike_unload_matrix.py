# -*- coding: utf-8 -*-
"""卸載組合矩陣：5 棚並排，t=10/12/14/16/18 逐棚下卸載令，找出會出兵的組合。
棚1: Gaia帳+Gaia兵, 卸載sp=0
棚2: Gaia帳+Gaia兵, t=8先把兵轉P1, 卸載sp=0（Gaia帳吐外家兵?）
棚3: P8帳+Gaia兵, 卸載當下帳與兵都先轉P1, 卸載sp=1（全套換主舞步）
棚4: P8帳+Gaia兵, 兵先轉P1, 卸載sp=8+座標（全流程失敗案重試+補座標）
棚5: P8帳+Gaia兵, 直接卸載sp=8+座標（B5帳1原樣重測）
全部卸載都帶座標。觀察: 哪幾棚的民兵站出來了；棚3換帳主時是否兵先彈出。
用法: python spike_unload_matrix.py <template> <輸出>"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from AoE2ScenarioParser.scenarios.aoe2_de_scenario import AoE2DEScenario
from AoE2ScenarioParser.datasets.players import PlayerId

MILITIA, FLAG, TENT = 74, 252, 1097
P0, P1, P8 = PlayerId.GAIA, PlayerId.ONE, PlayerId.EIGHT

def main(src, out):
    scn = AoE2DEScenario.from_file(src)
    um, tm = scn.unit_manager, scn.trigger_manager
    cx = scn.map_manager.map_width // 2
    y = cx

    def add(player, const, x, yy, **kw):
        return um.add_unit(player=player, unit_const=const, x=x + .5, y=yy + .5, **kw).reference_id

    um.add_unit(player=P1, unit_const=FLAG, x=cx + .5, y=y - 6 + .5)
    plan = [('棚1', P0), ('棚2', P0), ('棚3', P8), ('棚4', P8), ('棚5', P8)]
    T = {}
    for i, (label, towner) in enumerate(plan):
        x = cx - 16 + i * 7
        b = add(towner, TENT, x, y)
        g = add(P0, MILITIA, x, y, garrisoned_in_id=b)
        T[label] = dict(b=b, g=g, x=x)

    def trig(name, timer):
        t = tm.add_trigger(name, enabled=True, looping=False)
        t.new_condition.timer(timer=timer)
        return t
    def chat(t, m):
        t.new_effect.send_chat(source_player=P1, message=m)
    def unload(t, ref, sp, x):
        t.new_effect.unload(source_player=sp, selected_object_ids=[ref], location_x=x, location_y=y + 3)
    def own(t, ref, frm, to):
        t.new_effect.change_ownership(source_player=frm, target_player=to, selected_object_ids=[ref])

    t = trig('開場', 0)
    t.new_effect.change_diplomacy(diplomacy=0, source_player=P1, target_player=P8)
    t.new_effect.change_diplomacy(diplomacy=0, source_player=P8, target_player=P1)
    for label, _ in plan:
        t.new_effect.change_object_name(source_player=-1, selected_object_ids=[T[label]['b']], message=label)
    chat(t, '卸載矩陣: 左起棚1~5，各藏一隻Gaia民兵。t=10起每2秒卸一棚，看誰出兵')

    t = trig('棚2兵先轉P1', 8)
    own(t, T['棚2']['g'], P0, P1)
    chat(t, 't8: 棚2的兵已轉P1（帳仍Gaia）')

    t = trig('棚1卸', 10); unload(t, T['棚1']['b'], P0, T['棚1']['x']); chat(t, 't10: 棚1卸載(Gaia帳Gaia兵sp=0)')
    t = trig('棚2卸', 12); unload(t, T['棚2']['b'], P0, T['棚2']['x']); chat(t, 't12: 棚2卸載(Gaia帳P1兵sp=0)')
    t = trig('棚3舞步', 14)
    own(t, T['棚3']['g'], P0, P1)
    own(t, T['棚3']['b'], P8, P1)
    unload(t, T['棚3']['b'], P1, T['棚3']['x'])
    chat(t, 't14: 棚3帳+兵全轉P1後卸載sp=1（注意換帳主瞬間兵有沒有先彈出）')
    t = trig('棚4卸', 16)
    own(t, T['棚4']['g'], P0, P1)
    unload(t, T['棚4']['b'], P8, T['棚4']['x'])
    chat(t, 't16: 棚4兵轉P1後P8卸載+座標')
    t = trig('棚5卸', 18); unload(t, T['棚5']['b'], P8, T['棚5']['x']); chat(t, 't18: 棚5直接P8卸載Gaia兵+座標')
    t = trig('總結', 25)
    chat(t, 't25: 回報哪幾棚出兵、出兵當下歸屬（Gaia灰/藍P1）、棚3是否在換主瞬間彈兵')

    tm.legacy_execution_order = True
    scn.write_to_file(out)
    print(f'完成: {out}（觸發 {len(tm.triggers)} 支）')

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])

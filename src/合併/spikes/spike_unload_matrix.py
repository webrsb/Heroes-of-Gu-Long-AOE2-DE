# -*- coding: utf-8 -*-
"""卸載矩陣 v2：杜絕自動歸順——所有帳棚與兵建檔一律 P8，兵於 t=0 轉 Gaia（遊戲中轉的
Gaia 無歸順旗標）。五棚驗不同的重生順序/歸屬組合：
棚1: t=0兵轉Gaia → 卸載時 兵先轉P1(駐軍中) → sp=8卸載
棚2: t=0兵轉Gaia → sp=8先卸載(兵仍Gaia) → 2秒後兵轉P1
棚3: t=0兵轉Gaia → 卸載時 帳+兵都轉P1 → sp=1卸載
棚4: 兵一直P8(對照,AI同主卸載已證) → sp=8卸載 → 兵轉P1
棚5: t=0兵轉Gaia → sp=8卸載 → 永不轉家（驗:出來的兵保持Gaia不被吸走）
★驗證訊息自動報 P1 民兵數(1~4)。棚4的兵若在下令前自己跑出來=P8 AI亂卸(記錄)。
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
    T = {}
    for i in range(1, 6):
        x = cx - 16 + (i - 1) * 7
        b = add(P8, TENT, x, y)
        g = add(P8, MILITIA, x, y, garrisoned_in_id=b)
        T[i] = dict(b=b, g=g, x=x)

    def trig(name, timer):
        t = tm.add_trigger(name, enabled=True, looping=False)
        t.new_condition.timer(timer=timer)
        return t
    def chat(t, m):
        t.new_effect.send_chat(source_player=P1, message=m)
    def own(t, ref, frm, to):
        t.new_effect.change_ownership(source_player=frm, target_player=to, selected_object_ids=[ref])
    def unload(t, i, sp):
        t.new_effect.unload(source_player=sp, selected_object_ids=[T[i]['b']],
                            location_x=T[i]['x'], location_y=y + 3)

    t = trig('開場', 0)
    t.new_effect.change_diplomacy(diplomacy=0, source_player=P1, target_player=P8)
    t.new_effect.change_diplomacy(diplomacy=0, source_player=P8, target_player=P1)
    for i in (1, 2, 3, 5):
        own(t, T[i]['g'], P8, P0)     # 駐軍中 P8→Gaia（棚4 對照維持 P8）
    for i in range(1, 6):
        t.new_effect.change_object_name(source_player=-1, selected_object_ids=[T[i]['b']], message=f'棚{i}')
    chat(t, '矩陣v2: 全部P8建檔。棚1235兵已轉Gaia，棚4兵留P8。t=10起每3秒卸一棚')

    for n in range(1, 5):
        t = tm.add_trigger(f'驗{n}', enabled=True, looping=False)
        t.new_condition.own_objects(quantity=n, object_list=MILITIA, source_player=P1)
        chat(t, f'★驗證: P1 已擁有 {n} 隻民兵')

    t = trig('棚1', 10); own(t, T[1]['g'], P0, P1); unload(t, 1, P8)
    chat(t, 't10 棚1: 兵駐軍中轉P1 → P8卸載')
    t = trig('棚2卸', 13); unload(t, 2, P8); chat(t, 't13 棚2: 先卸載(Gaia兵)')
    t = trig('棚2轉', 15); own(t, T[2]['g'], P0, P1); chat(t, 't15 棚2: 出棚兵轉P1')
    t = trig('棚3', 18)
    own(t, T[3]['b'], P8, P1); own(t, T[3]['g'], P0, P1); unload(t, 3, P1)
    chat(t, 't18 棚3: 帳+兵全轉P1 → sp=1卸載（注意換帳主瞬間是否彈兵）')
    t = trig('棚4', 21); unload(t, 4, P8); own(t, T[4]['g'], P8, P1)
    chat(t, 't21 棚4: P8同主卸載 → 轉P1（若它更早自己出來=AI亂卸）')
    t = trig('棚5', 24); unload(t, 5, P8)
    chat(t, 't24 棚5: 卸載後永不轉家——出來的兵應保持Gaia灰色且不被吸走')
    t = trig('總結', 32)
    chat(t, 't32 回報: 各棚出兵?順序?顏色?★驗證幾隻?棚5是否維持Gaia?')

    tm.legacy_execution_order = True
    scn.write_to_file(out)
    print(f'完成: {out}（觸發 {len(tm.triggers)} 支）')

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])

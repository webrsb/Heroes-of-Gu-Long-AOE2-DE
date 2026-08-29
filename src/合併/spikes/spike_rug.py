# -*- coding: utf-8 -*-
"""毛毯藏兵測試：RUGS(const711, Gaia裝飾)當藏兵艙——無主人、無AI、無歸順、無外交。
兩隻民兵建檔掛P8（防歸順旗標）、garrisoned_in_id=毛毯、t=0轉Gaia。
萃取手段逐一隔離：駐軍中換家→毛毯卸載(sp=0)→傳送。兵2驗「Gaia兵直接卸載」。
用法: python spike_rug.py <template> <輸出>"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from AoE2ScenarioParser.scenarios.aoe2_de_scenario import AoE2DEScenario
from AoE2ScenarioParser.datasets.players import PlayerId

MILITIA, FLAG, RUG = 74, 252, 711
P0, P1, P8 = PlayerId.GAIA, PlayerId.ONE, PlayerId.EIGHT

def main(src, out):
    scn = AoE2DEScenario.from_file(src)
    um, tm = scn.unit_manager, scn.trigger_manager
    cx = scn.map_manager.map_width // 2

    def add(player, const, x, yy, **kw):
        return um.add_unit(player=player, unit_const=const, x=x + .5, y=yy + .5, **kw).reference_id

    um.add_unit(player=P1, unit_const=FLAG, x=cx + 6.5, y=cx + .5)
    rug = add(P0, RUG, cx, cx)
    g1 = add(P8, MILITIA, cx, cx, garrisoned_in_id=rug)
    g2 = add(P8, MILITIA, cx, cx, garrisoned_in_id=rug)

    def trig(name, timer):
        t = tm.add_trigger(name, enabled=True, looping=False)
        t.new_condition.timer(timer=timer)
        return t
    def chat(t, m):
        t.new_effect.send_chat(source_player=P1, message=m)

    t = trig('開場', 0)
    for g in (g1, g2):
        t.new_effect.change_ownership(source_player=P8, target_player=P0, selected_object_ids=[g])
    chat(t, '毛毯測試: 兩隻民兵駐在中央毛毯內(已轉Gaia)。地面應無兵。看毛毯有無駐軍跡象')

    for n in (1, 2):
        t = tm.add_trigger(f'驗{n}', enabled=True, looping=False)
        t.new_condition.own_objects(quantity=n, object_list=MILITIA, source_player=P1)
        chat(t, f'★驗證: P1 已擁有 {n} 隻民兵')

    t = trig('兵1換家', 10)
    t.new_effect.change_ownership(source_player=P0, target_player=P1, selected_object_ids=[g1])
    chat(t, 't10: 兵1駐軍中轉P1（看★驗證有沒有跳=駐軍中換家有效）')
    t = trig('毯卸載', 13)
    t.new_effect.unload(source_player=P0, selected_object_ids=[rug], location_x=cx, location_y=cx + 2)
    chat(t, 't13: 對毛毯下卸載令(sp=0)——兵1有沒有走出來？')
    t = trig('兵1傳送', 17)
    t.new_effect.teleport_object(source_player=P1, selected_object_ids=[g1], location_x=cx + 6, location_y=cx)
    chat(t, 't17: 傳送兵1到旗幟——剛才沒出來的話現在出來了嗎？')
    t = trig('毯卸載2', 21)
    t.new_effect.unload(source_player=P0, selected_object_ids=[rug], location_x=cx, location_y=cx + 2)
    chat(t, 't21: 再卸載毛毯——Gaia兵2有沒有出來？')
    t = trig('兵2收尾', 25)
    t.new_effect.change_ownership(source_player=P0, target_player=P1, selected_object_ids=[g2])
    t.new_effect.teleport_object(source_player=P1, selected_object_ids=[g2], location_x=cx + 6, location_y=cx)
    chat(t, 't25: 兵2換家+傳送。總結回報: 駐軍中換家?毯卸載?傳送? 各自有效與否')

    tm.legacy_execution_order = True
    scn.write_to_file(out)
    print(f'完成: {out}（觸發 {len(tm.triggers)} 支）')

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])

# -*- coding: utf-8 -*-
"""替換單位預覽檔：拳候選一排（掛P1可看數值），加 const817(Statue A) 實測有無圖形。
用法: python spike_preview_units.py <template> <輸出>"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from AoE2ScenarioParser.scenarios.aoe2_de_scenario import AoE2DEScenario
from AoE2ScenarioParser.datasets.players import PlayerId

CANDIDATES = [(2045, '董卓(DLC)'), (844, '李舜臣'), (168, '狄奧多里克'),
              (171, '紅髮艾瑞克'), (2346, '克里昂(DLC)')]
FLAG = 252

def main(src, out):
    scn = AoE2DEScenario.from_file(src)
    um, tm = scn.unit_manager, scn.trigger_manager
    cx = scn.map_manager.map_width // 2

    refs = []
    for i, (const, label) in enumerate(CANDIDATES):
        r = um.add_unit(player=PlayerId.ONE, unit_const=const, x=cx - 8 + i * 3 + .5, y=cx + .5)
        refs.append((r.reference_id, label))
    um.add_unit(player=PlayerId.GAIA, unit_const=817, x=cx + .5, y=cx + 6.5)     # Statue A 實測
    um.add_unit(player=PlayerId.GAIA, unit_const=FLAG, x=cx + 1.5, y=cx + 6.5)   # 旁邊放旗當座標記號

    t = tm.add_trigger('標籤', enabled=True)
    t.new_condition.timer(timer=1)
    for ref, label in refs:
        t.new_effect.change_object_name(source_player=PlayerId.ONE, selected_object_ids=[ref], message=label)
    t.new_effect.send_chat(source_player=PlayerId.ONE,
                           message='拳候選預覽: 左起 董卓/李舜臣/狄奧多里克/艾瑞克/克里昂。'
                                   '南方旗幟旁=const817雕像實測(看得到=保留,看不到=要換)')
    tm.legacy_execution_order = True
    scn.write_to_file(out)
    print(f'完成: {out}')

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])

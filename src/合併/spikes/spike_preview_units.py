# -*- coding: utf-8 -*-
"""替換單位預覽檔：拳候選一排（掛P1可看數值），加 const817(Statue A) 實測有無圖形。
用法: python spike_preview_units.py <template> <輸出>"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from AoE2ScenarioParser.scenarios.aoe2_de_scenario import AoE2DEScenario
from AoE2ScenarioParser.datasets.players import PlayerId

CANDIDATES = [
    (694, '拳:精銳狂戰士(推薦)'), (692, '拳:狂戰士'), (2045, '拳:董卓(DLC)'), (844, '拳:李舜臣'),
    (329, '37:駱駝騎士(推薦)'), (38, '37:騎士'), (546, '37:輕騎兵'),
    (473, '573:雙手劍士'), (77, '573:長劍士'), (83, '573:村民'),
]
FLAG = 252

def main(src, out):
    scn = AoE2DEScenario.from_file(src)
    um, tm = scn.unit_manager, scn.trigger_manager
    cx = scn.map_manager.map_width // 2

    refs = []
    for i, (const, label) in enumerate(CANDIDATES):
        r = um.add_unit(player=PlayerId.ONE, unit_const=const, x=cx - 8 + (i % 4) * 3 + .5, y=cx + (i // 4) * 3 + .5)
        refs.append((r.reference_id, label))
    um.add_unit(player=PlayerId.GAIA, unit_const=817, x=cx + .5, y=cx + 6.5)     # Statue A 實測
    um.add_unit(player=PlayerId.GAIA, unit_const=FLAG, x=cx + 1.5, y=cx + 6.5)   # 旁邊放旗當座標記號

    t = tm.add_trigger('標籤', enabled=True)
    t.new_condition.timer(timer=1)
    for ref, label in refs:
        t.new_effect.change_object_name(source_player=PlayerId.ONE, selected_object_ids=[ref], message=label)
    t.new_effect.send_chat(source_player=PlayerId.ONE,
                           message='替換候選預覽(北排拳4隻/中排37三隻/南排573三隻,懸停看名)。'
                                   '旗幟旁=const817雕像實測(看得到=保留,看不到=要換)')
    tm.legacy_execution_order = True
    scn.write_to_file(out)
    print(f'完成: {out}')

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])

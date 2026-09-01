# -*- coding: utf-8 -*-
"""全量觸發 DUMP（人讀版）：每支觸發的條件/效果全欄位攤平成文字，供編輯器翻閱與 grep。
用法: python -m analysis.dump_triggers <scenario> <out_txt>
標記：★本體=六職業本體 ref；訊息原文完整保留。"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

HERO_REFS = {0: 'P1刀', 1: 'P2劍', 2: 'P3槍', 502: 'P4棍', 7: 'P5拳', 45117: 'P6暗'}


def main(src, out_txt):
    from AoE2ScenarioParser.scenarios.aoe2_de_scenario import AoE2DEScenario
    from AoE2ScenarioParser.datasets.conditions import ConditionId
    from AoE2ScenarioParser.datasets.effects import EffectId
    from AoE2ScenarioParser.datasets.units import UnitInfo
    from AoE2ScenarioParser.datasets.buildings import BuildingInfo
    from AoE2ScenarioParser.datasets.other import OtherInfo
    from AoE2ScenarioParser.datasets.heroes import HeroInfo

    def constname(c):
        if c in (-1, None):
            return ''
        for D in (UnitInfo, HeroInfo, BuildingInfo, OtherInfo):
            try:
                return f'{c}={D.from_id(c).name}'
            except Exception:
                pass
        return f'{c}=?'

    def refmark(r):
        return f'{r}★{HERO_REFS[r]}' if r in HERO_REFS else str(r)

    scn = AoE2DEScenario.from_file(src)
    tm = scn.trigger_manager
    L = []
    for t in tm.triggers:
        L.append(f'{"=" * 70}')
        L.append(f'T{t.trigger_id}「{t.name or "(無名)"}」 enabled={t.enabled} looping={t.looping}')
        for i, c in enumerate(t.conditions):
            try:
                nm = ConditionId(c.condition_type).name
            except Exception:
                nm = f'cond{c.condition_type}'
            parts = [f'  C{i} {nm}']
            if getattr(c, 'unit_object', -1) not in (-1, None):
                parts.append(f'unit={refmark(c.unit_object)}')
            if getattr(c, 'next_object', -1) not in (-1, None):
                parts.append(f'next={refmark(c.next_object)}')
            if getattr(c, 'source_player', -1) not in (-1, None):
                parts.append(f'sp={c.source_player}')
            if getattr(c, 'object_list', -1) not in (-1, None):
                parts.append(f'物件={constname(c.object_list)}')
            if getattr(c, 'quantity', -1) not in (-1, None):
                parts.append(f'qty={c.quantity}')
            if getattr(c, 'timer', -1) not in (-1, None):
                parts.append(f'timer={c.timer}')
            if getattr(c, 'area_x1', -1) not in (-1, None):
                parts.append(f'區({c.area_x1},{c.area_y1})-({c.area_x2},{c.area_y2})')
            if getattr(c, 'inverted', 0) in (1, True):
                parts.append('反相')
            L.append(' '.join(parts))
        for i, e in enumerate(t.effects):
            try:
                nm = EffectId(e.effect_type).name
            except Exception:
                nm = f'eff{e.effect_type}'
            parts = [f'  E{i} {nm}']
            if getattr(e, 'source_player', -1) not in (-1, None):
                parts.append(f'sp={e.source_player}')
            if getattr(e, 'target_player', -1) not in (-1, None):
                parts.append(f'tp={e.target_player}')
            if getattr(e, 'object_list_unit_id', -1) not in (-1, None):
                parts.append(f'物件={constname(e.object_list_unit_id)}')
            sel = list(getattr(e, 'selected_object_ids', None) or [])
            if sel:
                parts.append('sel=[' + ','.join(refmark(r) for r in sel) + ']')
            if getattr(e, 'location_object_reference', -1) not in (-1, None):
                parts.append(f'loc_ref={refmark(e.location_object_reference)}')
            if getattr(e, 'location_x', -1) not in (-1, None) and e.location_x != -1:
                parts.append(f'loc=({e.location_x},{e.location_y})')
            if getattr(e, 'area_x1', -1) not in (-1, None):
                parts.append(f'區({e.area_x1},{e.area_y1})-({e.area_x2},{e.area_y2})')
            if getattr(e, 'quantity', None) not in (-1, None):
                parts.append(f'qty={e.quantity}')
            if getattr(e, 'trigger_id', -1) not in (-1, None):
                parts.append(f'→T{e.trigger_id}')
            msg = getattr(e, 'message', None) or ''
            if msg:
                parts.append(f'訊息「{msg}」')
            L.append(' '.join(parts))
    open(out_txt, 'w', encoding='utf-8', newline='\n').write('\n'.join(L) + '\n')
    print(f'DUMP 完成: {out_txt}（{len(tm.triggers)} 支）')


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])

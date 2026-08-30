# -*- coding: utf-8 -*-
"""s373 野怪生成改名（params.mob_names；spec docs/superpowers/specs/2026-08-30-野怪改名-design.md）。

野怪全由生成觸發動態建立（移除格→建立→改血(格)→改攻(格)）。本步在每支生成觸發尾端、
對每個帶座標的 P7 建立效果追加 change_object_name(sp=7, 該單位類型, 建立點單格)，
與原作改血/改攻同一套定址；同 tick 內建立即改名。對照表鍵＝(tid, const)。
顯示：有等級 'Lv{lv} {display}'，無等級 '{display}'。全 sp=7、不進矩陣、不增觸發。"""
from core.change import Change
from .base import trig_by_id, Step, BuildError

CREATE, P7 = 11, 7


def _fmt(row):
    lv = row.get('lv')
    return f"Lv{lv} {row['display']}" if lv not in (None, '') else row['display']


def apply_mob_names(tm, rows):
    changes = []
    table = {}
    for r in rows:
        key = (int(r['tid']), int(r['const']))
        if key in table:
            raise BuildError(f'缺裁決：mob_names (tid,const)={key} 重複')
        table[key] = r
    for tid in sorted({k[0] for k in table}):
        rows_t = {c: r for (t_, c), r in table.items() if t_ == tid}
        name = next(iter(rows_t.values()))['name']
        t = trig_by_id(tm, tid)
        if t is None or (t.name or '') != name:
            raise BuildError(f'缺裁決：T{tid} 名稱「{getattr(t, "name", None)}」≠ 預期「{name}」，'
                             f'基底觸發編號可能位移')
        creates = [e for e in t.effects
                   if getattr(e, 'effect_type', None) == CREATE and getattr(e, 'source_player', -1) == P7]
        located = [e for e in creates if getattr(e, 'location_x', -1) not in (-1, None)]
        if not located:
            raise BuildError(f'缺裁決：T{tid}「{name}」無帶座標的 P7 建立效果')
        present = {getattr(e, 'object_list_unit_id', -1) for e in located}
        missing, unused = present - set(rows_t), set(rows_t) - present
        if missing:
            raise BuildError(f'缺裁決：T{tid}「{name}」建立單位 const {sorted(missing)} 無對照行')
        if unused:
            raise BuildError(f'缺裁決：T{tid}「{name}」對照行 const {sorted(unused)} 未出現於觸發')
        for e in located:
            msg = _fmt(rows_t[e.object_list_unit_id])
            x, y = e.location_x, e.location_y
            t.new_effect.change_object_name(object_list_unit_id=e.object_list_unit_id, source_player=P7,
                                            area_x1=x, area_y1=y, area_x2=x, area_y2=y, message=msg)
            changes.append(Change('s373', 'eff_add', f'T{tid}「{name}」', 'change_object_name', '',
                                  f'({x},{y})→「{msg}」', '野怪生成改名'))
        stray = len(creates) - len(located)
        if stray:
            changes.append(Change('s373', 'skip', f'T{tid}「{name}」', 'create_no_loc', '',
                                  str(stray), '無座標建立效果跳過'))
    return changes


class MobNameStep(Step):
    id = 's373'
    title = '野怪生成改名'
    intro = '生成觸發尾端追加 change_object_name（建立點單格定址）。無 mob_names 參數時跳過。'

    def apply(self, ctx):
        rows = ctx.spec.params.get('mob_names')
        if not rows:
            return []
        return apply_mob_names(ctx.base.trigger_manager, rows)

    def test_guide(self, changes):
        n = sum(1 for c in changes if c.kind == 'eff_add')
        return (f'野怪改名：{n} 個建立點掛改名。單人驗：殺一隻民團等補怪，點選看「Lv1 民團」；'
                '東北角鐵豬王、賓周走廊增援「賓周幫幫眾」。\n'
                '陽性對照：金獅/銀龍/賓周名稱不變、血條系統照舊。')


STEP = MobNameStep()

# -*- coding: utf-8 -*-
"""s37 觸發欄位定點修復（params.trigger_fixes）。

用途：修原作者的複製貼上錯誤——6P 本體換單位後漏改的 ref8 斷鏈（編輯器紅字）、
player 欄位抄錯家。每條裁決帶三重防呆：觸發名、欄位現值都要與 spec 完全相符，
否則 BuildError 要求重新查證（基底若換版，舊裁決不得靜默套用）。"""
from core.change import Change
from .base import Step, BuildError


def apply_fix(tm, entry) -> Change:
    tid = entry['trigger_id']
    t = tm.triggers[tid]
    if (t.name or '') != entry.get('name', ''):
        raise BuildError(f'缺裁決：T{tid} 名稱「{t.name}」≠ spec 預期「{entry.get("name", "")}」，'
                         f'基底觸發編號可能位移，請重查')
    kind = entry['kind']
    obj = (t.conditions if kind == 'condition' else t.effects)[entry['index']]
    field, old, new = entry['field'], entry['old'], entry['new']
    tag = f'T{tid}「{t.name}」{"C" if kind == "condition" else "E"}#{entry["index"]}'
    if field == 'selected_object_ids':
        cur = list(obj.selected_object_ids or [])
        if old not in cur:
            raise BuildError(f'缺裁決：{tag} selected_object_ids={cur} 不含預期舊值 {old}，請重查')
        obj.selected_object_ids = [new if r == old else r for r in cur]
    else:
        cur = getattr(obj, field)
        if cur != old:
            raise BuildError(f'缺裁決：{tag} {field}={cur} ≠ spec 預期舊值 {old}，請重查')
        setattr(obj, field, new)
    return Change('s37', f'{kind}_field', tag, field, str(old), str(new),
                  entry.get('reason', ''))


class TrigFixStep(Step):
    id = 's37'
    title = '觸發定點修復'
    intro = '依 params.trigger_fixes 修原作者複製貼上錯誤（ref 斷鏈、player 欄位錯家）。'

    def apply(self, ctx):
        entries = (ctx.spec.params.get('trigger_fixes')) or []
        return [apply_fix(ctx.base.trigger_manager, e) for e in entries]

    def test_guide(self, changes):
        if not changes:
            return None
        refs = [c for c in changes if c.field in ('unit_object', 'selected_object_ids')]
        pls = [c for c in changes if c.field == 'source_player']
        return (f'觸發定點修復：ref 斷鏈 {len(refs)} 處、player 欄位 {len(pls)} 處。\n'
                '怎麼測（最快）：DE 編輯器開合併版看觸發清單——原本 6 支紅字'
                '（6馬召/6召/6哥8/暗刁6 三支無名）應全數轉綠。只看不存檔！\n'
                '遊戲內抽驗：用 6P 玩，本體死亡時馬應被收走（6召）；'
                '2P 施孽功銀兩應進自己帳（原本錯發 1P）。\n'
                '異常判讀：編輯器仍有紅字＝回報紅字觸發名稱與其條件/效果列表。')


STEP = TrigFixStep()

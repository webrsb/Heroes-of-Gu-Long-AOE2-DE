# -*- coding: utf-8 -*-
"""s37 觸發欄位定點修復（params.trigger_fixes）。

用途：修原作者的複製貼上錯誤——6P 本體換單位後漏改的 ref8 斷鏈（編輯器紅字）、
player 欄位抄錯家。每條裁決帶三重防呆：觸發名、欄位現值都要與 spec 完全相符，
否則 BuildError 要求重新查證（基底若換版，舊裁決不得靜默套用）。"""
from core.change import Change
from .base import Step, BuildError


def apply_fix(tm, entry) -> Change:
    if entry['kind'] == 'trigger_add':            # 原作漏建的座位副本（如 5/6 座位銀兩護欄）
        return _add_trigger(tm, entry)
    tid = entry['trigger_id']
    t = tm.triggers[tid]
    if (t.name or '') != entry.get('name', ''):
        raise BuildError(f'缺裁決：T{tid} 名稱「{t.name}」≠ spec 預期「{entry.get("name", "")}」，'
                         f'基底觸發編號可能位移，請重查')
    kind = entry['kind']
    if kind == 'effect_add':                      # 尾端新增啟停效果（複製貼上把效果放錯支時補回）
        spec = entry['effect']
        if spec['type'] not in ('activate_trigger', 'deactivate_trigger'):
            raise BuildError(f'缺裁決：T{tid} effect_add 只支援 activate/deactivate_trigger，得到 {spec["type"]}')
        target = tm.triggers[spec['trigger_id']] if 0 <= spec['trigger_id'] < len(tm.triggers) else None
        if target is None or (target.name or '') != spec.get('target_name', ''):
            raise BuildError(f'缺裁決：T{tid} effect_add 目標 T{spec["trigger_id"]} 名稱'
                             f'「{getattr(target, "name", None)}」≠ spec 預期「{spec.get("target_name", "")}」，請重查')
        getattr(t.new_effect, spec['type'])(trigger_id=spec['trigger_id'])
        return Change('s37', 'effect_add', f'T{tid}「{t.name}」', spec['type'], '',
                      f'→T{spec["trigger_id"]}「{target.name}」', entry.get('reason', ''))
    field, old, new = entry['field'], entry['old'], entry['new']
    if kind == 'trigger':                         # 觸發層旗標（enabled / looping）
        if field not in ('enabled', 'looping'):
            raise BuildError(f'缺裁決：T{tid} trigger 層只支援 enabled/looping，得到 {field}')
        cur = int(getattr(t, field) or 0)
        if cur != old:
            raise BuildError(f'缺裁決：T{tid}「{t.name}」{field}={cur} ≠ spec 預期舊值 {old}，請重查')
        setattr(t, field, new)
        return Change('s37', 'trigger_flag', f'T{tid}「{t.name}」', field, str(old), str(new),
                      entry.get('reason', ''))
    obj = (t.conditions if kind == 'condition' else t.effects)[entry['index']]
    tag = f'T{tid}「{t.name}」{"C" if kind == "condition" else "E"}#{entry["index"]}'
    if field == 'selected_object_ids':
        cur = list(obj.selected_object_ids or [])
        if isinstance(old, list):                      # 整列比對後整列替換（空選取漏填 ref 用）
            if cur != list(old):
                raise BuildError(f'缺裁決：{tag} selected_object_ids={cur} ≠ spec 預期舊列 {old}，請重查')
            obj.selected_object_ids = list(new)
        else:
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


def _resolve_by_name(tm, name, tag):
    """以觸發名找恰一支目標（新觸發的 id 在寫 spec 時不存在，只能以名指）。"""
    hits = [t for t in tm.triggers if (t.name or '') == name]
    if len(hits) != 1:
        raise BuildError(f'缺裁決：{tag} trigger_name「{name}」命中 {len(hits)} 支（須恰 1），請重查')
    return hits[0]


def _add_trigger(tm, entry) -> Change:
    """新增觸發：name/enabled/looping ＋ conditions/effects 列，每項 {type: <parser 方法名>, ...欄位}。
    效果可用 trigger_name 取代 trigger_id（施作時解析）。kind 記為 trigger_add，供 s90 觸發數對帳。"""
    t = tm.add_trigger(entry.get('name', ''), enabled=bool(entry.get('enabled', 1)),
                       looping=bool(entry.get('looping', 0)))
    for c in entry.get('conditions') or []:
        kw = {k: v for k, v in c.items() if k != 'type'}
        getattr(t.new_condition, c['type'])(**kw)
    for e in entry.get('effects') or []:
        kw = {k: v for k, v in e.items() if k != 'type'}
        if 'trigger_name' in kw:
            kw['trigger_id'] = _resolve_by_name(tm, kw.pop('trigger_name'),
                                                f'trigger_add「{entry.get("name", "")}」').trigger_id
        getattr(t.new_effect, e['type'])(**kw)
    summary = f'{len(entry.get("conditions") or [])}條件/{len(entry.get("effects") or [])}效果'
    return Change('s37', 'trigger_add', entry.get('name', ''), 'trigger', '', f'T{t.trigger_id} {summary}',
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

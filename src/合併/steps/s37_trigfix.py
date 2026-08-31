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
    if entry['kind'] == 'effect_add' and 'trigger_id' not in entry:
        # 以名稱指定目標：接「新觸發之間」的線用（新觸發 id 在寫 spec 時不存在），
        # 且可繞過名稱前向引用——先把兩支都新增，再回頭補互指的效果。
        t = _resolve_by_name(tm, entry['target_name'], f'effect_add「{entry["target_name"]}」')
        tid = t.trigger_id
    else:
        tid = entry['trigger_id']
        t = tm.triggers[tid]
        if (t.name or '') != entry.get('name', ''):
            raise BuildError(f'缺裁決：T{tid} 名稱「{t.name}」≠ spec 預期「{entry.get("name", "")}」，'
                             f'基底觸發編號可能位移，請重查')
    kind = entry['kind']
    if kind == 'effect_add':                      # 尾端新增效果：啟停（id+名防呆，或以名指）或座位私訊
        spec = entry['effect']
        tag = f'T{tid}「{t.name}」effect_add'
        if spec['type'] == 'send_chat':
            t.new_effect.send_chat(source_player=spec['source_player'], message=spec['message'])
            return Change('s37', 'effect_add', tag, 'send_chat', '',
                          f'sp{spec["source_player"]}「{spec["message"][:20]}」', entry.get('reason', ''))
        if spec['type'] not in ('activate_trigger', 'deactivate_trigger'):
            raise BuildError(f'缺裁決：{tag} 只支援 activate/deactivate_trigger/send_chat，得到 {spec["type"]}')
        if 'trigger_name' in spec:
            target = _resolve_by_name(tm, spec['trigger_name'], tag)
        else:
            target = tm.triggers[spec['trigger_id']] if 0 <= spec['trigger_id'] < len(tm.triggers) else None
            if target is None or (target.name or '') != spec.get('target_name', ''):
                raise BuildError(f'缺裁決：{tag} 目標 T{spec["trigger_id"]} 名稱'
                                 f'「{getattr(target, "name", None)}」≠ spec 預期「{spec.get("target_name", "")}」，請重查')
        getattr(t.new_effect, spec['type'])(trigger_id=target.trigger_id)
        return Change('s37', 'effect_add', tag, spec['type'], '',
                      f'→T{target.trigger_id}「{target.name}」', entry.get('reason', ''))
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


def _build_part(factory, spec, tag, player_fields=('source_player',)):
    """依 spec 建一個條件／效果。parser 方法簽名沒有的欄位（如 object_hp 的 source_player）
    在建立後直接寫入——parser 對這類欄位會塞預設值（實測 object_hp 預設 sp=1），
    留著會讓 s39 盤點誤判成跨職業（cross）而不生座位變體。欄位不存在即 BuildError。"""
    import inspect
    kw = {k: v for k, v in spec.items() if k != 'type'}
    meth = getattr(factory, spec['type'], None)
    if meth is None:
        raise BuildError(f'缺裁決：{tag} parser 沒有 {spec["type"]} 這個方法，請重查')
    sig = inspect.signature(meth)
    if any(p.kind == p.VAR_KEYWORD for p in sig.parameters.values()):
        return meth(**kw)                      # 測試假件（Recorder）：全部照傳
    extra = {k: kw.pop(k) for k in list(kw) if k not in sig.parameters}
    obj = meth(**kw)
    for k, v in extra.items():
        if not hasattr(obj, k):
            raise BuildError(f'缺裁決：{tag} 欄位 {k} 不存在於 {spec["type"]}，請重查')
        setattr(obj, k, v)
    # 幽靈玩家欄防呆（2026-08-31 教訓）。只檢查 revive_inventory 實際會讀的欄位：
    # 條件讀 source_player、效果讀 source_player 與 target_player；條件的 target_player 不影響分類。
    for fld in player_fields:
        if fld in spec:
            continue
        v = getattr(obj, fld, -1)
        if v is not None and 1 <= v <= 6:
            raise BuildError(
                f'缺裁決：{tag} 的 {spec["type"]} 沒指定 {fld}，但 parser 預設塞了 {fld}={v}。'
                f'留著會讓 s39 盤點把它算成「碰到玩家 {v}」→ 誤判跨職業 cross、不生座位變體、'
                f'啟停邊也不重指（實例：object_hp 預設 sp=1）。請在 spec 明確寫 {fld}（中性用 -1）')
    return obj


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
    tag = f'trigger_add「{entry.get("name", "")}」'
    for c in entry.get('conditions') or []:
        _build_part(t.new_condition, c, tag)
    for e in entry.get('effects') or []:
        spec = dict(e)
        if 'trigger_name' in spec:
            spec['trigger_id'] = _resolve_by_name(tm, spec.pop('trigger_name'), tag).trigger_id
        _build_part(t.new_effect, spec, tag, player_fields=('source_player', 'target_player'))
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

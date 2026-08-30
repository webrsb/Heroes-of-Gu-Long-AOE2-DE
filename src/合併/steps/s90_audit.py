# -*- coding: utf-8 -*-
"""s90 終檢不變量（spec §8）。任一失敗 → BuildError 中止、不出檔。

object refs 採「基線豁免」：origin 本來就 dangling 的引用不算違規
（build.py 開跑時把 origin 的 dangling 集合存進 ctx.notes['baseline_dangling']），
只有建置過程新增的 dangling 才擋。
"""
from AoE2ScenarioParser.datasets.effects import EffectId
from core.change import Change
from analysis.dependency import build_unit_index
from .base import Step, BuildError
from .s30_attackfix import needs_fix

_ACT = {int(EffectId.ACTIVATE_TRIGGER), int(EffectId.DEACTIVATE_TRIGGER)}


def check_attack(scn):
    return [f'T{t.trigger_id}「{t.name}」效果{i} 攻擊力編碼仍壞（quantity={e.quantity}）'
            for t in scn.trigger_manager.triggers
            for i, e in enumerate(t.effects) if needs_fix(e)]


def check_trigger_refs(scn):
    n = len(scn.trigger_manager.triggers)
    return [f'T{t.trigger_id}「{t.name}」效果{i} trigger_id={e.trigger_id} 超界(0~{n-1})'
            for t in scn.trigger_manager.triggers
            for i, e in enumerate(t.effects)
            if int(e.effect_type) in _ACT and e.trigger_id is not None
            and not (e.trigger_id == -1 or 0 <= e.trigger_id < n)]


def collect_dangling(scn):
    idx = build_unit_index(scn)
    dangling = set()
    for t in scn.trigger_manager.triggers:
        for e in t.effects:
            for r in (e.selected_object_ids or []):
                if r >= 0 and r not in idx:
                    dangling.add(r)
            loc = getattr(e, 'location_object_reference', None)
            if loc is not None and loc >= 0 and loc not in idx:
                dangling.add(loc)
    return dangling


def check_object_refs(scn, baseline):
    new_dangling = collect_dangling(scn) - set(baseline)
    return [f'物件引用 ref{r} 不存在（建置過程新增的 dangling）'
            for r in sorted(new_dangling)]


def check_reconciliation(scn, notes):
    init = notes.get('initial_trigger_count')
    if init is None:
        return []
    added = sum(1 for c in notes.get('all_changes', []) if c.kind == 'trigger_add')
    actual = len(scn.trigger_manager.triggers)
    if actual != init + added:
        return [f'觸發數對帳失敗：初始 {init} ＋ 宣告新增 {added} ≠ 實際 {actual}']
    return []


def check_no_empty_effects(scn):
    """管線中和殼（type 0）不得落檔（s80 應已清空；殘留代表 s80 之後又有步驟中和）。"""
    out = []
    for t in scn.trigger_manager.triggers:
        idx = [i for i, e in enumerate(t.effects) if int(e.effect_type) == 0]
        if idx:
            out.append(f'T{t.trigger_id}「{t.name}」殘留 {len(idx)} 個空效果殼 E{idx}')
    return out


def check_boss_refs(spec, notes):
    targets = (spec.params.get('boss_hp') or {}).get('targets') or []
    refs = notes.get('boss_refs') or {}
    return [f'雙0血目標「{t["label"]}」未被 s40 定位' for t in targets
            if t['label'] not in refs]


class AuditStep(Step):
    id = 's90'
    title = '終檢'
    intro = '六項不變量稽核（spec §8 五項＋空效果殼零殘留），任一失敗即中止建置。'

    def apply(self, ctx):
        violations = []
        violations += check_attack(ctx.base)
        violations += check_trigger_refs(ctx.base)
        violations += check_object_refs(ctx.base, ctx.notes.get('baseline_dangling', set()))
        violations += check_reconciliation(ctx.base, ctx.notes)
        violations += check_boss_refs(ctx.spec, ctx.notes)
        violations += check_no_empty_effects(ctx.base)
        if violations:
            raise BuildError('終檢未過：\n  ' + '\n  '.join(violations))
        return [Change(self.id, 'audit', '全檔', '—', '', '6/6 通過', 'spec §8＋空殼')]


STEP = AuditStep()

# -*- coding: utf-8 -*-
"""s10 自動搬運器：把 merge_spec 圈為 auto 的劍譜5 觸發組＋所屬物件搬進無法無天。

流程：
  1. 建立配對表存回 ctx.pairing（後續 step 共用）
  2. 每個 auto 群：deepcopy 觸發 → 記錄跨界啟動引用（import_triggers 會把
     指向搬入集合外的 trigger_id 重設為 -1）→ 搬運獨有物件 → import → 回填跨界引用
  3. 任何 spec 未覆蓋的衝突（掛點配不到、ref 衝突）→ BuildError 列缺哪條裁決
"""
import copy
from AoE2ScenarioParser.datasets.effects import EffectId
from core.change import Change
from analysis.pairing import pair_triggers
from analysis.dependency import collect_object_refs, build_unit_index
from .base import Step, BuildError

_ACT = {int(EffectId.ACTIVATE_TRIGGER), int(EffectId.DEACTIVATE_TRIGGER)}


def plan_cross_refs(triggers, member_ids, pairing, group_name):
    """回傳 [(copy_idx, effect_idx, base_target_id)]；配不到的收集後一次 BuildError。"""
    plan, missing = [], []
    for ci, t in enumerate(triggers):
        for ei, e in enumerate(t.effects):
            if int(e.effect_type) in _ACT and e.trigger_id is not None \
                    and e.trigger_id >= 0 and e.trigger_id not in member_ids:
                b_id = pairing.a2b.get(e.trigger_id)
                if b_id is None:
                    missing.append(f'觸發「{t.name}」(id {t.trigger_id}) 效果{ei} → a側 {e.trigger_id}')
                else:
                    plan.append((ci, ei, b_id))
    if missing:
        raise BuildError(f'缺裁決：群「{group_name}」有啟動邊在基底配不到掛點，'
                         f'需改 patch 或在 spec 排除：' + '；'.join(missing))
    return plan


class TransplantStep(Step):
    id = 's10'
    title = '自動搬運'
    intro = '把 merge_spec 圈為 auto 的劍譜5 觸發組與所屬物件搬進無法無天基底。'

    def apply(self, ctx):
        changes = []
        ctx.pairing = pair_triggers(ctx.source.trigger_manager.triggers,
                                    ctx.base.trigger_manager.triggers)
        auto_groups = [g for g in ctx.spec.groups if g.action == 'auto']
        if not auto_groups:
            return changes
        src_by_id = {t.trigger_id: t for t in ctx.source.trigger_manager.triggers}
        idx_src = build_unit_index(ctx.source)
        idx_base = build_unit_index(ctx.base)
        for g in auto_groups:
            members = set(g.trigger_ids)
            originals = [src_by_id[i] for i in sorted(members)]
            copies = copy.deepcopy(originals)
            refill = plan_cross_refs(copies, members, ctx.pairing, g.name)
            # 物件搬運（在 import 前，衝突先擋）
            need_refs = collect_object_refs(originals)
            collisions = [r for r in need_refs
                          if r in idx_src and r in idx_base and idx_src[r] != idx_base[r]]
            if collisions:
                raise BuildError(f'缺裁決：群「{g.name}」引用的 ref {collisions} '
                                 f'在兩版是不同物件（衝突類型2），需手寫補丁')
            for r in sorted(need_refs):
                if r in idx_src and r not in idx_base:
                    p, const, _, _ = idx_src[r]
                    u = next(u for u in ctx.source.unit_manager.units[p]
                             if u.reference_id == r)
                    ctx.base.unit_manager.add_unit(
                        player=p, unit_const=u.unit_const, x=u.x, y=u.y, z=u.z,
                        rotation=u.rotation, reference_id=r)
                    idx_base[r] = idx_src[r]
                    changes.append(Change(self.id, 'unit_add', f'ref{r} const{const}',
                                          '—', '—', f'P{p} ({u.x},{u.y})',
                                          f'merge_spec: {g.name}'))
            imported = ctx.base.trigger_manager.import_triggers(copies, deepcopy=False)
            for t in imported:
                changes.append(Change(self.id, 'trigger_add',
                                      f'T{t.trigger_id}「{t.name}」', '—', '—',
                                      '(來自劍譜5)', f'merge_spec: {g.name}'))
            for ci, ei, b_id in refill:
                eff = imported[ci].effects[ei]
                old = eff.trigger_id
                eff.trigger_id = b_id
                changes.append(Change(self.id, 'remap',
                                      f'T{imported[ci].trigger_id}「{imported[ci].name}」效果{ei}',
                                      'trigger_id', str(old), str(b_id),
                                      '跨界掛點回填（配對表）'))
        return changes

    def test_guide(self, changes):
        groups = sorted({c.reason.replace('merge_spec: ', '') for c in changes
                         if c.reason.startswith('merge_spec')})
        return (f'搬入群：{"、".join(groups)}。\n'
                '怎麼測：進遊戲逐群觸發其入口（盤點報告各群明細有觸發名單），確認功能動作；\n'
                '同時抽測基底原主線一項（任選熟悉的任務）確認未壞。\n'
                '異常判讀：搬入功能無反應＝掛點斷線，回報群名；基底主線壞掉＝搬運污染，立即回報。')


STEP = TransplantStep()

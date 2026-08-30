# -*- coding: utf-8 -*-
"""s80 清空殼：把管線中和成 effect_type=0 的效果殼在寫檔前真刪。

為什麼有殼：s39（拆分/騎池/連動剝除）與 s375（Joan 重置抽除）為保住步驟內的效果索引，
把效果就地轉 type 0（`revive_mount.neutralize_effect`）。引擎會略過 type 0，但殼寫進檔案後
DE 編輯器把整支觸發標紅（2026-08-30 使用者截圖：402 支/2409 殼）。殼是建置中間態，不該落檔。

為什麼自己重排 display order：parser 的 `Trigger.remove_effect` 刪除後只把 order 陣列中
≥ 新長度的值濾掉、不重新編號，顯示順序非恆等（產物有 116 支）時會錯位。本步先讀舊 order，
刪殼後以「刪除點前方位移」重算：new = [x − #(deleted < x) for x in old if x ∉ deleted]。
"""
from core.change import Change
from .base import Step

EMPTY = 0


def _remap(order, deleted):
    ds = sorted(deleted)
    return [x - sum(1 for d in ds if d < x) for x in order if x not in deleted]


def prune_empty_effects(tm):
    changes = []
    for t in tm.triggers:
        deleted = [i for i, e in enumerate(t.effects) if getattr(e, 'effect_type', None) == EMPTY]
        if not deleted:
            continue
        old_order = getattr(t, 'effect_order', None)
        new_order = _remap(list(old_order), deleted) if old_order is not None else None
        n_before = len(t.effects)
        for i in reversed(deleted):
            del t.effects[i]
        if new_order is not None:
            t.effect_order = new_order
        changes.append(Change('s80', 'eff_prune', f'T{t.trigger_id}', 'effects',
                              str(n_before), str(len(t.effects)),
                              f'刪 {len(deleted)} 個中和殼 E{deleted}'))
    return changes


class PruneStep(Step):
    id = 's80'
    title = '清空殼'
    intro = '真刪管線中和（type 0）的效果殼並重排 display order；s90 第六項不變量擋殘留。'

    def apply(self, ctx):
        return prune_empty_effects(ctx.base.trigger_manager)

    def test_guide(self, changes):
        n = sum(int(c.old) - int(c.new) for c in changes)
        return (f'清空殼：{len(changes)} 支觸發刪 {n} 個殼。編輯器（僅開檔檢視、絕不存檔）'
                '「1升級」「3-6打坐◇騎池1」等不再紅字；殼原本就不執行，遊戲內行為應無差。\n'
                '陽性對照：科技/名 仍紅（來源就有的 -2147483648 改血，待溢位裁決，非本步範圍）。')


STEP = PruneStep()

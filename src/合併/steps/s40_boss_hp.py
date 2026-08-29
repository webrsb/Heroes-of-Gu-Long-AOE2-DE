# -*- coding: utf-8 -*-
"""s40 雙0血。配方出自 verify/01n（NAKUZ Q61 第一步，實機 N1/N3 存活驗證）：

    Change Object HP ADD(65536 − A) → 最大血量 int16 回繞成 0
    → 建築物當前血量夾限失效，本體既有的灌血效果照常把血池灌大。

A（該物件屆時的有效最大血量）無法靜態推得 —— 本體自身的 ΔmaxHP 觸發
會在開場後陸續執行，所以 wrap_add = 65536 − A 是 merge_spec 的校正參數：
首輪用估值 → 使用者實機看 tooltip 回報 → 修參數重建（見 test_guide）。
"""
from AoE2ScenarioParser.datasets.trigger_lists import Operation
from core.change import Change
from analysis.dependency import build_unit_index
from .base import Step, BuildError


def locate_target(idx, unit_const, tile, label) -> int:
    hits = [r for r, (p, c, x, y) in idx.items()
            if c == unit_const and (int(x), int(y)) == tuple(tile)]
    if len(hits) != 1:
        raise BuildError(f'缺裁決：目標「{label}」在基底 tile{tuple(tile)} '
                         f'找到 {len(hits)} 個 const {unit_const}（需正好 1 個）：{hits}')
    return hits[0]


class BossHpStep(Step):
    id = 's40'
    title = '雙0血'
    intro = '對指定魔王/邊界目標套 65536−A 回繞，使最大血量歸 0、解除建築夾血（§5.6/01n）。'

    def apply(self, ctx):
        changes = []
        targets = (ctx.spec.params.get('boss_hp') or {}).get('targets') or []
        if not targets:
            return changes
        idx = build_unit_index(ctx.base)
        ctx.notes['boss_refs'] = {}
        t = ctx.base.trigger_manager.add_trigger('ZZ_雙0血', enabled=True, looping=False)
        for tg in targets:
            ref = locate_target(idx, tg['unit_const'], tg['tile'], tg['label'])
            ctx.notes['boss_refs'][tg['label']] = ref
            t.new_effect.change_object_hp(
                quantity=int(tg['wrap_add']),
                operation=int(Operation.ADD),
                selected_object_ids=[ref])
            changes.append(Change(self.id, 'unit', f'ref{ref} {tg["label"]}',
                                  'max_hp', 'A', f'ADD {tg["wrap_add"]} → 0(回繞)',
                                  '§5.6/01n 雙0血'))
        changes.append(Change(self.id, 'trigger_add', f'T{t.trigger_id}「ZZ_雙0血」',
                              '—', '—', f'{len(targets)} 個效果', '§5.7'))
        return changes

    def test_guide(self, changes):
        labels = [c.target.split(' ', 1)[1] for c in changes if c.kind == 'unit']
        return (f'目標 {"、".join(labels)} 已套雙0血（wrap_add 目前是估值）。\n'
                '怎麼測：進遊戲滑鼠移到各目標上看 tooltip；派兵打亡魂之堡 30 秒。\n'
                '預期：tooltip 顯示「生命 0」；血持續下降、不回滿、不被秒殺。\n'
                '異常A：tooltip 是正數 N ＝ wrap_add 錯，回報 N（我改成 65536−N 重建）。\n'
                '異常B：一打就死或完全打不動＝灌血順序問題，回報現象與截圖。')


STEP = BossHpStep()

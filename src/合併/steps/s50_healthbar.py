# -*- coding: utf-8 -*-
"""s50 caption 血條。規格：遷移記錄 §5.7a（樣式 3，使用者 2026-08-29 選定）：

    亡魂之堡 [####______] 40%

caption 限制（ZZ_test15 系列實測）：只能 ASCII＋中日韓（全形％/方塊字元變豆腐）、
不支援變數代入 → 每 1% 一支固定文字觸發（99 階，100% 是初始態不需觸發）。
caption 綁物件，玩家看得到目標才看得到字 → 不需距離開關/遲滯/清除。

params.healthbar.enabled=false 時整步 no-op —— start_hp 要等 s40 實測回報後才有真值。
"""
from AoE2ScenarioParser.datasets.trigger_lists import Comparison
from core.change import Change
from .base import Step, BuildError


def bar_text(name: str, pct: int) -> str:
    filled = pct // 10
    return f'{name} [{"#" * filled}{"_" * (10 - filled)}] {pct}%'


def thresholds(start_hp: float):
    return [(pct, start_hp * pct / 100) for pct in range(99, 0, -1)]


class HealthbarStep(Step):
    id = 's50'
    title = 'caption血條'
    intro = '為魔王目標生成 99 階 caption 血條（樣式 3，§5.7a）。'

    def apply(self, ctx):
        changes = []
        hb = ctx.spec.params.get('healthbar') or {}
        if not hb.get('enabled'):
            return changes
        boss_refs = ctx.notes.get('boss_refs') or {}
        tm = ctx.base.trigger_manager
        rung_ids = []
        for tg in hb.get('targets') or []:
            label = tg['label']
            ref = boss_refs.get(label)
            if ref is None:
                raise BuildError(f'缺裁決：血條目標「{label}」不在 s40 boss_refs 中'
                                 f'（先在 params.boss_hp.targets 補上同 label）')
            name = tg.get('display_name', label)
            for pct, hp in thresholds(float(tg['start_hp'])):
                # enabled=False：血池要到 t≈10 才灌滿，太早啟動會被低血量期
                # 一路誤燒到 1%（階梯非循環、只發一次）。t=activate_at 統一啟動。
                t = tm.add_trigger(f'ZZ_血條_{label}_{pct:02d}',
                                   enabled=False, looping=False)
                t.new_condition.object_hp(quantity=int(hp), unit_object=ref,
                                          comparison=int(Comparison.LESS))
                t.new_effect.change_object_caption(message=bar_text(name, pct),
                                                   selected_object_ids=[ref])
                rung_ids.append(t.trigger_id)
                changes.append(Change(self.id, 'trigger_add',
                                      f'T{t.trigger_id}「ZZ_血條_{label}_{pct:02d}」',
                                      'threshold', '—', f'HP<{int(hp)}',
                                      '§5.7a 樣式3'))
        act_at = int(hb.get('activate_at', 20))
        ta = tm.add_trigger('ZZ_血條_啟動', enabled=True, looping=False)
        ta.new_condition.timer(timer=act_at)
        for rid in rung_ids:
            ta.new_effect.activate_trigger(trigger_id=rid)
        changes.append(Change(self.id, 'trigger_add', f'T{ta.trigger_id}「ZZ_血條_啟動」',
                              'timer', '—', f't={act_at}s 啟動 {len(rung_ids)} 階',
                              '血池 t≈10 才灌滿，延後啟動防誤燒'))
        return changes

    def test_guide(self, changes):
        return ('血條已生成（每目標 99 階）。\n'
                '怎麼測：派兵持續攻擊亡魂之堡與聚魂塔。\n'
                '預期：物件上方浮字從 99% 逐步下降、格數同步減少、% 為半形不豆腐。\n'
                '異常判讀：字不出現＝條件門檻全錯（start_hp 錯），回報當時 tooltip 血量；\n'
                '百分比跳動異常＝start_hp 偏差，回報實際起始血量。')


STEP = HealthbarStep()

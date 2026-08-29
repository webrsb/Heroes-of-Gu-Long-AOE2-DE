# -*- coding: utf-8 -*-
"""s40 雙0血（2026-08-29 第六輪重構：確定性版）。

前五輪教訓：本體在 t=0 之後仍會多次 ADD 最大血量（客棧 −4500、塔魂 −100、
開門 +32767…），任何「猜有效 max 再回繞」的做法都會被後手推成負 max 而暴斃。

新做法——max 的控制權完全收歸我方：
  1. **歸零本體的 max 操作**：所有命中目標的 Change Object HP 效果 quantity→0。
     例外：quantity=+32767 是 AoC 的「回繞負 max 殺牆開門」慣用寫法，
     依原意改成 Kill Object（目標欄位原樣保留）。
     若某效果的目標集合不完全落在 13 目標內 → BuildError 缺裁決。
  2. **確定性回繞**：目標的 max 從此恆為檔案基血（已知常數：城堡 4800、
     守衛塔 1500、柵欄牆 250），t=0 ADD (65536 − 基血) → 0，同觸發立刻灌血
     （01n N1 配方——max→0 會把當前血量等比縮放歸 0，必須馬上補）。

犧牲品（記錄於異動檔）：本體 boss 階段的 max 增益（+1500/+1300/+12000）失效，
那些在 DE 會重新啟動夾血、摧毀血池，屬於必須捨棄的 AoC 專屬寫法。
"""
from AoE2ScenarioParser.datasets.effects import EffectId
from AoE2ScenarioParser.datasets.trigger_lists import Operation
from core.change import Change
from analysis.dependency import build_unit_index, effect_target_refs
from .base import Step, BuildError
from .s30_attackfix import as_int16

_CH_HP = int(EffectId.CHANGE_OBJECT_HP)
_KILL = int(EffectId.KILL_OBJECT)
_DMG = int(EffectId.DAMAGE_OBJECT)
_GATE_Q = 32767   # AoC「殺牆開門」慣用值


def locate_target(idx, unit_const, tile, label) -> int:
    hits = [r for r, (p, c, x, y) in idx.items()
            if c == unit_const and (int(x), int(y)) == tuple(tile)]
    if len(hits) != 1:
        raise BuildError(f'缺裁決：目標「{label}」在基底 tile{tuple(tile)} '
                         f'找到 {len(hits)} 個 const {unit_const}（需正好 1 個）：{hits}')
    return hits[0]


def classify_hp_effect(quantity, hit_refs, boss_refs):
    """命中 boss 的 ChangeHP 效果處置：
    'kill'（+32767 開門）/'zero'（歸零）/'split'（目標混雜，改指名非目標）/'conflict'。"""
    if not hit_refs & boss_refs:
        return None
    if not hit_refs <= boss_refs:
        return 'conflict' if quantity == _GATE_Q else 'split'
    return 'kill' if quantity == _GATE_Q else 'zero'


class BossHpStep(Step):
    id = 's40'
    title = '雙0血'
    intro = ('歸零本體對魔王/邊界目標的所有 max 操作（+32767 開門改 Kill Object），'
             '再以基血常數回繞 max→0 並立即灌血（§5.6/01n，確定性版）。')

    def apply(self, ctx):
        changes = []
        targets = (ctx.spec.params.get('boss_hp') or {}).get('targets') or []
        if not targets:
            return changes
        idx = build_unit_index(ctx.base)
        ctx.notes['boss_refs'] = {}
        for tg in targets:
            tg['_ref'] = locate_target(idx, tg['unit_const'], tg['tile'], tg['label'])
            ctx.notes['boss_refs'][tg['label']] = tg['_ref']
        boss_refs = set(ctx.notes['boss_refs'].values())

        # 1. 等價遷移本體的 max 操作（原有功能不刪除）：
        #    AoC 改 max 會等比帶動當前血量；雙0血下 max 恆為 0，
        #    故把每個 max 操作換成對當前血量的同量增減（Damage 負值＝增），
        #    數值先用 as_int16 還原 65536−N 回繞寫法（+55537 其實是 −9999）。
        #    +32767 是「回繞負 max 殺牆開門」→ 依原意改 Kill Object。
        conflicts, plan = [], []
        for t in ctx.base.trigger_manager.triggers:
            for i, e in enumerate(t.effects):
                if int(e.effect_type) != _CH_HP or not e.quantity:
                    continue
                hit = effect_target_refs(e, idx)
                act = classify_hp_effect(e.quantity, hit, boss_refs)
                if act is None:
                    continue
                if act == 'conflict':
                    conflicts.append(f'T{t.trigger_id}「{t.name}」效果{i} '
                                     f'開門效果同時命中非目標 {sorted(hit - boss_refs)[:5]}')
                else:
                    plan.append((t, i, e, hit, act))
        if conflicts:
            raise BuildError('缺裁決：' + '；'.join(conflicts))
        for t, i, e, hit, act in plan:
            tag = f'T{t.trigger_id}「{t.name}」效果{i}'
            sem = as_int16(e.quantity)   # 作者語意值（還原回繞寫法）
            if act == 'kill':
                e.effect_type = _KILL
                changes.append(Change(self.id, 'effect', tag, 'effect_type',
                                      f'ChangeHP +{_GATE_Q}', 'KillObject',
                                      'AoC 回繞殺牆開門 → 依原意改摧毀'))
            elif act == 'zero':
                old_q = e.quantity
                e.effect_type = _DMG
                e.quantity = -sem   # max+Δ ⇒ 當前血量+Δ（Damage 負值＝增）
                changes.append(Change(self.id, 'effect', tag, 'effect_type/quantity',
                                      f'ChangeHP Δmax {old_q}（語意 {sem:+}）',
                                      f'Damage {-sem:+}（當前血量 {sem:+}）',
                                      '等價遷移：max 操作 → 當前血量操作'))
            else:  # split：非目標保留原 max 語意，魔王部分補等價當前血量效果
                keep = sorted(hit - boss_refs)
                bosses = sorted(hit & boss_refs)
                e.selected_object_ids = keep
                comp = t.new_effect.damage_object(quantity=-sem,
                                                  selected_object_ids=bosses)
                changes.append(Change(self.id, 'effect', tag, 'targets',
                                      f'區域過濾(混雜 {len(bosses)} 個魔王目標)',
                                      f'原效果限縮至 {keep}；魔王改補 Damage {-sem:+}',
                                      '等價遷移：目標混雜分拆'))

        # 2. 確定性回繞＋灌血（同觸發成對）
        t = ctx.base.trigger_manager.add_trigger('ZZ_雙0血', enabled=True, looping=False)
        for tg in targets:
            ref = tg['_ref']
            wrap = 65536 - int(tg['base_hp'])
            t.new_effect.change_object_hp(quantity=wrap,
                                          operation=int(Operation.ADD),
                                          selected_object_ids=[ref])
            t.new_effect.damage_object(quantity=-int(tg['heal']),
                                       selected_object_ids=[ref])
            changes.append(Change(self.id, 'unit', f'ref{ref} {tg["label"]}',
                                  'max_hp', str(tg['base_hp']), f'ADD {wrap} → 0(回繞)',
                                  '§5.6/01n 雙0血'))
            changes.append(Change(self.id, 'unit', f'ref{ref} {tg["label"]}',
                                  'current_hp', '0(縮放歸零)', f'+{tg["heal"]}(灌血)',
                                  '01n N1 第二步'))
        changes.append(Change(self.id, 'trigger_add', f'T{t.trigger_id}「ZZ_雙0血」',
                              '—', '—', f'{len(t.effects)} 個效果', '§5.7'))
        return changes

    def test_guide(self, changes):
        n_kill = sum(1 for c in changes if c.new == 'KillObject')
        n_zero = sum(1 for c in changes if c.field == 'quantity' and c.new == '0')
        return (f'確定性雙0血：歸零本體 {n_zero} 個 max 操作、{n_kill} 個開門效果改為直接摧毀。\n'
                '怎麼測：開場確認亡魂之堡、聚魂塔（守衛塔外觀）、界線牆都站著；\n'
                '等 15 秒後看 tooltip——三類目標都應「生命 0」；派兵打城堡與塔各 30 秒，持續掉血不回滿。\n'
                '重點驗開門：清光任一段界線的小兵，該段牆應直接消失（原 +32767 開門已改 Kill）。\n'
                '異常判讀：誰倒了回報名字；tooltip 有正數回報數字；牆不消失回報「開門失敗」。')


STEP = BossHpStep()

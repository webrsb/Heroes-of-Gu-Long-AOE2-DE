# -*- coding: utf-8 -*-
"""s374 野怪平衡曲線（params.mob_balance；spec docs/superpowers/specs/2026-09-01-野怪平衡曲線-design.md）。

生成觸發結構＝每建立點「移除(15)→建立(11)→改血(27,格)→改攻(28,格)」＋部分觸發的全域 28。
本步把每格 27 改成 hp−base_hp、每格 28 改成 atk−base_atk，沿用 class0/ADD 慣例
（s30 已先把全檔 28 正規化為 class0），全域 28 一律歸零（總量已折入格效果）。
hp: null＝表二血不動。差值必 ≥0（設計夾0）且 ≤int16。
渦鬼(2713/2714)、頭目、表三不入表＝維持現值。觸發名比對防基底位移（同 s373）。"""
from AoE2ScenarioParser.datasets.trigger_lists import Operation
from core.change import Change
from .base import trig_by_id, Step, BuildError

CREATE, CH_HP, CH_ATK, P7 = 11, 27, 28, 7
ADD = int(Operation.ADD)


def _tile(e):
    return (e.area_x1, e.area_y1, e.area_x2, e.area_y2)


def _delta(target, base, tag, what):
    d = int(target) - int(base)
    if d < 0:
        raise BuildError(f'缺裁決：{tag} {what} 目標 {target} 低於基礎 {base}（夾0 應在設計表處理）')
    if d > 32767:
        raise BuildError(f'缺裁決：{tag} {what} 差值 {d} 超過 int16')
    return d


def _set_atk(e, amount):
    e.operation = ADD
    e.armour_attack_class = 0
    e.armour_attack_quantity = amount


def apply_mob_balance(tm, rows):
    changes = []
    table = {}
    for r in rows:
        key = (int(r['tid']), int(r['const']))
        if key in table:
            raise BuildError(f'缺裁決：mob_balance (tid,const)={key} 重複')
        table[key] = r
    for tid in sorted({k[0] for k in table}):
        rows_t = {c: r for (t_, c), r in table.items() if t_ == tid}
        name = next(iter(rows_t.values()))['name']
        t = trig_by_id(tm, tid)
        if t is None or (t.name or '') != name:
            raise BuildError(f'缺裁決：T{tid} 名稱「{getattr(t, "name", None)}」≠ 預期「{name}」，'
                             f'基底觸發編號可能位移')
        tag = f'T{tid}「{name}」'
        creates = [e for e in t.effects
                   if getattr(e, 'effect_type', None) == CREATE and getattr(e, 'source_player', -1) == P7
                   and getattr(e, 'location_x', -1) not in (-1, None)]
        present = {e.object_list_unit_id for e in creates}
        missing, unused = present - set(rows_t), set(rows_t) - present
        if missing:
            raise BuildError(f'缺裁決：{tag} 建立單位 const {sorted(missing)} 無對照行')
        if unused:
            raise BuildError(f'缺裁決：{tag} 對照行 const {sorted(unused)} 未出現於觸發')
        tiles = [((e.location_x, e.location_y), e.object_list_unit_id) for e in creates]
        if len({xy for xy, _ in tiles}) != len(tiles):
            raise BuildError(f'缺裁決：{tag} 多個建立效果共用同一格，格效果無法歸屬')
        for (x, y), const in tiles:
            r = rows_t[const]
            area = (x, y, x, y)

            def scoped(e, et, area=area, const=const):
                return (getattr(e, 'effect_type', None) == et and _tile(e) == area
                        and getattr(e, 'object_list_unit_id', -1) in (-1, const))

            hps = [e for e in t.effects if scoped(e, CH_HP)]
            atks = [e for e in t.effects if scoped(e, CH_ATK)]
            if r.get('hp') is not None:
                if not hps:
                    raise BuildError(f'缺裁決：{tag} 格({x},{y}) 無 ChangeHP 效果')
                d = _delta(r['hp'], r['base_hp'], tag, '血')
                old = hps[0].quantity
                hps[0].quantity = d
                for e in hps[1:]:
                    e.quantity = 0
                changes.append(Change('s374', 'effect', f'{tag}({x},{y})', 'hp_add',
                                      str(old), str(d), f"Lv{r['lv']} 目標血 {r['hp']}"))
            if not atks:
                raise BuildError(f'缺裁決：{tag} 格({x},{y}) 無 ChangeAttack 效果')
            d = _delta(r['atk'], r['base_atk'], tag, '攻')
            old = getattr(atks[0], 'armour_attack_quantity', atks[0].quantity)
            _set_atk(atks[0], d)
            for e in atks[1:]:
                _set_atk(e, 0)
            changes.append(Change('s374', 'effect', f'{tag}({x},{y})', 'atk_add',
                                  str(old), str(d), f"Lv{r['lv']} 目標攻 {r['atk']}（{r['kind']}）"))
        for e in t.effects:
            if getattr(e, 'effect_type', None) == CH_ATK and _tile(e) == (-1, -1, -1, -1):
                old = getattr(e, 'armour_attack_quantity', e.quantity)
                _set_atk(e, 0)
                changes.append(Change('s374', 'effect', tag, 'global_atk',
                                      str(old), '0', '全域加攻歸零，總量折入格效果'))
    return changes


class MobBalanceStep(Step):
    id = 's374'
    title = '野怪平衡曲線'
    intro = ('生成觸發加血/加攻改寫為曲線目標（DPS 7.5×1.051^Lv、血 70×1.042^Lv，'
             '遠程×0.7/快速×0.85）；渦鬼與頭目維持現值。無 mob_balance 參數時跳過。')

    def apply(self, ctx):
        rows = ctx.spec.params.get('mob_balance')
        if not rows:
            return []
        return apply_mob_balance(ctx.base.trigger_manager, rows)

    def test_guide(self, changes):
        n = sum(1 for c in changes if c.kind == 'effect')
        return (f'野怪平衡：{n} 筆加值改寫。單人驗（新手體驗）：開場站著給民團打，'
                '約 10–11 刀才倒（現況 4 刀）；Lv9 獵人單下傷害應高於 Lv4 山賊；'
                'Lv87 狂屍應明顯強於 Lv66 赤武（單下約 1,081 vs 331）。\n'
                '陽性對照：渦鬼（珠光/殺人）與首領/豬王/靈象數值不變；'
                '渦鬼殺人仍一刀 2 萬級＝沒有全表誤縮。')


STEP = MobBalanceStep()

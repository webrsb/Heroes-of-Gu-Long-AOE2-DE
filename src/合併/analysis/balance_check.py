# -*- coding: utf-8 -*-
"""野怪平衡特徵斷言（s91 掛載，回傳 [(ok, msg)]，比照 ferry_check）。

從建置後觸發重推實值：血＝base_hp＋Σ格27、攻＝base_atk＋Σ格28＋Σ全域28（class 必為 0），
與 params.mob_balance 目標對帳；另斷言表本身對 Lv 單調（近戰基準 DPS 與血，2% 容差吸收取整）。

常數與 tile 過濾語意鏡像 steps/s374_mobbalance.py（寫入端），兩邊改動需同步。"""
CREATE, CH_HP, CH_ATK, P7 = 11, 27, 28, 7
DISCOUNT = {'m': 1.0, 'r': 0.7, 'f': 0.85, 'rf': 0.6}


def _tile(e):
    return (e.area_x1, e.area_y1, e.area_x2, e.area_y2)


def _trig(tm, tid):
    """觸發查找：假件走 triggers_by_id；真 parser 用 triggers[tid]（append-only，id==index）。
    語意等價 steps.base.trig_by_id；本模組刻意不 import steps，保持獨立驗證（不信任寫入端邏輯）。"""
    d = getattr(tm, 'triggers_by_id', None)
    if d is not None:
        return d.get(tid)
    ts = tm.triggers
    if 0 <= tid < len(ts) and ts[tid].trigger_id == tid:
        return ts[tid]
    for t in ts:                      # 保底線性掃（不應發生）
        if t.trigger_id == tid:
            return t
    return None


def _check_reconciliation(tm, rows):
    results = []
    by_tid = {}
    for r in rows:
        by_tid.setdefault(int(r['tid']), {})[int(r['const'])] = r
    for tid, rows_t in sorted(by_tid.items()):
        name = next(iter(rows_t.values()))['name']
        t = _trig(tm, tid)
        if t is None:
            results.append((False, f'T{tid} 名稱「觸發不存在」≠ 預期「{name}」'))
            continue
        if (t.name or '') != name:
            results.append((False, f'T{tid} 名稱「{getattr(t, "name", None)}」≠ 預期「{name}」'))
            continue
        creates = [e for e in t.effects
                   if getattr(e, 'effect_type', None) == CREATE and getattr(e, 'source_player', -1) == P7
                   and getattr(e, 'location_x', -1) not in (-1, None)]
        for ce in creates:
            r = rows_t.get(ce.object_list_unit_id)
            if r is None:
                results.append((False, f'T{tid}「{name}」const {ce.object_list_unit_id} 不在表內'))
                continue
            area = (ce.location_x, ce.location_y, ce.location_x, ce.location_y)
            const = ce.object_list_unit_id
            hp_add = atk_add = 0
            bad_cls = None
            for e in t.effects:
                et = getattr(e, 'effect_type', None)
                scoped = _tile(e) == area and getattr(e, 'object_list_unit_id', -1) in (-1, const)
                glob = _tile(e) == (-1, -1, -1, -1) and getattr(e, 'object_list_unit_id', -1) in (-1, const)
                if et == CH_HP and scoped:
                    hp_add += int(e.quantity or 0)
                elif et == CH_ATK and (scoped or glob):
                    cls = getattr(e, 'armour_attack_class', 0)
                    if cls not in (0, None):
                        bad_cls = cls
                    atk_add += int(getattr(e, 'armour_attack_quantity', None) or 0)
            tag = f'T{tid}「{name}」格({ce.location_x},{ce.location_y})'
            if bad_cls is not None:
                results.append((False, f'{tag} 攻擊效果 class={bad_cls}≠0'))
            if r.get('hp') is not None:
                ok = r['base_hp'] + hp_add == r['hp']
                results.append((ok, f'{tag} 血 {r["base_hp"]}+{hp_add} {"＝" if ok else "≠"} 目標 {r["hp"]}'))
            ok = r['base_atk'] + atk_add == r['atk']
            results.append((ok, f'{tag} 攻 {r["base_atk"]}+{atk_add} {"＝" if ok else "≠"} 目標 {r["atk"]}'))
    return results


def _check_monotonic(rows):
    # 表自身單調（僅表一＝hp 非 null；同 Lv 容 2% 取整誤差）
    results = []
    ladder = sorted((r for r in rows if r.get('hp') is not None), key=lambda r: r['lv'])
    for a, b in zip(ladder, ladder[1:]):
        if a['kind'] not in DISCOUNT or b['kind'] not in DISCOUNT:
            bad = a['kind'] if a['kind'] not in DISCOUNT else b['kind']
            results.append((False, f'單調檢查：未知 kind {bad}'))
            continue
        da = a['atk'] / a['itv'] / DISCOUNT[a['kind']]
        db = b['atk'] / b['itv'] / DISCOUNT[b['kind']]
        ok = db >= da * 0.98 and b['hp'] >= a['hp']
        results.append((ok, f"單調 Lv{a['lv']}{a['name']}→Lv{b['lv']}{b['name']}："
                            f"基準DPS {da:.1f}→{db:.1f}、血 {a['hp']}→{b['hp']}"))
    return results


def check_mob_balance(tm, rows):
    return _check_reconciliation(tm, rows) + _check_monotonic(rows)

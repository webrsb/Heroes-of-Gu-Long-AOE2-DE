# -*- coding: utf-8 -*-
"""野怪平衡特徵斷言（s91 掛載，回傳 [(ok, msg)]，比照 ferry_check）。

從建置後觸發重推實值：血＝base_hp＋Σ（涵蓋該生成格的）27、攻＝base_atk＋Σ（涵蓋該生成格的）28
（class 必為 0），與 params.mob_balance 目標對帳；另斷言表本身對 Lv 單調（近戰基準 DPS 與血，
2% 容差吸收取整）。

「涵蓋」＝幾何模型：area 全 -1（全域）或 area_x1<=x<=area_x2 且 area_y1<=y<=area_y2（矩形涵蓋該點，
單格效果是退化情形）。母夜叉矩形（T2711 olu=430、範圍涵蓋 3 個生成格）落在此模型內自然算數，
不需另立「olu==const 即算」的旁支——2026-09-02 品質審查一度加了這條旁支，結果在 T4785/T4786/
T4787/T4788/T5372 這類「多生成格共用同一 const、且每格各自 olu=該 const 而非 -1」的既有正確資料
上重複計數（同一 const 的四格效果互相加總），實測建置直接假警報。已改回純幾何涵蓋，兩型別對稱。

2026-09-02 品質審查發現：舊版用「單格精確比對＋全域」兩種形狀，漏掉了矩形涵蓋多格的區域加攻
（T2711 母夜叉 olu=430 矩形），導致 s91 沒抓到寫入端 s374 的同款漏洞。本模組獨立實作這個幾何
涵蓋模型（刻意不 import steps.s374_mobbalance 的謂詞，不信任寫入端邏輯）；兩邊改動需個別驗證，
不可只改一邊、假設另一邊語意同步跟上。"""
CREATE, CH_HP, CH_ATK, P7 = 11, 27, 28, 7
DISCOUNT = {'m': 1.0, 'r': 0.7, 'f': 0.85, 'rf': 0.6}


def _tile(e):
    return (e.area_x1, e.area_y1, e.area_x2, e.area_y2)


def _covers(e, x, y):
    ax1, ay1, ax2, ay2 = _tile(e)
    if (ax1, ay1, ax2, ay2) == (-1, -1, -1, -1):
        return True
    return ax1 <= x <= ax2 and ay1 <= y <= ay2


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
            x, y = ce.location_x, ce.location_y
            const = ce.object_list_unit_id
            hp_add = atk_add = 0
            bad_cls = None
            for e in t.effects:
                et = getattr(e, 'effect_type', None)
                if getattr(e, 'source_player', -1) != P7:
                    continue
                olu = getattr(e, 'object_list_unit_id', -1)
                if olu not in (-1, const):
                    continue
                if et == CH_HP and _covers(e, x, y):
                    hp_add += int(e.quantity or 0)
                elif et == CH_ATK and _covers(e, x, y):
                    cls = getattr(e, 'armour_attack_class', 0)
                    if cls not in (0, None):
                        bad_cls = cls
                    atk_add += int(getattr(e, 'armour_attack_quantity', None) or 0)
            tag = f'T{tid}「{name}」格({x},{y})'
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

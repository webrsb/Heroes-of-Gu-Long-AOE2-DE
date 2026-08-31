# -*- coding: utf-8 -*-
"""渡船落地驗證（讀產物，唯讀）：新觸發與其座位變體存在、X船6 票效果與東頭暈啟動已清、
X船4 移除已清、X草 無啟動邊、X草2 只清 E0/E1、船卸 一次性由 船/船2 武裝、船旗 全域啟用。
用法（在 src/合併 下）：python tools/verify_ferry.py [out/古龍921_合併.aoe2scenario]"""
import io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, __file__.rsplit('tools', 1)[0])
from core.scenario_io import load

SEATS, PIERS = range(1, 7), ('東', '西')
KINDS = ('船入', '船暈', '船窗止', '船出', '船清入', '船免')
POINTS = {'東': dict(enter=(112, 226), land_in=(110, 225), move_in=(110, 227),
                    in_flag=(110, 228), land_out=(112, 228), move_out=(114, 228)),
          '西': dict(enter=(79, 233), land_in=(81, 232), move_in=(81, 234),
                    in_flag=(81, 235), land_out=(79, 235), move_out=(77, 235))}
DOCK_OUT = {'東': (109, 225), '西': (82, 232)}


def main(path):
    tm = load(path).trigger_manager
    by_name = {}
    for t in tm.triggers:
        by_name.setdefault(t.name or '', []).append(t)
    fails = []

    def check(ok, msg):
        print(('OK   ' if ok else 'FAIL ') + msg)
        if not ok:
            fails.append(msg)

    for p in PIERS:
        for s in SEATS:
            for k in KINDS:
                nm = f'{s}{k}{p}'
                base = by_name.get(nm, [])
                variants = [t for slot in SEATS if slot != s for t in by_name.get(f'{nm}◇位{slot}', [])]
                if k == '船暈':          # 職業鍵 shared：只有原支，無座位變體
                    check(len(base) == 1 and not variants, f'{nm} 原支 1／變體 0（shared）→ 得 {len(base)}／{len(variants)}')
                else:
                    check(len(base) == 1 and len(variants) == 5, f'{nm} 原支 1／變體 5 → 得 {len(base)}／{len(variants)}')
        t = by_name.get(f'船卸{p}', [])
        check(len(t) == 1 and not t[0].enabled and not t[0].looping, f'船卸{p} 一次性、平時關')
        if t:
            arming = [tid for tid in (3732, 3733) if any(int(e.effect_type) == 8 and e.trigger_id == t[0].trigger_id
                                                        for e in tm.triggers[tid].effects)]
            check(arming == [3732, 3733], f'船卸{p} 由 船/船2 武裝 → 得 {arming}')
    t = by_name.get('船旗初始化', [])
    check(len(t) == 1 and t[0].enabled and len(t[0].effects) == 4, '船旗初始化 4 支旗')
    for tid in (3750, 3755, 3760, 3765, 3770, 3775, 3781, 3787, 3793, 3799, 3805, 3811):
        t = tm.triggers[tid]
        check(not any(int(e.effect_type) == 11 for e in t.effects), f'T{tid}「{t.name}」無 CREATE（票已清）')
        check(not any(int(e.effect_type) == 8 and e.trigger_id in (5358, 5361, 5363, 5365, 5367, 5369) for e in t.effects),
              f'T{tid}「{t.name}」不直接啟動 X頭暈起')
        east = tid in (3750, 3755, 3760, 3765, 3770, 3775)
        n_act = sum(1 for e in t.effects if int(e.effect_type) == 8)
        check(n_act == (2 if east else 4),
              f'T{tid}「{t.name}」啟動 {2 if east else 4} 支（' +
              ('血東/費東；開窗與提示搬到費東）' if east else '入/窗止/暈/免）'))
        has_hint = any(int(e.effect_type) == 3 and '三分鐘' in (e.message or '') for e in t.effects)
        check(has_hint != east, f'T{tid}「{t.name}」買票提示{"在費東（本支不該有）" if east else "在本支"}')
    def area_of(o):
        return (o.area_x1, o.area_y1, o.area_x2, o.area_y2)
    # s39 把所有矩陣觸發的 enabled 一律設 0、改由選角啟動清單打開 → 查 enabled 是假陽性，改查有啟動邊指向
    activated = {e.trigger_id for t in tm.triggers for e in t.effects if int(e.effect_type) == 8}
    for p in PIERS:
        pt = POINTS[p]
        for s in SEATS:
            t = by_name[f'{s}船入{p}'][0]
            e = t.effects[0]
            check(not t.conditions and int(e.effect_type) == 35 and area_of(e) == pt['enter'] * 2
                  and (e.location_x, e.location_y) == pt['land_in'],
                  f'{s}船入{p} 零條件、{pt["enter"]}→{pt["land_in"]}')
            t = by_name[f'{s}船暈{p}'][0]
            check(area_of(t.conditions[0]) == pt['enter'] * 2, f'{s}船暈{p} 條件在進入點 {pt["enter"]}')
            t = by_name[f'{s}船清入{p}'][0]
            e = t.effects[0]
            check(not t.conditions and t.trigger_id in activated and int(e.effect_type) == 12
                  and area_of(e) == pt['land_in'] * 2 and (e.location_x, e.location_y) == pt['move_in'],
                  f'{s}船清入{p} 選角啟用、{pt["land_in"]}→{pt["move_in"]}')
            t = by_name[f'{s}船出{p}'][0]
            tp, tk = t.effects[0], t.effects[1]
            check(not t.conditions and t.trigger_id in activated and int(tp.effect_type) == 35
                  and area_of(tp) == pt['in_flag'] * 2 and (tp.location_x, tp.location_y) == pt['land_out']
                  and int(tk.effect_type) == 12 and area_of(tk) == pt['land_out'] * 2
                  and (tk.location_x, tk.location_y) == pt['move_out'],
                  f'{s}船出{p} 選角啟用、{pt["in_flag"]}→{pt["land_out"]}→任務{pt["move_out"]}')
        t = by_name[f'船卸{p}'][0]
        check((t.effects[0].location_x, t.effects[0].location_y) == DOCK_OUT[p],
              f'船卸{p} 卸到卸貨落點 {DOCK_OUT[p]}（避開出來旗）')
    t = by_name['船旗初始化'][0]
    got = {(e.location_x, e.location_y) for e in t.effects}
    want = {POINTS[p][k] for p in PIERS for k in ('enter', 'in_flag')}
    check(got == want, f'船旗＝進入點與出來點 {sorted(want)} → 得 {sorted(got)}')
    for tid in (3748, 3753, 3758, 3763, 3768, 3773, 3779, 3785, 3791, 3797, 3803, 3809):
        t = tm.triggers[tid]
        check(not any(int(e.effect_type) == 15 for e in t.effects), f'T{tid}「{t.name}」REMOVE 已清')
    # X草：原支與 ◇位 變體都不得被任何觸發啟動（s39 本就把矩陣原支停用，查 enabled 是假陽性）。
    # 名稱 `X草` 與等級門檻迴圈 T3673… 同名，以條件區域（牆內西 81,232–83,236）區分。
    def _is_wall_grass(t):
        c = t.conditions[0] if t.conditions else None
        return (t.name or '').split('◇')[0] in {f'{s}草' for s in SEATS} and c is not None \
            and (c.area_x1, c.area_y1, c.area_x2, c.area_y2) == (81, 232, 83, 236)
    grass_ids = {t.trigger_id for t in tm.triggers if _is_wall_grass(t)}
    hits = [(t.trigger_id, e.trigger_id) for t in tm.triggers for e in t.effects
            if int(e.effect_type) == 8 and e.trigger_id in grass_ids]
    check(len(grass_ids) >= 6 and not hits, f'X草 無任何啟動邊指向（{len(grass_ids)} 支）→ 得 {hits[:5]}')
    for tid in (3735, 3737, 3739, 3741, 3743, 3745):
        t = tm.triggers[tid]
        check(not any(int(e.effect_type) == 8 for e in t.effects), f'T{tid}「{t.name}」周賓橋啟動邊已清')
        check(any(int(e.effect_type) == 9 for e in t.effects), f'T{tid}「{t.name}」保留關等級提示迴圈的 DEACTIVATE')
    for s in SEATS:      # 「失去精力 100000」統一由費東發（原作 3船6 抄成「失去了 2000 兩銀」）
        fee = by_name.get(f'{s}船費東', [])
        check(bool(fee) and any('100000' in (e.message or '') and '精力' in (e.message or '')
                                for e in fee[0].effects if int(e.effect_type) == 3),
              f'{s}船費東 發「失去精力 100000」')
    for tid in (3673, 3675, 3677, 3679, 3681, 3683, 3685):
        t = tm.triggers[tid]
        check(int(t.conditions[1].inverted or 0) == 1, f'T{tid}「{t.name}」等級門檻已反相（<1159 才推）')
    HERO = {1: 0, 2: 1, 3: 2, 4: 502, 5: 7, 6: 45117}
    X6E = {1: 3750, 2: 3755, 3: 3760, 4: 3765, 5: 3770, 6: 3775}
    for s in SEATS:                          # 東碼頭：封鎖(小id) → 扣費(大id)，皆由 X船6 同 tick 武裝
        blk = by_name.get(f'{s}船血東', [])
        fee = by_name.get(f'{s}船費東', [])
        ok = len(blk) == 1 and len(fee) == 1 and blk[0].trigger_id < fee[0].trigger_id
        if ok:
            c = blk[0].conditions[0]
            ok = c.unit_object == HERO[s] and c.quantity == 100000 and c.comparison == 3
            armed = {e.trigger_id for e in tm.triggers[X6E[s]].effects if int(e.effect_type) == 8}
            ok = ok and {blk[0].trigger_id, fee[0].trigger_id} <= armed
            ok = ok and any(int(e.effect_type) == 9 and e.trigger_id == fee[0].trigger_id for e in blk[0].effects)
            ok = ok and any(int(e.effect_type) == 24 and e.quantity == 100000 for e in fee[0].effects)
        check(ok, f'{s}船血東(小id) HP≤100000→拆 {s}船費東(大id)，兩支由 T{X6E[s]} 武裝、扣費在費東')
        t = tm.triggers[X6E[s]]
        check(not any(int(e.effect_type) == 24 for e in t.effects),
              f'T{X6E[s]}「{t.name}」原扣費效果已中和（改由費東執行）')
    for s in range(2, 7):                    # 西碼頭 2–6 座位補的等級門檻（基底缺）
        got = by_name.get(f'{s}船級西', [])
        variants = [x for slot in SEATS if slot != s for x in by_name.get(f'{s}船級西◇位{slot}', [])]
        ok = len(got) == 1 and len(variants) == 5 and int(got[0].conditions[1].inverted or 0) == 1 \
            and got[0].conditions[1].quantity == 1159
        check(ok, f'{s}船級西 原支1/變體5、反相、1159 → 得 {len(got)}/{len(variants)}')
    # 東解除器（qty=1160 的 X草2 系）：本體與變體皆不得有任何啟動邊指入（s37 停用→不進 enable_lists）
    def _is_gate_clear(t):
        return (t.name or '').split('◇')[0].endswith('草2') \
            and any(getattr(c, 'quantity', -1) == 1160 for c in t.conditions)
    clear_ids = {t.trigger_id for t in tm.triggers if _is_gate_clear(t)}
    hits = [(t.trigger_id, e.trigger_id) for t in tm.triggers for e in t.effects
            if int(e.effect_type) == 8 and e.trigger_id in clear_ids]
    check(len(clear_ids) >= 6 and not hits, f'東解除器無啟動邊（{len(clear_ids)} 支）→ 得 {hits[:5]}')
    print(f'\n{"全部通過" if not fails else f"{len(fails)} 項 FAIL"}')
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else 'out/古龍921_合併.aoe2scenario'))

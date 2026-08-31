# -*- coding: utf-8 -*-
"""渡船落地驗證（讀產物，唯讀）：新觸發與其座位變體存在、X船6 票效果與東頭暈啟動已清、
X船4 移除已清、X草 無啟動邊、X草2 只清 E0/E1、船卸 一次性由 船/船2 武裝、船旗 全域啟用。
用法（在 src/合併 下）：python tools/verify_ferry.py [out/古龍921_合併.aoe2scenario]"""
import io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, __file__.rsplit('tools', 1)[0])
from core.scenario_io import load

SEATS, PIERS = range(1, 7), ('東', '西')
KINDS = ('船入', '船暈', '船窗止', '船出', '船清入', '船清出', '船免')


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
        check(sum(1 for e in t.effects if int(e.effect_type) == 8) == 4, f'T{tid}「{t.name}」啟動 4 支（入/窗止/暈/免）')
        check(any(int(e.effect_type) == 3 and '三分鐘' in (e.message or '') for e in t.effects), f'T{tid}「{t.name}」有買票提示')
    ENTER = {'東': (112, 226, 112, 228), '西': (79, 233, 79, 234)}
    for p in PIERS:
        for s in SEATS:
            for kind in ('船入', '船暈'):
                t = by_name[f'{s}{kind}{p}'][0]
                c = t.conditions[0]
                got = (c.area_x1, c.area_y1, c.area_x2, c.area_y2)
                check(got == ENTER[p], f'{s}{kind}{p} 進場感應區＝貼牆整排 {ENTER[p]} → 得 {got}')
            t = by_name[f'{s}船入{p}'][0]
            check(len(t.conditions) == 1, f'{s}船入{p} 無閱歷門檻（靜默失敗源）→ 得 {len(t.conditions)} 條件')
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
    t = tm.triggers[3760]
    check(any('100000' in (e.message or '') for e in t.effects if int(e.effect_type) == 3), 'T3760 3船6 訊息已改精力')
    for tid in (3673, 3675, 3677, 3679, 3681, 3683, 3685):
        t = tm.triggers[tid]
        check(int(t.conditions[1].inverted or 0) == 1, f'T{tid}「{t.name}」等級門檻已反相（<1159 才推）')
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

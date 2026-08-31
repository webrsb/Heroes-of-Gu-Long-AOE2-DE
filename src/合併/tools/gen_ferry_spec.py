# -*- coding: utf-8 -*-
"""渡船 spec 區塊產生器（docs/superpowers/specs/2026-08-30-船夫搭船-design.md §三～§五）。
用法（在 src/合併 下）：python tools/gen_ferry_spec.py > <暫存.yaml>，把輸出貼到 merge_spec.yaml
`trigger_fixes:` 清單尾端。輸出順序：75 支 trigger_add（被引用者先；每座位 暈→入→窗止→出→清入→清出）
→ X船6 編輯 → 3船6 訊息 → 船/船2 武裝卸貨 → X船4 中和 → X草 停用／X草2 中和 E0/E1。
merge_spec.yaml 仍是唯一權威；本檔只是避免手打 160 條出錯。"""
import io, sys, textwrap
import yaml

HERO_REF = {1: 0, 2: 1, 3: 2, 4: 502, 5: 7, 6: 45117}
DIZZY = {1: 5358, 2: 5361, 3: 5363, 4: 5365, 5: 5367, 6: 5369}      # X頭暈起（基底 id）
X6 = {'東': {1: 3750, 2: 3755, 3: 3760, 4: 3765, 5: 3770, 6: 3775},
      '西': {1: 3781, 2: 3787, 3: 3793, 4: 3799, 5: 3805, 6: 3811}}
X4 = {'東': ({1: 3748, 2: 3753, 3: 3758, 4: 3763, 5: 3768, 6: 3773}, 1),
      '西': ({1: 3779, 2: 3785, 3: 3791, 4: 3797, 5: 3803, 6: 3809}, 2)}
GRASS = [(3734, '1草'), (3735, '1草2.'), (3736, '2草'), (3737, '2草2'), (3738, '3草'), (3739, '3草2'),
         (3740, '4草'), (3741, '4草2'), (3742, '5草'), (3743, '5草2'), (3744, '6草'), (3745, '6草2')]
FLAG_A, TRANSPORT = 600, 545
PIER = {
    # enter＝進場感應區（貼牆那一排，含旗格）。2026-08-31 驗收：只認單一旗格時右鍵點旗子只會停在旗子旁邊，
    # 永遠踩不到 → 擴成貼牆整排；西刻意排除 (79,235)（出港清場格），否則出港者會被叫回來又被吸進去。
    '東': dict(out_flag=(112, 227), enter=(112, 226, 112, 228),
              in_land=(110, 226), in_clear=(110, 225), in_flag=(110, 228),
              out_land=(116, 232), out_clear=(116, 234), dock=(107, 225, 109, 229)),
    '西': dict(out_flag=(79, 233), enter=(79, 233, 79, 234),
              in_land=(81, 233), in_clear=(81, 232), in_flag=(81, 235),
              out_land=(75, 234), out_clear=(79, 235), dock=(82, 233, 84, 235)),
              # out_clear (79,235)＝使用者 2026-08-31 指定（外旗南 2 格），舊值 (73,234) 堵住走進碼頭的動線
}
# 等級門檻推人觸發（基底條件方向寫反：閱歷 ≥1159 → 罵不夠 16 級＋推走，石頭越多越被騷擾）。
# 修法：C1 加 inverted=1 → <1159 才推；東解除器（≥1160 關推人，兼每 5 秒洗「你以符合等級條件」）失去存在意義，停用。
# 西解除器 T3686 出廠 enabled=0 且武裝它的中繼被無法無天 ID 位移毀掉，不動。
GATE_PUSH = {3673: '1草', 3675: '2草', 3677: '3草', 3679: '4草', 3681: '5草', 3683: '6草', 3685: '1船'}
GATE_CLEAR = {3674: '1草2', 3676: '2草2', 3678: '3草2', 3680: '4草2', 3682: '5草2', 3684: '6草2'}
SHUTTLE = {3732: '船', 3733: '船2'}                 # 班次觸發（派船時武裝一次性卸貨）
# 報價鏈（X船→X船3→X船6）基底 id：售票窗開著時由 X船免 每輪壓停用＝窗內重複進場免費（2026-08-31 使用者裁決）
BUY_CHAIN = {'東': {1: (3746, 3747, 3750), 2: (3751, 3752, 3755), 3: (3756, 3757, 3760),
                    4: (3761, 3762, 3765), 5: (3766, 3767, 3770), 6: (3771, 3772, 3775)},
             '西': {1: (3776, 3778, 3781), 2: (3782, 3784, 3787), 3: (3788, 3790, 3793),
                    4: (3794, 3796, 3799), 5: (3800, 3802, 3805), 6: (3806, 3808, 3811)}}
HINT = '<ORANGE>買票後三分鐘內走到旗子那排貼乾草堆的格子即可進入登船處；牆內踩旗可回岸'


def _tile(xy):
    x, y = xy
    return dict(area_x1=x, area_y1=y, area_x2=x, area_y2=y)


def _rect(r):
    return dict(area_x1=r[0], area_y1=r[1], area_x2=r[2], area_y2=r[3])


def _add(name, enabled, looping, conditions, effects, reason):
    return dict(kind='trigger_add', name=name, enabled=enabled, looping=looping, reason=reason,
                conditions=conditions, effects=effects)


def seat_triggers(s, p):
    c = PIER[p]
    tag = f'渡船{p}座位{s}'
    return [
        # 暈必須排在入之前：同 tick 內入先執行會把英雄傳走，暈就看不到旗格上的英雄（legacy 順序＝id 順序）
        _add(f'{s}船暈{p}', 0, 0,
             [dict(type='bring_object_to_area', unit_object=HERO_REF[s], **_rect(c['enter']))],
             [dict(type='activate_trigger', trigger_id=DIZZY[s])],
             f'{tag}：英雄進貼牆感應區（窗開）→ 啟動 X頭暈起；取代原作付費即暈'),
        _add(f'{s}船入{p}', 0, 1,
             [dict(type='objects_in_area', quantity=1, source_player=s, **_rect(c['enter']))],
             [dict(type='teleport_object', source_player=s, **_rect(c['enter']),
                   location_x=c['in_land'][0], location_y=c['in_land'][1])],
             f'{tag}：售票窗內走進貼牆感應區→傳一隻進牆內落點。不設閱歷門檻：門檻由 X草／1船 推人觸發'
             f'（已反相成 <1159 才推）在到船夫之前擋下，加在這裡只會變成無提示的靜默失敗'),
        _add(f'{s}船免{p}', 0, 1,
             [],
             [dict(type='deactivate_trigger', trigger_id=BUY_CHAIN[p][s][0]),
              dict(type='deactivate_trigger', trigger_id=BUY_CHAIN[p][s][1]),
              dict(type='deactivate_trigger', trigger_id=BUY_CHAIN[p][s][2])],
             f'{tag}：售票窗開著＝這趟已付清，每輪壓住報價鏈（X船/X船3/X船6），重複進場不再扣費；'
             f'X船4 每輪重啟 X船 沒關係——本支 id 較大、同輪稍後蓋回去'),
        _add(f'{s}船窗止{p}', 0, 0,
             [dict(type='timer', timer=180)],
             [dict(type='deactivate_trigger', trigger_name=f'{s}船入{p}'),
              dict(type='deactivate_trigger', trigger_name=f'{s}船暈{p}'),
              dict(type='deactivate_trigger', trigger_name=f'{s}船免{p}')],
             f'{tag}：售票窗 3 分鐘關閉（過期後重新走鏈＝重新收費）'),
        _add(f'{s}船出{p}', 1, 1,
             [dict(type='objects_in_area', quantity=1, source_player=s, **_tile(c['in_flag']))],
             [dict(type='teleport_object', source_player=s, **_tile(c['in_flag']),
                   location_x=c['out_land'][0], location_y=c['out_land'][1])],
             f'{tag}：踩牆內旗→傳一隻到牆外落點（抵達者／後悔者）'),
        _add(f'{s}船清入{p}', 1, 1,
             [dict(type='objects_in_area', quantity=1, source_player=s, **_tile(c['in_land']))],
             [dict(type='task_object', source_player=s, **_tile(c['in_land']),
                   location_x=c['in_clear'][0], location_y=c['in_clear'][1])],
             f'{tag}：牆內落點被壓住→叫走到北端死巷（傳送迴圈重試）'),
        _add(f'{s}船清出{p}', 1, 1,
             [dict(type='objects_in_area', quantity=1, source_player=s, **_tile(c['out_land']))],
             [dict(type='task_object', source_player=s, **_tile(c['out_land']),
                   location_x=c['out_clear'][0], location_y=c['out_clear'][1])],
             f'{tag}：牆外落點被壓住→叫走'),
    ]


def global_triggers():
    out = []
    for p in PIER:
        c = PIER[p]
        out.append(_add(f'船卸{p}', 0, 0,
                        [dict(type='timer', timer=8),
                         dict(type='objects_in_area', quantity=1, source_player=8, object_list=TRANSPORT, **_rect(c['dock']))],
                        [dict(type='unload', source_player=8, object_list_unit_id=TRANSPORT, **_rect(c['dock']),
                              location_x=c['in_land'][0], location_y=c['in_land'][1])],
                        f'渡船{p}：一次性，派船時武裝，TIMER 8 待離港船駛出水域，對岸船抵達即 UNLOAD 到牆內落點一次'
                        f'（不可迴圈：兩船開局即在水域內，會把剛登船者卸回；spike_ferry ①／v4）'))
    flags = [dict(type='create_object', source_player=0, object_list_unit_id=FLAG_A,
                  location_x=PIER[p][k][0], location_y=PIER[p][k][1])
             for p in PIER for k in ('out_flag', 'in_flag')]
    out.append(_add('船旗初始化', 1, 0, [dict(type='timer', timer=0)], flags,
                    '渡船：兩碼頭牆外／牆內 Gaia 旗（FLAG_A 600）'))
    return out


def edits():
    out = []
    for p, ids in X6.items():
        for s, tid in ids.items():
            nm = f'{s}船6'
            create_idx = 1 if (p == '東' and s == 6) else 2
            out.append(dict(trigger_id=tid, name=nm, kind='effect', index=create_idx, field='effect_type',
                            old=11, new=0, reason='票（地圖顯示器）機制移除，牆改由傳送進出'))
            if p == '東':
                out.append(dict(trigger_id=tid, name=nm, kind='effect', index=4, field='effect_type',
                                old=8, new=0, reason='頭暈改由英雄踩牆外旗觸發（X船暈）'))
            for k in ('船入', '船窗止', '船暈', '船免'):
                out.append(dict(trigger_id=tid, name=nm, kind='effect_add',
                                effect=dict(type='activate_trigger', trigger_name=f'{s}{k}{p}'),
                                reason='買票開售票窗'))
            out.append(dict(trigger_id=tid, name=nm, kind='effect_add',
                            effect=dict(type='send_chat', source_player=s, message=HINT),
                            reason='買票提示，僅買票座位可見'))
    out.append(dict(trigger_id=3760, name='3船6', kind='effect', index=3, field='message',
                    old='<GREEN>失去了　2000　兩銀', new='<GREEN>失去精力        100000',
                    reason='東碼頭扣的是精力，其餘五座位皆「失去精力 100000」，3P 抄錯'))
    for tid, nm in SHUTTLE.items():
        for p in PIER:
            out.append(dict(trigger_id=tid, name=nm, kind='effect_add',
                            effect=dict(type='activate_trigger', trigger_name=f'船卸{p}'),
                            reason='派船時武裝一次性卸貨'))
    for p, (ids, idx) in X4.items():
        for s, tid in ids.items():
            out.append(dict(trigger_id=tid, name=f'{s}船4', kind='effect', index=idx, field='effect_type',
                            old=15, new=0, reason='票已不存在；此移除唯一可能刪到的是船上駐軍中的英雄'))
    for tid, nm in GATE_PUSH.items():
        out.append(dict(trigger_id=tid, name=nm, kind='condition', index=1, field='inverted',
                        old=-1, new=1, reason='等級門檻方向寫反（≥1159 推走）；反相成 <1159 才推，不夠級到不了船夫不會被扣錢'))
    for tid, nm in GATE_CLEAR.items():
        out.append(dict(trigger_id=tid, name=nm, kind='trigger', field='enabled', old=1, new=0,
                        reason='推人方向修正後只剩每 5 秒洗「你以符合等級條件」的功能'))
    for tid, nm in GRASS:
        if nm.endswith('草'):                       # X草：整支停用（只有兩條指箭影高人的啟動邊）
            out.append(dict(trigger_id=tid, name=nm, kind='trigger', field='enabled', old=1, new=0,
                            reason='基底 ID 位移：指到箭影高人迴圈，牆內有人即誤啟'))
        else:                                       # X草2：只中和 E0/E1（周賓橋），保留 E2 關等級提示迴圈
            for idx in (0, 1):
                out.append(dict(trigger_id=tid, name=nm, kind='effect', index=idx, field='effect_type',
                                old=8, new=0, reason='基底 ID 位移：指到周賓橋；E2 關 X草2 等級提示迴圈須保留'))
    return out


def entries():
    adds = []
    for p in PIER:
        for s in range(1, 7):
            adds += seat_triggers(s, p)
    return adds + global_triggers() + edits()


def render():
    text = yaml.safe_dump(entries(), allow_unicode=True, sort_keys=False, default_flow_style=None, width=200)
    return textwrap.indent(text, '    ')


if __name__ == '__main__':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    print('    # 【2026-08-30 船夫搭船 DE 重做】由 tools/gen_ferry_spec.py 產生；設計見 docs/superpowers/specs/2026-08-30-船夫搭船-design.md')
    print(render(), end='')

# -*- coding: utf-8 -*-
"""六座位對稱稽核「建議修」→ merge_spec.trigger_fixes 條目產生器（2026-09-01）。

來源：六個裁決代理對 657 條 finding 的裁決（`verdicts/*.yaml`、彙整於 `audit_ledger.yaml`）中
verdict=pending 且理由以「建議修：」開頭者。本檔把它們固化成可重現的 spec 條目，
並提供 `validate()` 對「s37 實際會看到的狀態」逐條驗舊值。

**為什麼要對 until_s36 驗而不是對基底驗**：s37 跑在 s30（攻擊力重編碼）之後，
改攻效果（type 28）的量值屆時已改用 `armour_attack_quantity` 表示，對基底驗會全錯。

用法（在 src/合併 下）：
    python build.py --until s36                 # 先產出驗證用中間態
    python tools/gen_audit_fixes.py --check     # 只驗不輸出
    python tools/gen_audit_fixes.py            # 印出 YAML 區塊
"""
import io
import sys

sys.path.insert(0, __file__.rsplit('tools', 1)[0])

CHANGE_ATTACK = 28
UNTIL_S36 = 'out/古龍921_合併_until_s36.aoe2scenario'

# 逐條裁決來源見 audit_ledger.yaml；name 一律用 s371 改名「前」的原名（s37 早於 s371）
FIXES = [
    # ── 斷線／指錯目標（功能整條失效）───────────────────────────────
    # 註：T5491 漢娜斯1／T2907 5渦死5／T287 5道4／T292 6道4×2／T2908 6渦死5 的修法
    #     merge_spec 早已有（歷次 session），代理不知情而重複提出，已移除——
    #     驗證用的 until_s36 中間態看不到 s37 內部的先後順序，故加 check_duplicates() 把關。
    dict(trigger_id=1097, name='6峨', kind='effect', index=2, field='trigger_id',
         old=1097, new=18, reason='自指；1–5峨 皆 ACTIVATE 自家 N升級（稽核 edge_missing）'),
    dict(trigger_id=2857, name='5渦', kind='effect', index=1, field='trigger_id',
         old=2857, new=15, reason='自指；其餘座位皆 ACTIVATE 自家 N升級（稽核 edge_missing）'),
    dict(trigger_id=388, name='5醫3', kind='effect', index=3, field='trigger_id',
         old=209, new=247, reason='抄錯族：停用 5教頭2 應為 5醫學者2（稽核 edge_missing）'),
    # ── 漏接的啟停邊 ─────────────────────────────────────────
    dict(kind='effect_add', trigger_id=1936, name='4木',
         effect=dict(type='activate_trigger', trigger_id=2035, target_name='4南僧'),
         reason='4木 漏抄「啟動 4南僧」；1/2/3/5/6木 皆有，致 T2035 全檔無啟動來源'),
    dict(trigger_id=2035, name='4南僧', kind='trigger', field='enabled', old=1, new=0,
         reason='南僧六支應出廠停用、由 N木 啟動；4P 出廠即開（配合上一條補回啟動邊）'),
    dict(kind='effect_add', trigger_id=2540, name='4卜2',
         effect=dict(type='deactivate_trigger', trigger_id=2534, target_name='4卜'),
         reason='4卜2 有 2 條件卻 0 效果；其餘座位皆停用自家 N卜，致 4卜 迴圈永不停'),
    dict(kind='effect_add', trigger_id=4263, name='3珠',
         effect=dict(type='activate_trigger', trigger_id=9, target_name='3升級'),
         reason='3珠 漏抄「啟動 3升級」；撿到珠寶項飾不做升級結算'),
    dict(kind='effect_add', trigger_id=5266, name='刀客破壞之神',
         effect=dict(type='activate_trigger', trigger_id=7, target_name='1升級'),
         reason='1P 漏抄「啟動 1升級」；2–6P 對應支皆有'),
    dict(kind='effect_add', trigger_id=4620, name='4迪3',
         effect=dict(type='activate_trigger', trigger_id=4230, target_name='4哥'),
         reason='4迪3 漏接「啟動 4哥」；其餘五座位皆有'),
    dict(kind='effect_add', trigger_id=4620, name='4迪3',
         effect=dict(type='deactivate_trigger', trigger_id=5497, target_name='漢娜斯4'),
         reason='4迪3 漏接「停用 漢娜斯4」；其餘五座位皆有，致 P4 對白不結束'),
    dict(kind='effect_add', trigger_id=5020, name='堡定6',
         effect=dict(type='activate_trigger', trigger_id=4677, target_name='失血'),
         reason='堡定6 只有 2 效果；1–5 皆 4 效果（漏 失血）'),
    dict(kind='effect_add', trigger_id=5020, name='堡定6',
         effect=dict(type='activate_trigger', trigger_id=5050, target_name='神弓之洛6~1'),
         reason='同上，漏 神弓之洛6~1'),
    # ── 持續回血迴圈數值（無敵風險）──────────────────────────────
    dict(trigger_id=4418, name='6神', kind='effect', index=0, field='quantity',
         old=-7000, new=-49, reason='OBJECT_HAS_TARGET 每 tick 回血，1–5P 皆 -49；-7000＝143 倍等於無敵'),
    dict(trigger_id=4401, name='6谷', kind='effect', index=0, field='quantity',
         old=-1000, new=-19, reason='N谷 小回血 1–5P 皆 -19；-1000 是下一支「谷2」的值貼錯'),
    dict(trigger_id=4007, name='1谷2', kind='effect', index=0, field='quantity',
         old=-3000, new=-1000, reason='N谷2 大回血其餘座位皆 -1000；1P 三倍等於半無敵'),
    # ── 等級／經驗表手誤 ────────────────────────────────────
    dict(trigger_id=1063, name='5 48', kind='condition', index=0, field='quantity',
         old=33936, new=22936, reason='lv48 其餘五座位 22936；33936 高過自家 lv50(25725)，等級會跳號倒退'),
    dict(trigger_id=1064, name='5 49', kind='condition', index=0, field='quantity',
         old=34304, new=24304, reason='lv49 其餘五座位 24304；同上斷裂'),
    dict(trigger_id=2030, name='6-79', kind='condition', index=0, field='quantity',
         old=97945, new=94474, reason='lv79 與自家 lv80 撞值，6箭 吃掉一級；其餘五座位 94474'),
    dict(trigger_id=1015, name='3 42', kind='condition', index=0, field='quantity',
         old=15875, new=15785, reason='lv42 其餘五座位 15785（78/87 對調手誤）'),
    dict(trigger_id=726, name='3 82', kind='condition', index=0, field='quantity',
         old=105187, new=105137, reason='lv82 其餘五座位 105137（13/18 對調手誤）'),
    dict(trigger_id=3311, name='3 8', kind='condition', index=0, field='quantity',
         old=194, new=196, reason='lv8 其餘五座位 196'),
    # ── 分身（馬騎）與本尊不同步 ─────────────────────────────
    dict(trigger_id=3270, name='2 1-5Lv', kind='effect', index=4, field='quantity',
         old=0, new=5, reason='升級加上限血：本尊 E#0 給 5，分身 E#4 給 0；其餘座位皆 5/5'),
    dict(trigger_id=961, name='1 31-50', kind='effect', index=4, field='quantity',
         old=8, new=10, reason='升級加上限血：本尊 10、分身 8；其餘座位皆 10/10'),
    dict(trigger_id=1191, name='1當2', kind='effect', index=4, field='quantity',
         old=0, new=-100, reason='當歸丸回 100 精力，分身那份給 0；NPC 台詞與同支 E#3 皆 100'),
    dict(trigger_id=4387, name='6王3', kind='effect', index=3, field='quantity',
         old=-2000, new=-1000, reason='醉酒回血本尊/分身應同值；同支 E#2 為 -1000'),
    dict(trigger_id=4320, name='6酒4', kind='effect', index=2, field='quantity',
         old=-1000, new=-100, reason='解酒回血應與同支上限血 -100、分身 E#5 -100 成對'),
    # ── 其他數值與物件種類 ───────────────────────────────────
    dict(trigger_id=1291, name='6血', kind='effect', index=0, field='quantity',
         old=-42, new=-51, reason='同支訊息寫「51 點江湖閱歷」，其餘五座位亦 -51（訊息未改＝抄錯）'),
    dict(trigger_id=2931, name='6魔', kind='effect', index=1, field='quantity',
         old=-330, new=-600, reason='最後一擊獎勵 1–5P 皆 -600，且六座位訊息同為「800 兩銀」'),
    dict(trigger_id=5448, name='觸發事件 刀氣', kind='effect', index=1, field='quantity',
         old=-200, new=-400, reason='毀學群體回血 2–6P 皆 -400'),
    dict(trigger_id=3713, name='3船2', kind='effect', index=0, field='object_list_unit_id',
         old=723, new=837, reason='座位旗標是 MAP_REVEALER(837)；723 CRATER 清不到東西'),
    dict(trigger_id=4138, name='4棍', kind='effect', index=0, field='selected_object_ids',
         old=[], new=[28463], reason='CHANGE_OWNERSHIP 8→7 三種目標全空＝P8 全圖物件轉 P7；同支線他支皆帶 sel'),
    dict(trigger_id=2241, name='4棍8', kind='condition', index=0, field='timer',
         old=5, new=1, reason='每秒回血技週期，3槍8／5拳8 皆 1 秒且回血量未加倍補償'),
    dict(trigger_id=2108, name='2道4', kind='condition', index=0, field='timer',
         old=2, new=1, reason='同上；2P 週期加倍但回血量沒跟著加倍＝速率減半'),
    # ── 改攻擊力：s30 之後量值走 armour_attack_quantity（見檔頭說明）──
    dict(trigger_id=4189, name='1哥5', kind='effect', index=4, field='armour_attack_quantity',
         old=50, new=100, reason='卸鐵甲扣攻：本尊 E#2 為 100、其餘座位分身亦 100；1P 分身只扣 50'),
    # ── 2026-09-01 攻略 session 查證後追加（原作漏抄的前置檢查／冷卻）──────────
    dict(kind='condition_add', trigger_id=2652, name='6進',
         condition=dict(type='objects_in_area', quantity=1, source_player=6,
                        area_x1=229, area_y1=234, area_x2=229, area_y2=234),
         reason='6進 缺「推薦書在位」條件（1P(229,239)／5P(229,235) 同序列）；箭客可跳過第二試練直接學醫8'),
    dict(kind='condition_add', trigger_id=792, name='1武',
         condition=dict(type='objects_in_area', quantity=1, source_player=1,
                        area_x1=133, area_y1=32, area_x2=144, area_y2=66),
         reason='1武 缺「玩家在武僧刷怪區」檢查（他座皆有）；離區也會誤發 51 閱歷擊殺獎'),
    dict(kind='condition_add', trigger_id=793, name='1武2',
         condition=dict(type='timer', timer=20),
         reason='1武2 是重新武裝器，他座每 20 秒一次；1P 缺 TIMER 等於冷卻被拿掉、可同殺雙領'),
    dict(trigger_id=1867, name='6軒2', kind='effect', index=2, field='quantity',
         old=10000, new=-1000,
         reason='軒轅任務正常收支＝+2000+1000−10000＝淨 −7000；6P 同支扣兩次（E#2 也扣 10000）＝淨 −20000'),
    dict(trigger_id=1867, name='6軒2', kind='effect', index=3, field='message',
         old='<AQUA>失去了　10000　點江湖閱歷', new='<AQUA>得到了　1000　點江湖閱歷',
         reason='隨上一條改回「得到 1000」，與其餘五座位訊息一致'),
    # ── 2026-09-01 第二批（攻略 session 查證：8 條裡 2 修 6 不修）─────────────
    dict(kind='condition_add', trigger_id=5113, name='殺豬1',
         condition=dict(type='objects_in_area', quantity=1, source_player=1,
                        area_x1=233, area_y1=61, area_x2=239, area_y2=69, object_group=6),
         reason='殺豬1 只有擊殺數條件，他座還要求「人在領獎區」（2P 帶 object_group=6 步兵過濾，'
                '刀客同為步兵）；缺檢查＝P1 不在場也領 500 閱歷。區域取 1P 自己的武裝觸發 殺豬1~1 用的範圍。'
                '不補 TIMER：他座那筆只是延遲（殺豬N 非循環，不具冷卻作用），且 2P 版本來就沒有'),
    dict(kind='effect_add', trigger_id=2546, name='1仙4',
         effect=dict(type='change_object_hp', source_player=1, selected_object_ids=[0],
                     quantity=1000, operation=-1),
         reason='仙子附體（道9）學會時的一次性上限獎：2P 本體+1000/馬+2100、3P 900/900、5P 900/1600、'
                '6P 1000/1000，P1 兩筆皆無＝抄漏（P1 面板同為「1秒171精力」，非 4P 那種改成 221 的補償型設計）。'
                '對齊同型近戰、面板同值的最近鄰 2P。sel=0 為 P1 本體（P8 馬列 x=91.5→P1…96.5→P6 可對）'),
    dict(kind='effect_add', trigger_id=2546, name='1仙4',
         effect=dict(type='change_object_hp', source_player=1, selected_object_ids=[26109],
                     quantity=2100, operation=-1),
         reason='同上，P1 馬騎本體（ref 26109，P8 馬列 x=91.5 那隻）；量值對齊 2P 的 26186 +2100'),
]


def validate(path=UNTIL_S36):
    """對「s37 實際會看到的狀態」逐條驗名稱與舊值。回傳 [(ok, 說明)]。"""
    from core.scenario_io import load
    tm = load(path).trigger_manager
    out = []
    for f in FIXES:
        tid = f['trigger_id']
        t = tm.triggers[tid] if 0 <= tid < len(tm.triggers) else None
        tag = f'T{tid}「{f.get("name")}」{f.get("kind")}#{f.get("index")}.{f.get("field", "")}'
        if t is None or (t.name or '') != f['name']:
            out.append((False, f'{tag} 名稱不符：實得「{getattr(t, "name", None)}」'))
            continue
        if f['kind'] == 'condition_add':
            out.append((True, f'{tag} 追加條件 {f["condition"]["type"]}（無舊值可驗，s37 名稱防呆把關）'))
            continue
        if f['kind'] == 'effect_add' and 'trigger_id' not in f['effect']:
            sel = f['effect'].get('selected_object_ids') or []
            out.append((True, f'{tag} 追加效果 {f["effect"]["type"]} sel={sel}（無舊值可驗，'
                              f's37 名稱防呆＋幽靈玩家欄防呆把關）'))
            continue
        if f['kind'] == 'effect_add':
            tgt = f['effect']['trigger_id']
            tt = tm.triggers[tgt] if 0 <= tgt < len(tm.triggers) else None
            ok = tt is not None and (tt.name or '') == f['effect']['target_name']
            out.append((ok, f'{tag} → T{tgt}「{getattr(tt, "name", None)}」'
                            f'{"" if ok else " ✗ 目標名稱不符"}'))
            continue
        if f['kind'] == 'trigger':
            cur = int(getattr(t, f['field']) or 0)
            out.append((cur == f['old'], f'{tag} 現值 {cur} 期望舊值 {f["old"]}'))
            continue
        seq = t.conditions if f['kind'] == 'condition' else t.effects
        if f['index'] >= len(seq):
            out.append((False, f'{tag} 索引越界（共 {len(seq)}）'))
            continue
        obj = seq[f['index']]
        cur = getattr(obj, f['field'], None)
        cur = list(cur) if isinstance(cur, list) else cur
        want = f['old']
        ok = cur == want
        extra = ''
        if f['kind'] == 'effect' and int(getattr(obj, 'effect_type', 0)) == CHANGE_ATTACK \
                and f['field'] == 'quantity':
            extra = '（改攻效果：s30 後量值在 armour_attack_quantity，不該改 quantity）'
            ok = False
        out.append((ok, f'{tag} 現值 {cur!r} 期望舊值 {want!r}{extra}'))
    return out


def check_duplicates(spec_path='merge_spec.yaml'):
    """與現有 merge_spec 條目撞位＝重複修（s37 會在第二條就報「舊值不符」而中止）。
    2026-09-01 踩過：代理不知道歷次 session 早修過同一處，6 條重複。"""
    import yaml
    entries = yaml.safe_load(open(spec_path, encoding='utf-8'))['params']['trigger_fixes'] or []
    have = set()
    for e in entries:
        if e.get('kind') in ('effect', 'condition', 'trigger'):
            have.add((e.get('trigger_id'), e.get('kind'), e.get('index'), e.get('field')))
        elif e.get('kind') == 'effect_add' and (e.get('effect') or {}).get('trigger_id'):
            have.add((e.get('trigger_id'), 'effect_add', e['effect']['type'], e['effect']['trigger_id']))
    out = []
    for f in FIXES:
        if f['kind'] == 'condition_add':
            k = (f['trigger_id'], 'condition_add', f['condition']['type'],
                 f['condition'].get('timer', f['condition'].get('area_x1')))
        elif f['kind'] == 'effect_add':
            k = (f['trigger_id'], 'effect_add', f['effect']['type'],
                 f['effect'].get('trigger_id', tuple(f['effect'].get('selected_object_ids') or ())))
        else:
            k = (f['trigger_id'], f['kind'], f.get('index'), f.get('field'))
        if k in have:
            out.append(f'重複：{k} 已存在於 {spec_path}')
    return out


def render():
    import textwrap
    import yaml
    text = yaml.safe_dump(FIXES, allow_unicode=True, sort_keys=False, default_flow_style=None, width=200)
    return textwrap.indent(text, '    ')


def main(argv):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    results = validate()
    bad = [m for ok, m in results if not ok]
    import os
    if os.path.exists('merge_spec.yaml'):
        bad += check_duplicates()
    for ok, m in results:
        if not ok:
            print('FAIL ' + m)
    for m in bad:
        if not any(m == x for _, x in results):
            print('DUP  ' + m)
    print(f'{len(results)} 條，{len(bad)} 條不符')
    if bad:
        return 1
    if '--check' not in argv:
        print('    # 【2026-09-01 六座位對稱稽核裁決：原作 bug 修正】由 tools/gen_audit_fixes.py 產生')
        print(render(), end='')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))

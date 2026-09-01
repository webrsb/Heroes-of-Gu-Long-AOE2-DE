# -*- coding: utf-8 -*-
"""啟動稽核（2026-08-30，銀龍/神弓越權啟動事故後新增）：
對建置後劇情檔做觸發啟停圖靜態檢查，抓「復活鏈把不該碰的觸發打開」這一類系統性錯誤。

檢查項：
1. 懸空邊——8/9 效果指向不存在的 trigger_id
2. 退役邊——任何啟動(8)效果指向 退役_ 觸發（deactivate 允許）
3. 死亡路徑越權——監視/重生/命盡/馬監視 觸發啟動了非白名單目標
   （白名單＝復活鏈家族：監視|重生|命盡|馬監視|訊|啟動|選角、dl ◇位 變體）
4. ◇命 副本閘防——每支 ◇命 觸發必須帶命數條件(變數 V_LIFE==L；舊制為 Gaia 720 單格旗)
   或命 ref 條件，否則它一被打開就無條件生效（銀龍事故根因）
5. 死亡路徑停用越權——同 3 但查停用(9)邊
6. 重生區條件——◇命副本綁單位的區域條件涵蓋重生點（備身駐軍即提前成立）
7. 啟動來源清單——選角/啟動器對非鏈觸發的啟動明細（人工複核用，不判錯）

用法: python -m analysis.audit_activation <scenario> [out_md]
結束碼: 0=無違規, 1=有違規。
"""
import sys, re

CHAIN_RE = re.compile(r'^(監視|重生|命盡|馬監視|訊|啟動|選角|轉生旗|補池|命旗)')
DEATH_RE = re.compile(r'^(監視|重生|命盡|馬監視)')
FLAG_CONST = 720
ACTIVATE, DEACTIVATE = 8, 9
VARIABLE_VALUE = 22        # 條件：變數 vs 常數（命數閘）


def audit_killvar(tm, offsets):
    """擊殺變數槽位一致：condition 78 / effect 56 的變數隱含玩家位（v−off）必須等於
    同觸發所有 sp∈1..6 欄位（矩陣改寫漏變數欄即抓到）。回傳 violations。"""
    vio = []
    for t in tm.triggers:
        tn = t.name or '(無名)'
        if tn.startswith('退役_'):
            continue
        implied = set()
        for c in t.conditions:
            if getattr(c, 'condition_type', None) == 78:
                for fld in ('variable', 'variable2'):
                    v = getattr(c, fld, -1)
                    for off in offsets:
                        if off + 1 <= v <= off + 6:
                            implied.add(v - off)
        for e in t.effects:
            if getattr(e, 'effect_type', None) == 56:
                v = getattr(e, 'variable', -1)
                for off in offsets:
                    if off + 1 <= v <= off + 6:
                        implied.add(v - off)
        if not implied:
            continue
        sps = {getattr(x, 'source_player', -1) for x in list(t.conditions) + list(t.effects)}
        sps = {s for s in sps if s in range(1, 7)}
        if len(implied) != 1 or (sps and sps != implied):
            vio.append(('變數槽位', f'T{t.trigger_id}「{tn}」變數隱含位 {sorted(implied)} '
                                 f'vs 玩家欄 {sorted(sps)}'))
    return vio


def audit(tm, life_xs=None, life_refs=None, respawn=None, var_offsets=None,
          life_vars=None):
    """回傳 (violations, review_lines)。violations=[(類別, 說明)]。"""
    n = len(tm.triggers)
    by_id = {t.trigger_id: t for t in tm.triggers}
    name = lambda t: t.name or '(無名)'
    vio, review = [], []
    life_ref_set = {r for refs in (life_refs or {}).values() for r in refs}

    for t in tm.triggers:
        tn = name(t)
        for i, e in enumerate(t.effects):
            et = getattr(e, 'effect_type', None)
            if et not in (ACTIVATE, DEACTIVATE):
                continue
            tid = getattr(e, 'trigger_id', -1)
            tgt = by_id.get(tid)
            if tgt is None:
                vio.append(('懸空邊', f'T{t.trigger_id}「{tn}」E{i} →T{tid} 不存在'))
                continue
            gn = name(tgt)
            if et == ACTIVATE and gn.startswith('退役_') and not tn.startswith('退役_'):
                # 退役來源→退役目標放行（來源不可達，裁決 2026-08-29）
                vio.append(('退役邊', f'T{t.trigger_id}「{tn}」E{i} 啟動退役觸發「{gn}」'))
            if DEATH_RE.match(tn):
                ok = CHAIN_RE.match(gn) or '◇位' in gn
                if et == ACTIVATE and not ok:
                    vio.append(('死亡路徑越權',
                                f'T{t.trigger_id}「{tn}」啟動 T{tid}「{gn}」'
                                f'(enabled={tgt.enabled})——非復活鏈白名單'))
                if et == DEACTIVATE and not ok:
                    vio.append(('死亡路徑停用越權',
                                f'T{t.trigger_id}「{tn}」停用 T{tid}「{gn}」——非復活鏈白名單'))
            if et == ACTIVATE and (tn.startswith('選角') or tn.startswith('啟動')) \
                    and not CHAIN_RE.match(gn):
                review.append(f'T{t.trigger_id}「{tn}」→T{tid}「{gn}」'
                              f'(enabled={tgt.enabled})')

    # ◇命 副本閘防：必須有命數條件（變數 V_LIFE，2026-09-01 起；或舊制 Gaia 720
    # 單格 @life_xs 欄）或命 ref 條件
    life_var_set = {int(v) for v in (life_vars or {}).values()} or None
    for t in tm.triggers:
        tn = name(t)
        if '◇命' not in tn or tn.startswith('退役_'):
            continue
        # 旗分支：僅在給了 life_xs（舊制命旗欄）時成立——2026-09-01 起命數走變數，
        # 若無條件放行任何單格 Gaia 720，命盡旗/騎馬旗會被誤認成命閘（比原本鬆）。
        has_flag = life_xs is not None and any(
            getattr(c, 'object_list', -1) == FLAG_CONST
            and getattr(c, 'source_player', -1) == 0
            and getattr(c, 'area_x1', -1) == getattr(c, 'area_x2', -2)
            and getattr(c, 'area_x1', -1) in life_xs
            for c in t.conditions)
        has_flag = has_flag or any(
            getattr(c, 'condition_type', -1) == VARIABLE_VALUE
            and (life_var_set is None or getattr(c, 'variable', -1) in life_var_set)
            for c in t.conditions)
        # 命 ref 閘：副本條件已改綁該命備身 ref（expand_conditions 多ref路徑、
        # X馬3◇命L 的 BRING 改命）。給定 life_refs 時精確比對，否則任何
        # 單位綁定條件都視為 ref 閘（備身 ref 建置期才產生，事後稽核無從得知清單）。
        if life_ref_set:
            has_life_ref = any(getattr(c, f, -1) in life_ref_set
                               for c in t.conditions for f in ('unit_object', 'next_object'))
        else:
            has_life_ref = any(getattr(c, f, -1) not in (-1, None)
                               for c in t.conditions for f in ('unit_object', 'next_object'))
        if not (has_flag or has_life_ref):
            vio.append(('◇命無旗防',
                        f'T{t.trigger_id}「{tn}」無命數/命旗/命ref條件——被打開即無條件生效'))

    # ◇命副本的區域條件涵蓋重生點：備身駐容器疊於重生點且駐軍計入區域條件，
    # 家族一啟用該副本條件即提前成立（BRING/區域類）
    if respawn is not None:
        rx, ry = int(respawn[0]), int(respawn[1])
        for t in tm.triggers:
            tn = name(t)
            if '◇命' not in tn or tn.startswith('退役_'):
                continue
            for i, c in enumerate(t.conditions):
                if getattr(c, 'unit_object', -1) in (-1, None):
                    continue
                x1, y1 = getattr(c, 'area_x1', -1), getattr(c, 'area_y1', -1)
                x2, y2 = getattr(c, 'area_x2', -1), getattr(c, 'area_y2', -1)
                if x1 in (-1, None) or x2 in (-1, None):
                    continue
                if x1 <= rx <= x2 and y1 <= ry <= y2:
                    vio.append(('重生區條件',
                                f'T{t.trigger_id}「{tn}」C{i} 綁單位且區域'
                                f'({x1},{y1})-({x2},{y2}) 涵蓋重生點——'
                                f'備身駐軍時條件提前成立'))
    if var_offsets:
        vio += audit_killvar(tm, var_offsets)
    return vio, review


def main(src, out_md=None):
    import yaml, os, io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    from AoE2ScenarioParser.scenarios.aoe2_de_scenario import AoE2DEScenario
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    spec = yaml.safe_load(open(os.path.join(here, 'merge_spec.yaml'), encoding='utf-8'))
    rv = (spec.get('params') or spec).get('revive') or {}
    life_xs = set(int(x) for x in (rv.get('cells') or {}).get('life_xs') or []) or None
    lvo = rv.get('life_var_offset')
    life_vars = {cid: int(lvo) + cid for cid in range(1, 7)} if lvo is not None else None

    respawn = rv.get('respawn')
    kv = (spec.get('params') or spec).get('killvar') or {}
    var_offsets = (int(kv['v_kills_offset']), int(kv['v_base_offset'])) if kv else None
    scn = AoE2DEScenario.from_file(src)
    vio, review = audit(scn.trigger_manager, life_xs=life_xs, respawn=respawn,
                        var_offsets=var_offsets, life_vars=life_vars)

    lines = [f'# 啟動稽核 — {os.path.basename(src)}', '']
    lines.append(f'觸發總數: {len(scn.trigger_manager.triggers)}')
    lines.append(f'違規: {len(vio)}　複核清單: {len(review)}')
    lines.append('')
    if vio:
        lines.append('## 違規')
        for k, s in vio:
            lines.append(f'- **[{k}]** {s}')
        lines.append('')
    if review:
        lines.append('## 選角/啟動器 → 非鏈觸發（人工複核，非違規）')
        for s in review:
            lines.append(f'- {s}')
    text = '\n'.join(lines) + '\n'
    if out_md:
        open(out_md, 'w', encoding='utf-8', newline='\n').write(text)
        print(f'報表: {out_md}')
    print(f'違規 {len(vio)} 項、複核 {len(review)} 項')
    for k, s in vio[:40]:
        print(f'  [{k}] {s}')
    return 1 if vio else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None))

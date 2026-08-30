# -*- coding: utf-8 -*-
"""啟動稽核（2026-08-30，銀龍/神弓越權啟動事故後新增）：
對建置後劇情檔做觸發啟停圖靜態檢查，抓「復活鏈把不該碰的觸發打開」這一類系統性錯誤。

檢查項：
1. 懸空邊——8/9 效果指向不存在的 trigger_id
2. 退役邊——任何啟動(8)效果指向 退役_ 觸發（deactivate 允許）
3. 死亡路徑越權——監視/重生/命盡/馬監視 觸發啟動了非白名單目標
   （白名單＝復活鏈家族：監視|重生|命盡|馬監視|訊|啟動|選角、dl ◇位 變體）
4. ◇命 副本旗防——每支 ◇命 觸發必須帶命旗條件(Gaia 720 單格)或命 ref 條件，
   否則它一被打開就無條件生效（銀龍事故根因）
5. 啟動來源清單——選角/啟動器對非鏈觸發的啟動明細（人工複核用，不判錯）

用法: python -m analysis.audit_activation <scenario> [out_md]
結束碼: 0=無違規, 1=有違規。
"""
import sys, re

CHAIN_RE = re.compile(r'^(監視|重生|命盡|馬監視|訊|啟動|選角|轉生旗|補池|命旗)')
DEATH_RE = re.compile(r'^(監視|重生|命盡|馬監視)')
FLAG_CONST = 720
ACTIVATE, DEACTIVATE = 8, 9


def audit(tm, life_xs=None, life_refs=None):
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
            if et == ACTIVATE and DEATH_RE.match(tn):
                ok = CHAIN_RE.match(gn) or '◇位' in gn
                if not ok:
                    vio.append(('死亡路徑越權',
                                f'T{t.trigger_id}「{tn}」啟動 T{tid}「{gn}」'
                                f'(enabled={tgt.enabled})——非復活鏈白名單'))
            if et == ACTIVATE and (tn.startswith('選角') or tn.startswith('啟動')) \
                    and not CHAIN_RE.match(gn):
                review.append(f'T{t.trigger_id}「{tn}」→T{tid}「{gn}」'
                              f'(enabled={tgt.enabled})')

    # ◇命 副本旗防：必須有命旗條件（Gaia 720 單格 @life_xs 欄）或命 ref 條件
    for t in tm.triggers:
        tn = name(t)
        if '◇命' not in tn or tn.startswith('退役_'):
            continue
        has_flag = any(
            getattr(c, 'object_list', -1) == FLAG_CONST
            and getattr(c, 'source_player', -1) == 0
            and getattr(c, 'area_x1', -1) == getattr(c, 'area_x2', -2)
            and (life_xs is None or getattr(c, 'area_x1', -1) in life_xs)
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
                        f'T{t.trigger_id}「{tn}」無命旗/命ref條件——被打開即無條件生效'))
    return vio, review


def main(src, out_md=None):
    import yaml, os, io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    from AoE2ScenarioParser.scenarios.aoe2_de_scenario import AoE2DEScenario
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    spec = yaml.safe_load(open(os.path.join(here, 'merge_spec.yaml'), encoding='utf-8'))
    rv = (spec.get('params') or spec).get('revive') or {}
    life_xs = set(int(x) for x in (rv.get('cells') or {}).get('life_xs') or []) or None

    scn = AoE2DEScenario.from_file(src)
    vio, review = audit(scn.trigger_manager, life_xs=life_xs)

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
        open(out_md, 'w', encoding='utf-8').write(text)
        print(f'報表: {out_md}')
    print(f'違規 {len(vio)} 項、複核 {len(review)} 項')
    for k, s in vio[:40]:
        print(f'  [{k}] {s}')
    return 1 if vio else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None))

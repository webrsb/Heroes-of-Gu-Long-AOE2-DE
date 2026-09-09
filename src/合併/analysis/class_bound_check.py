# -*- coding: utf-8 -*-
"""s91 特徵斷言：職業綁定物件的 P8 託管（2026-09-06）。

座位≠職業以後，凡是「屬於某職業、開場就在圖上」的物件都必須走同一條路：
**開場歸 P8 → 選角時轉讓給入座玩家**。漏一種物件或漏一個座位都不會有紅字，
只會在遊戲裡默默錯人——鏡像漏改是視覺錯位，九環旗（任務計數種子）漏改是
所有任務門檻整體差 1（條件 OBJECTS_IN_AREA sp=座位 qty=2..9，種子沒轉讓就少一支）。
歷史：九環旗就是這樣漏掉的（本體、鏡像都改了，只有它留在 P{cid}）。

獨立於 s38/s39 重驗**最終檔狀態**：
  P — 每個綁定 ref 開場屬 P8（不是 P{cid}、也不是別家）
  T — 每個職業 ×6 座位的「選角{cid}位{s}」都把該 ref 由 8 轉給 s
  X — 選角觸發不得轉讓別職業的綁定 ref（防裁決表抄錯列）
回傳 [(ok, msg)]，s91 對 not ok 者升 BuildError。
"""
OWNERSHIP = 18
SLOTS = (1, 2, 3, 4, 5, 6)
# 表名 → 這張表在 params.revive 裡的鍵；hero_refs 是必填欄，其餘缺表即視為本檔沒有該類物件
TABLES = (('本體', 'hero_refs'), ('鏡像', 'mirrors'), ('九環旗', 'class_flags'))


def _sel(e):
    return list(getattr(e, 'selected_object_ids', None) or [])


def _tables(params):
    out = {}
    for label, key in TABLES:
        tbl = {int(k): int(v) for k, v in (params.get(key) or {}).items()}
        if tbl:
            out[label] = tbl
    return out


def check_class_bound(um, tm, params):
    tables = _tables(params)
    if not tables:
        return [(False, '缺 params.revive 的職業綁定表（hero_refs/mirrors/class_flags 全空），無從驗證')]
    out = []
    owner = {u.reference_id: p for p in range(9) for u in um.units[p]}
    ref2key = {}                       # ref → (表名, 職業)
    for label, tbl in tables.items():
        lack = [c for c in SLOTS if c not in tbl]
        if lack:
            out.append((False, f'P[{label}] 職業覆蓋不齊，缺 {lack}——座位變體會跟錯人'))
        for cid, ref in sorted(tbl.items()):
            if ref in ref2key:
                out.append((False, f'P[{label}] 職業{cid} ref{ref} 與 {ref2key[ref]} 重覆宣告'))
                continue
            ref2key[ref] = (label, cid)
            p = owner.get(ref)
            if p is None:
                out.append((False, f'P[{label}] 職業{cid} ref{ref} 不在單位表'))
            elif p != 8:
                out.append((False, f'P[{label}] 職業{cid} ref{ref} 開場屬 P{p}，應為 P8 託管'))
            else:
                out.append((True, f'P[{label}] 職業{cid} ref{ref} 開場 P8'))

    by_name = {}
    for t in tm.triggers:
        by_name.setdefault(t.name or '', []).append(t)
    for label, tbl in tables.items():
        for cid, ref in sorted(tbl.items()):
            for s in SLOTS:
                name = f'選角{cid}位{s}'
                ts = by_name.get(name) or []
                if len(ts) != 1:
                    out.append((False, f'T[{label}] 選角觸發「{name}」有 {len(ts)} 支（應為 1）'))
                    continue
                hit = [e for e in ts[0].effects
                       if getattr(e, 'effect_type', None) == OWNERSHIP
                       and ref in _sel(e)]
                if not hit:
                    out.append((False, f'T[{label}] {name} 沒轉讓職業{cid} ref{ref}'
                                       f'——該座位選了也拿不到'))
                    continue
                bad = [e for e in hit if getattr(e, 'source_player', None) != 8
                       or getattr(e, 'target_player', None) != s]
                if bad:
                    e = bad[0]
                    out.append((False, f'T[{label}] {name} 轉讓 ref{ref} 的方向錯：'
                                       f'P{getattr(e, "source_player", None)}→'
                                       f'P{getattr(e, "target_player", None)}，應為 P8→P{s}'))
                else:
                    out.append((True, f'T[{label}] {name} ref{ref} P8→P{s}'))

    for cid in SLOTS:
        for s in SLOTS:
            for t in by_name.get(f'選角{cid}位{s}') or []:
                for e in t.effects:
                    if getattr(e, 'effect_type', None) != OWNERSHIP:
                        continue
                    for ref in _sel(e):
                        key = ref2key.get(ref)
                        if key and key[1] != cid:
                            out.append((False, f'X 選角{cid}位{s} 轉讓了職業{key[1]}的'
                                               f'{key[0]} ref{ref}——裁決表抄錯列'))
    return out


def report_asymmetric_start_units(um):
    """報告項（不擋建置）：開場屬 P1..P6、卻**六座位不對稱**的單位。

    對稱＝六位玩家都在同一格擁有同 const 的一顆（顯示器、領航員、保命隱形物件都是這型，
    純座位資源，留在玩家手上才對）。不對稱則分三形狀，因為要人做的判斷不同：
      職業列   六位各一顆同 const、六格互異——九環旗就長這樣，**最可能是漏宣告**
      擺位參差 六位都有這個 const，只是有幾顆沒對齊（原作 837 顯示器就差一格）
      部分座位 只有一兩位有——原作給該座位的機關/佈景（P1 角落柵欄＋海牆＝「血2」鏈的機關、
               P6 重弩手在 T1「名」開場即轉手），留著才對
    已宣告的三張表在這時點都已是 P8，不會出現在這裡。"""
    cells = {}          # (const, player) → 該玩家持有此 const 的所有格
    for p in SLOTS:
        for u in um.units[p]:
            cells.setdefault((u.unit_const, p), set()).add((u.x, u.y))
    rows = []
    for p in SLOTS:
        for u in um.units[p]:
            sets = [cells.get((u.unit_const, q), set()) for q in SLOTS]
            if all((u.x, u.y) in st for st in sets):
                continue
            if not all(sets):
                smell = '只有部分座位有——多半是原作給該座位的機關/佈景'
            elif all(len(st) == 1 for st in sets) and len({next(iter(st)) for st in sets}) == len(SLOTS):
                smell = '六位各一顆同 const 且六格互異——職業列的形狀，先查是不是漏宣告'
            else:
                smell = '六位都有這個 const、只是這幾顆沒對齊——多半是原作擺位不齊'
            rows.append(f'B P{p} ref{u.reference_id} const{u.unit_const} '
                        f'@({u.x},{u.y}) 開場屬玩家但六座位不對稱：{smell}')
    return sorted(rows)

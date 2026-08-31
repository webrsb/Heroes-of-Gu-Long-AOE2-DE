# -*- coding: utf-8 -*-
"""結構不變量稽核（跑在建置中的產物上，由 s91 呼叫）。

2026-08-31 起因：東碼頭「精力不足封鎖」連兩次只在遊玩時才發現失效，而兩個根因都是**靜態可查**的：
  1. 封鎖器 id 比被攔的扣費大 → 同 tick 攔不住（DE 對同輪被啟動的觸發依 id 順序評估）。
  2. `object_hp` 被 parser 塞了預設 `sp=1` → s39 盤點判成跨職業 cross → 不生座位變體、
     `X船6` 變體的啟停邊也沒重指 → 封鎖器拆到原支、實際扣費的變體照跑。
既有 `audit_variants` 漏掉第 2 點的原因：它的 A1 規則前提是「目標**有**變體」，
而這裡的目標一個變體都沒有，於是掉進所有分支的縫裡。**只檢查「接錯」不檢查「該有的沒有」是盲區。**

閘門（違規即 BuildError）：
  K key 契約     —— spec 新增觸發須宣告 key: seat|class|global；seat 恰 5 個 ◇位 變體，class/global 恰 0
  E 變體邊同座位 —— 帶座位的觸發（原支或 ◇位s）的啟停邊指向 key=seat 的觸發時，必須指同座位那支
  O 攔截順序     —— 同一支同 tick 啟動 A 與 B、且 A 要停用 B 時，要求 A.id < B.id
  G 傳送迴圈     —— 傳送／任務的目的格不得落在任何傳送來源區內（會被原地反覆傳走）

報告（不擋建置，寫進 s91 log 供人看）：
  S 座位覆蓋   —— spec 條目按「名稱去掉開頭座位數字」分組，覆蓋不齊者列出（基底本來就缺的情形很常見）
  H 血量數值   —— `Change Object HP` 絕對值 > 32767（int16 天花板，超過回繞致死；負血技巧刻意用時屬預期）
"""
import re

ACT, DEACT, TELEPORT, TASK, CHANGE_HP = 8, 9, 35, 12, 27
INT16_MAX = 32767
VAR = re.compile(r'^(.*)◇位([1-6])$')
KEYS = ('seat', 'class', 'global')
DIGITS = set('123456')          # 不可寫成 `x in '123456'`：空字串是任何字串的子串（無名觸發會誤判）


def _g(o, k, d=-1):
    v = getattr(o, k, d)
    return d if v is None else v


def _by_name(triggers):
    d = {}
    for t in triggers:
        d.setdefault(t.name or '', []).append(t)
    return d


def spec_added(entries):
    """spec 的 trigger_add 條目 → {name: entry}。"""
    return {e['name']: e for e in entries if e.get('kind') == 'trigger_add' and e.get('name')}


def _holder_slot(name):
    """這支觸發屬於哪個座位：`◇位s` 優先，其次開頭數字（座位鍵命名慣例）。"""
    m = VAR.match(name or '')
    if m:
        return int(m.group(2))
    return int(name[0]) if (name or '')[:1] in DIGITS else None


def check_key_contracts(triggers, added):
    by = _by_name(triggers)
    out = []
    for name, entry in sorted(added.items()):
        key = entry.get('key')
        if key not in KEYS:
            out.append(f'K spec 新增觸發「{name}」未宣告 key（須為 {"/".join(KEYS)}）')
            continue
        base = by.get(name, [])
        if len(base) != 1:
            out.append(f'K「{name}」原支應恰 1 支，實得 {len(base)}')
            continue
        n_var = sum(len(by.get(f'{name}◇位{s}', [])) for s in range(1, 7))
        want = 5 if key == 'seat' else 0
        if n_var != want:
            hint = ''
            if want and not n_var:
                hint = ('（0 個＝被 s39 盤點判成 cross 或非家族：檢查有沒有幽靈玩家欄、'
                        '或條件／效果同時碰到兩個職業）')
            out.append(f'K「{name}」宣告 key={key} 應有 {want} 個座位變體，實得 {n_var}{hint}')
    return out


def check_variant_edges(triggers, added):
    """key=seat 的觸發，其所有進來的啟停邊都必須來自同座位（或無座位的全域觸發）。"""
    by = _by_name(triggers)
    seat_names = [n for n, e in added.items() if e.get('key') == 'seat']
    tid2 = {}
    for n in seat_names:
        s0 = _holder_slot(n)
        for t in by.get(n, []):
            tid2[t.trigger_id] = (n, s0)
        for slot in range(1, 7):
            for t in by.get(f'{n}◇位{slot}', []):
                tid2[t.trigger_id] = (n, slot)
    out = []
    for t in triggers:
        hs = _holder_slot(t.name or '')
        if hs is None:
            continue
        for i, e in enumerate(t.effects):
            if int(_g(e, 'effect_type', 0)) not in (ACT, DEACT):
                continue
            tgt = _g(e, 'trigger_id')
            if tgt in tid2:
                tname, tslot = tid2[tgt]
                if tslot != hs:
                    out.append(f'E T{t.trigger_id}「{t.name}」E#{i} 指向「{tname}」的位{tslot}，'
                               f'但本支在位{hs} → 應指同座位那支')
    return out


def _fires_immediately(t):
    """零條件（或只有 timer 0）＝一被武裝就在同一輪執行，攔截者必須有更小的 id 才來得及。
    有區域／計時等真條件的目標不算——那種情況攔截者通常還有機會（基底 3204 處都是這型，不該報）。"""
    for c in t.conditions:
        if int(_g(c, 'condition_type', 0)) == 10 and 0 <= _g(c, 'timer', -1) <= 0:
            continue
        return False
    return True


def _can_fire_same_tick(t):
    """帶 timer>0 的條件在被武裝的那一輪不可能成立 → 那支不是「同 tick 攔截者」，順序無所謂
    （例：X船窗止 timer 180 停用零條件的 X船入，是刻意的延後關窗，不是攔截）。"""
    for c in t.conditions:
        if int(_g(c, 'condition_type', 0)) == 10 and _g(c, 'timer', -1) > 0:
            return False
    return True


def _block_order_findings(triggers, allow=()):
    """同 tick 攔截順序：C 同時啟動 A、B，A 要停用 B，**B 零條件（立刻執行）且 A 也能在同輪執行**
    → 要求 A.id < B.id，否則 B 早跑掉（spike_objhp D 組實測：同輪依 id 順序）。產出 (訊息, (C, A, B))。"""
    by_id = {t.trigger_id: t for t in triggers}
    allow = {tuple(x) for x in allow}
    for t in triggers:
        armed = {_g(e, 'trigger_id') for e in t.effects if int(_g(e, 'effect_type', 0)) == ACT}
        armed = {a for a in armed if a in by_id}
        for a in sorted(armed):
            for e in by_id[a].effects:
                if int(_g(e, 'effect_type', 0)) != DEACT:
                    continue
                b = _g(e, 'trigger_id')
                if b in armed and a > b and (a, b) not in allow \
                        and _fires_immediately(by_id[b]) and _can_fire_same_tick(by_id[a]):
                    yield (f'O T{t.trigger_id}「{t.name}」同 tick 啟動 T{a}「{by_id[a].name}」與 '
                           f'T{b}「{by_id[b].name}」，而 T{a} 要停用零條件的 T{b} 但 id 較大 → 攔不住',
                           (t.trigger_id, a, b))


def check_block_order(triggers, allow=(), own_tids=None):
    """閘門用：own_tids 給定時只保留碰到「本次施工」的違規（基底既有形狀交給 report_block_order）。"""
    return [m for m, tids in _block_order_findings(triggers, allow)
            if own_tids is None or set(tids) & set(own_tids)]


def report_block_order(triggers, allow=(), own_tids=frozenset()):
    """報告用：與 check_block_order 互補——基底既有形狀（原作風格，多為無害狀態機）。"""
    return [m for m, tids in _block_order_findings(triggers, allow) if not set(tids) & set(own_tids)]


def own_trigger_ids(triggers, added):
    """spec 新增觸發及其 s39 副本（◇位／◇命）的 tid 集合。"""
    names = set(added)
    return {t.trigger_id for t in triggers if (t.name or '').split('◇')[0] in names}


def _areas(o):
    a = (_g(o, 'area_x1'), _g(o, 'area_y1'), _g(o, 'area_x2'), _g(o, 'area_y2'))
    return a if a[0] != -1 else None


def check_teleport_loops(triggers):
    """傳送／任務的目的格不得落在任何傳送來源區內（落地後又被傳走）。"""
    sources = []      # (tid, name, area)
    for t in triggers:
        for e in t.effects:
            if int(_g(e, 'effect_type', 0)) == TELEPORT:
                a = _areas(e)
                if a:
                    sources.append((t.trigger_id, t.name or '', a))
    out = []
    for t in triggers:
        for i, e in enumerate(t.effects):
            et = int(_g(e, 'effect_type', 0))
            if et not in (TELEPORT, TASK):
                continue
            x, y = _g(e, 'location_x'), _g(e, 'location_y')
            if x == -1:
                continue
            for stid, sname, (x1, y1, x2, y2) in sources:
                if x1 <= x <= x2 and y1 <= y <= y2:
                    out.append(f'G T{t.trigger_id}「{t.name}」E#{i} 目的格 ({x},{y}) 落在 '
                               f'T{stid}「{sname}」的傳送來源區 ({x1},{y1})-({x2},{y2}) 內 → 會被再傳走')
    return out


CREATE, OBJ_IN_AREA = 11, 5


def spec_tiles(triggers, added):
    """spec 新增觸發引進地圖的格子：CREATE_OBJECT 放物件的位置、傳送／任務的目的格。
    回傳 {(x, y): 說明}——這些是「我方新增的靜態存在」，最容易踩到原作的區域對話觸發。"""
    own = own_trigger_ids(triggers, added)
    tiles = {}
    for t in triggers:
        if t.trigger_id not in own:
            continue
        for i, e in enumerate(t.effects):
            et = int(_g(e, 'effect_type', 0))
            if et == CREATE:
                xy = (_g(e, 'location_x'), _g(e, 'location_y'))
                what = f'T{t.trigger_id}「{t.name}」E#{i} 放物件'
            elif et in (TELEPORT, TASK):
                xy = (_g(e, 'location_x'), _g(e, 'location_y'))
                what = f'T{t.trigger_id}「{t.name}」E#{i} {"傳送" if et == TELEPORT else "任務"}目的'
            else:
                continue
            if xy[0] != -1:
                tiles.setdefault(xy, what)
    return tiles


def report_area_overlap(triggers, added, max_side=40):
    """我方新增的格子若落在別人「玩家相關區域條件」內 → 列出複核。
    2026-08-30 廣場洗頻的教訓：s38 放的顯示器落在 `白雲X1` 的對話區內，每 16 秒洗一句永不停。
    刻意重疊（如渡船進入旗就在付費區內）也會列出，由人判斷——故為報告不是閘門。"""
    tiles = spec_tiles(triggers, added)
    own = own_trigger_ids(triggers, added)
    seen, out = set(), []
    for t in triggers:
        if t.trigger_id in own:
            continue
        for i, c in enumerate(t.conditions):
            if int(_g(c, 'condition_type', 0)) != OBJ_IN_AREA:
                continue
            sp = _g(c, 'source_player')
            if not 1 <= sp <= 6:
                continue
            a = _areas(c)
            if not a or a[2] - a[0] > max_side or a[3] - a[1] > max_side:
                continue
            for (x, y), what in tiles.items():
                if a[0] <= x <= a[2] and a[1] <= y <= a[3]:
                    base = (t.name or '').split('◇')[0]
                    if (x, y, base, i) in seen:
                        continue                     # 同一支的座位變體只報一次
                    seen.add((x, y, base, i))
                    out.append(f'A 我方格 ({x},{y})［{what}］落在「{t.name}」C#{i} 的玩家區域條件 '
                               f'({a[0]},{a[1]})-({a[2]},{a[3]}) sp={sp} 內')
    return out


def report_seat_coverage(entries, kinds=None, tag='S'):
    """spec 條目按「名稱去掉開頭座位數字」分組，覆蓋不齊者列出。
    kinds 可限定條目種類（如只看 trigger_add；基底編輯的單座位修正很常見、屬預期）。"""
    groups = {}
    for e in entries:
        if kinds and e.get('kind') not in kinds:
            continue
        nm = e.get('name') or e.get('target_name') or ''
        if nm[:1] in DIGITS:
            groups.setdefault(nm[1:], set()).add(int(nm[0]))
    return [f'{tag}「X{k}」spec 只覆蓋座位 {sorted(v)}（{len(v)}/6）'
            for k, v in sorted(groups.items()) if len(v) != 6]


def report_hp_range(triggers):
    out = []
    for t in triggers:
        for i, e in enumerate(t.effects):
            if int(_g(e, 'effect_type', 0)) == CHANGE_HP:
                q = _g(e, 'quantity', 0)
                if q is not None and abs(q) > INT16_MAX:
                    out.append(f'H T{t.trigger_id}「{t.name}」E#{i} Change HP {q}（>|{INT16_MAX}|，'
                               f'int16 回繞：實效 {((q + 32768) % 65536) - 32768}）')
    return out


def audit_all(triggers, spec_entries, allow_block_order=()):
    """回傳 (violations, reports)。violations 非空 → 呼叫端應中止建置。"""
    added = spec_added(spec_entries)
    own = own_trigger_ids(triggers, added)
    violations = (check_key_contracts(triggers, added)
                  + check_variant_edges(triggers, added)
                  + check_block_order(triggers, allow=allow_block_order, own_tids=own)
                  + check_teleport_loops(triggers))
    reports = (report_area_overlap(triggers, added)
               + report_block_order(triggers, allow=allow_block_order, own_tids=own)
               + report_seat_coverage(spec_entries, kinds=('trigger_add',), tag='S新增')
               + report_seat_coverage(spec_entries, kinds=('effect', 'condition', 'trigger',
                                                           'effect_add', 'condition_add'), tag='S編輯')
               + report_hp_range(triggers))
    return violations, reports

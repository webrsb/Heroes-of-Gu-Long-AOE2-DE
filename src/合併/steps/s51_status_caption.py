# -*- coding: utf-8 -*-
"""s51 狀態頭頂字幕（spec docs/superpowers/specs/2026-09-02-狀態頭頂字幕-design.md）。
狀態牌（每職業一顆，Change Object Name 寫入）→ 同觸發尾端附掛 change_object_caption
到該職業全部命 ref；清除類與「條件引用 mount_ref」的觸發加掛 mount_ref。
重生 timer／上馬拷貝補 caption ' '，保證新身體/新馬出場乾淨（替身不顯示）。
sel 有值時 sp 不過濾（通用指南 §7.1 實測）→ caption 一律 source_player=-1。"""
from core.change import Change
from .base import Step, BuildError, trig_by_id

CLEAR = ' '                       # caption 清除慣用手法（s39 清職業名同式）
RENAME, ACTIVATE, OWNERSHIP = 26, 8, 18


def load_status_caption(sc: dict):
    """裁決表載入：boards 六職業齊；texts find(strip) 唯一、to: null＝清除。"""
    boards = {int(k): int(v) for k, v in (sc.get('boards') or {}).items()}
    if sorted(boards.values()) != [1, 2, 3, 4, 5, 6]:
        raise BuildError(f'缺裁決：status_caption.boards 職業覆蓋不齊：{boards}')
    texts = {}
    for row in sc.get('texts') or []:
        if 'find' not in row or 'to' not in row:
            raise BuildError(f'缺裁決：status_caption.texts 列缺 find/to 欄：{row}（清除請明寫 to: null）')
        find = str(row['find']).strip()
        if find in texts:
            raise BuildError(f'缺裁決：status_caption.texts 重複 find「{find}」')
        to = row['to']
        if to is None:
            head = CLEAR
        else:
            head = str(to)
            if not head.strip():
                raise BuildError(f'缺裁決：texts「{find}」to 為空字串（清除請明寫 to: null）')
        bad = [ch for ch in head if not (ch.isascii() or '一' <= ch <= '鿿')]
        if bad:
            raise BuildError(f'缺裁決：texts「{find}」頭頂文含 caption 不支援字元 {bad}（僅 ASCII＋中日韓，§5.7a）')
        texts[find] = head
    if not texts:
        raise BuildError('缺裁決：status_caption.texts 空表')
    return boards, texts


def cond_refs(t):
    refs = set()
    for c in t.conditions:
        for a in ('unit_object', 'next_object'):
            v = getattr(c, a, -1)
            if v not in (-1, None):
                refs.add(v)
    return refs


def derive_boards(tm, life_refs, candidates):
    """由原觸發「X毒」推導 牌ref→職業，與裁決表對帳（spec §二.2，防寫死盲信）。
    原作重名前科（「6毒」＝T955 毒鏢任務＋T4472 設定器）→ 同名觸發以
    「恰一個狀態牌寫入」過濾，倖存者必須恰一支。"""
    derived = {}
    for cid in range(1, 7):
        named = [x for x in tm.triggers if (x.name or '') == f'{cid}毒']
        cands = []
        for t in named:
            hits = [e.selected_object_ids[0] for e in t.effects
                    if getattr(e, 'effect_type', None) == RENAME
                    and len(getattr(e, 'selected_object_ids', None) or []) == 1
                    and e.selected_object_ids[0] in candidates]
            if len(hits) == 1:
                cands.append((t, hits[0]))
        if len(cands) != 1:
            surv = '、'.join(f'T{t.trigger_id}(牌{b})' for t, b in cands)
            raise BuildError(f'缺前置：「{cid}毒」帶恰一個狀態牌寫入的觸發不是恰一支'
                             f'（同名 {len(named)}、倖存 {len(cands)}：{surv or "無"}）')
        t, board = cands[0]
        if life_refs[cid][0] not in cond_refs(t):
            raise BuildError(f'缺前置：「{cid}毒」條件未引用職業{cid}本體 ref{life_refs[cid][0]}')
        if board in derived:
            raise BuildError(f'缺前置：牌 ref{board} 同時被職業 {derived[board]} 與 {cid} 宣告')
        derived[board] = cid
    return derived


class StatusCaptionStep(Step):
    id = 's51'
    title = '狀態字幕'
    intro = '狀態牌寫入→頭頂 caption 附掛；重生/上馬清字（spec 2026-09-02）。'

    def apply(self, ctx):
        sc = ctx.spec.params.get('status_caption')
        if not sc:
            return []
        rv = ctx.notes.get('revive') or {}
        life_refs = rv.get('life_refs')
        if not life_refs:
            raise BuildError('缺前置：notes[revive].life_refs 不存在（s38 未跑？）')
        boards, texts = load_status_caption(sc)
        tm = ctx.base.trigger_manager
        derived = derive_boards(tm, life_refs, set(boards))
        if derived != boards:
            raise BuildError(f'缺裁決：牌ref→職業推導 {derived} 與 boards {boards} 不一致')
        rv_params = ctx.spec.params.get('revive') or {}
        mount_refs = {int(k): int(v) for k, v in (rv_params.get('mount_refs') or {}).items()}
        if sorted(mount_refs) != [1, 2, 3, 4, 5, 6]:
            raise BuildError(f'缺裁決：params.revive.mount_refs 職業覆蓋不齊：{mount_refs}')
        board_set = set(boards)
        changes, unknown, writes, mixed, ghost = [], {}, [], [], []
        for t in tm.triggers:
            for e in t.effects:
                if getattr(e, 'effect_type', None) != RENAME:
                    continue
                sel = list(getattr(e, 'selected_object_ids', None) or [])
                raw = (getattr(e, 'message', '') or '').strip()
                if not (set(sel) & board_set):
                    if raw in texts:   # 反向哨兵：非牌 sel 卻寫裁決表文字＝掃描盲點（區域模式/漏 ref）
                        ghost.append(f'T{t.trigger_id}「{t.name}」sel={sel}')
                    continue
                if len(sel) != 1:
                    mixed.append(f'T{t.trigger_id}「{t.name}」sel={sel}')
                    continue
                if raw not in texts:
                    unknown.setdefault(raw, f'T{t.trigger_id}「{t.name}」')
                    continue
                writes.append((t, boards[sel[0]], raw))
        problems = []          # 一次掃完統一報，分診不斷頭
        if mixed:
            problems.append('缺前置：狀態牌 sel 混搭：' + '；'.join(mixed))
        if ghost:
            problems.append('缺前置：非牌 sel 寫裁決表文字（掃描盲點）：' + '；'.join(ghost))
        if unknown:
            lst = '\n  '.join(f'「{k}」首見 {v}' for k, v in sorted(unknown.items()))
            problems.append(f'缺裁決：狀態牌文字不在 status_caption.texts（{len(unknown)} 種）：\n  {lst}')
        if problems:
            raise BuildError('\n'.join(problems))

        parents_of = {}          # activate 目標 → 父觸發（報告項用，一次線性掃建索引）
        for p in tm.triggers:
            for pe in p.effects:
                if getattr(pe, 'effect_type', None) == ACTIVATE:
                    parents_of.setdefault(getattr(pe, 'trigger_id', -1), []).append(
                        f'T{p.trigger_id}「{p.name}」')

        for t, cid, raw in writes:        # 先收集後附掛：不在迭代 effects 時 append
            head = texts[raw]
            with_mount = head == CLEAR or mount_refs[cid] in cond_refs(t)
            target = list(life_refs[cid]) + ([mount_refs[cid]] if with_mount else [])
            t.new_effect.change_object_caption(message=head, source_player=-1,
                                               selected_object_ids=target)
            tag = ('清除' if head == CLEAR else f'「{head}」') + \
                  f'（職業{cid}{"＋馬" if with_mount else ""}）'
            changes.append(Change(self.id, 'effect', f'T{t.trigger_id}「{t.name}」',
                                  'caption', f'「{raw}」', tag, 'spec §二.1 掛字規則'))
            keyset = set(life_refs[cid]) | {mount_refs[cid]}
            if head != CLEAR and not (cond_refs(t) & keyset):
                # 報告項：非本體ref鍵寫入器（spec §四）——條件未引用該職業命ref/mount_ref 的
                # 狀態設定（醉酒零條件型、6刀3 純TIMER型）；騎預置馬期間可能顯示缺口。清除類不列。
                changes.append(Change(self.id, 'report', f'T{t.trigger_id}「{t.name}」',
                                      '—', '',
                                      f'非本體ref鍵寫入器；父觸發：'
                                      f'{"、".join(parents_of.get(t.trigger_id, [])) or "無"}',
                                      '騎預置馬期間可能顯示缺口，複核用'))

        rvo = ctx.notes.get('revive_out') or {}
        timer = (rvo.get('chains') or {}).get('timer') or {}
        if not timer:
            raise BuildError('缺前置：notes[revive_out].chains.timer 空（s39 未跑？）')
        for key, tid in sorted(timer.items()):
            t = trig_by_id(tm, tid)
            deploy = [e for e in t.effects
                      if getattr(e, 'effect_type', None) == OWNERSHIP
                      and getattr(e, 'source_player', -1) == 0]
            if len(deploy) != 1 or len(deploy[0].selected_object_ids or []) != 1:
                raise BuildError(f'缺前置：重生觸發 T{tid} 部署效果不是恰一個單一 ref')
            ref = deploy[0].selected_object_ids[0]
            t.new_effect.change_object_caption(message=CLEAR, source_player=-1,
                                               selected_object_ids=[ref])
            changes.append(Change(self.id, 'effect', f'T{tid}「{t.name}」', 'caption',
                                  '', f'清字 ref{ref}', 'spec §三.1 重生清字'))
        mc = rvo.get('mount_copies')
        if mc is None:
            raise BuildError('缺前置：notes[revive_out].mount_copies 未曝露（s39 需增列）')
        for (cid, s, L), tid in sorted(mc.items()):
            t = trig_by_id(tm, tid)
            t.new_effect.change_object_caption(message=CLEAR, source_player=-1,
                                               selected_object_ids=[mount_refs[cid]])
            changes.append(Change(self.id, 'effect', f'T{tid}「{t.name}」', 'caption',
                                  '', f'清字 mount ref{mount_refs[cid]}', 'spec §三.2 上馬清字'))
        return changes

    def test_guide(self, changes):
        n = sum(1 for c in changes if c.kind == 'effect')
        rep = sum(1 for c in changes if c.kind == 'report')
        return (f'狀態頭頂字幕：附掛＋清字共 {n} 效果、報告項 {rep}（非本體ref鍵寫入器）。\n'
                '怎麼測：選角後讓毒物碰英雄 → 頭上出「中毒 2秒-100精力」且狀態牌同步；\n'
                '走解毒區 → 頭上清空；死亡重生 → 新身體頭上必乾淨（毒未解也不顯示）；\n'
                '上馬後再觸發震懾/中毒/內傷 → 馬頭上出字；買神弓 → 上膛亮「一觸即發」、卸下窗口乾淨。\n'
                '陽性對照：狀態牌本身照舊改名（原作行為未動）。\n'
                '異常判讀：頭上無字但牌有字＝附掛沒生效（回報觸發名）；替身/伯樂馬有字＝清字或掛字規則漏。')


STEP = StatusCaptionStep()

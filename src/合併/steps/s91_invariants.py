# -*- coding: utf-8 -*-
"""s91 結構不變量與特徵斷言（違規即 BuildError、不出檔）。

為什麼要有這一步（2026-08-31 定案）：渡船那套機制連續三次「建置全綠、進遊戲才炸」，
而事後追出來的根因全都是**靜態可查**的——封鎖器 id 比被攔的動作大（同 tick 攔不住）、
新增觸發被盤點判成 cross 而沒生座位變體、啟停邊指到別座位。
s90 查的是全檔通用不變量（攻擊力編碼／trigger_id 超界／dangling ref／觸發數對帳／空殼），
s91 查的是**這次施工的結構契約**：

  閘門（BuildError）：analysis.audit_structure 的 K/E/O/G ＋ 各特徵斷言（渡船／野怪平衡／狀態字幕／職業綁定物件）
  報告（寫進 log 供人看）：座位覆蓋 S、血量數值 H、開場單位六座位不對稱 B

spec 可用 `params.invariant_allow.block_order: [[a, b], ...]` 對「刻意讓大 id 停用小 id」放行。
"""
from core.change import Change
from .base import Step, BuildError


class InvariantStep(Step):
    id = 's91'
    title = '結構不變量'
    intro = 'key 契約／變體邊同座位／同 tick 攔截順序／傳送迴圈＋各功能特徵斷言；違規即中止。'

    def apply(self, ctx):
        from analysis.audit_structure import audit_all
        from analysis.ferry_check import check_ferry
        tm = ctx.base.trigger_manager
        entries = ctx.spec.params.get('trigger_fixes') or []
        allow = (ctx.spec.params.get('invariant_allow') or {}).get('block_order') or []
        violations, reports = audit_all(tm.triggers, entries, allow_block_order=allow)

        features = {'渡船': check_ferry(tm)} if any(
                e.get('kind') == 'trigger_add' and '船' in (e.get('name') or '') for e in entries) else {}
        # 兩種掛載條件來源不同，刻意不三元統一：渡船由 entries（本輪施工項）自動判定是否涉船；
        # 野怪平衡則由 params.mob_balance 這張裁決表本身是否存在來驅動，與 entries 無關。
        if ctx.spec.params.get('mob_balance'):
            from analysis.balance_check import check_mob_balance
            features['野怪平衡'] = check_mob_balance(tm, ctx.spec.params['mob_balance'])
        if ctx.spec.params.get('revive'):
            from analysis.class_bound_check import (check_class_bound,
                                                    report_asymmetric_start_units)
            features['職業綁定物件'] = check_class_bound(
                ctx.base.unit_manager, tm, ctx.spec.params['revive'])
            reports += report_asymmetric_start_units(ctx.base.unit_manager)
        if ctx.spec.params.get('status_caption'):
            from analysis.status_check import check_status_caption
            features['狀態字幕'] = check_status_caption(tm, ctx.spec.params, ctx.notes)
        n_feature = 0
        for tag, results in features.items():
            n_feature += len(results)
            violations += [f'F[{tag}] {msg}' for ok, msg in results if not ok]

        ctx.notes['invariant_reports'] = reports
        if violations:
            head = f'結構不變量未過（{len(violations)} 項）：'
            raise BuildError(head + '\n  ' + '\n  '.join(violations[:40])
                             + ('\n  …（其餘省略）' if len(violations) > 40 else ''))
        changes = [Change(self.id, 'audit', '全檔', '—', '',
                          f'K/E/O/G 0 違規；特徵斷言 {n_feature} 項全過',
                          'audit_structure ＋ ferry_check ＋ balance_check')]
        changes += [Change(self.id, 'report', '—', '—', '', r, '複核用，不擋建置') for r in reports]
        return changes

    def test_guide(self, changes):
        reports = [c.new for c in changes if c.kind == 'report']
        if not reports:
            return '結構不變量：閘門全過，無待複核項。'
        import collections, re
        tally = collections.Counter((re.match(r'S新增|S編輯|[ABKEOGH]', r) or [''])[0] for r in reports)
        legend = {'A': '我方新增的格子落在原作的玩家區域條件內（廣場洗頻型，刻意重疊也會列出）',
                  'O': '基底既有的同 tick 攔截形狀（原作風格，多為無害狀態機）',
                  'H': 'Change HP 超過 int16 天花板 32767（負血技巧刻意用時屬預期）',
                  'B': '開場屬玩家、六座位卻不對稱的單位（座位機關/佈景屬正常；'
                       '若是某職業專屬就是漏宣告職業綁定物件，九環旗那次就這樣漏的）',
                  'S新增': 'spec 新增觸發的座位覆蓋不齊',
                  'S編輯': 'spec 編輯基底時只改了部分座位（單座位修正很常見）'}
        lines = [f'  {k} ×{v}　{legend.get(k, "")}' for k, v in sorted(tally.items())]
        return ('結構不變量：閘門（key 契約／變體邊同座位／同 tick 攔截順序／傳送迴圈＋特徵斷言）全過。\n'
                '以下為報告項，不擋建置，只在懷疑某功能怪異時回頭查 logs/91_結構不變量.tsv：\n'
                + '\n'.join(lines)
                + '\n  新增功能後請務必看「S新增」那一類——座位沒補齊是最常見的漏。')


STEP = InvariantStep()

# -*- coding: utf-8 -*-
"""DE 字型缺字換字裁決表（2026-09-01）。

事實（`analysis/font_check.py` 實測）：DE 的 CJK 不走系統字型，而是預烘的點陣字圖集
（`resources/_common/fonts/combined.txt` 與 `combined_sansserif.txt`，兩份覆蓋完全相同）：
共 7697 字，其中 CJK 統一漢字只有 **5510** 個。清單外的字**不 fallback、直接開天窗**——
這就是使用者在遊戲中看到「多處缺字」的原因。本檔是換字裁決，`validate()` 保證
「每個替代字自己在覆蓋表內」且「套用後全檔缺字歸零」。

裁決原則（依序）：
1. **同音優先**（人名、招式名）：讀音不變，玩家唸得出來也認得出是誰 —— 櫻→英、檐→岩、刁→雕。
2. **同義次之**（一般詞）：棧→店（客店）、瀛→洋（東洋）、舫→船（畫船）、衲→僧（老僧）。
3. **順手改對**：原作本來就寫錯或用了方言字 —— 磹斧兵→擲斧兵（AoE2 正式譯名）、
   ㄧ→一（注音符號誤用）、竅→鞘（金劍出鞘）、搵→找／冇→沒（粵語）。
4. **標點取覆蓋表內的等價形**：全形數字→半形（全形 ０–９ 整組沒有）、＜＞→《》、【】→「」、
   ＊→*、ｈｐ→hp。**絕不用半形 `<` `>`**——那是 DE 的顏色標籤定界符，會被吃掉。
5. 詞級規則先跑、字級規則後跑（`秘訣→秘技` 這種字級換不好的才進詞級）。

用法（在 src/合併 下）：
    python -m tools.gen_glyph_fixes            # 驗證＋輸出報告到 reports/
    python -m tools.gen_glyph_fixes --check    # 只驗證（給 CI／建置前用）
"""
import io
import sys
from pathlib import Path

sys.path.insert(0, __file__.rsplit('tools', 1)[0])

SCENARIO = 'out/古龍921_合併.aoe2scenario'

# ── 詞級規則（先跑，順序有意義）─────────────────────────────────────────────
WORD = [
    ('秘訣', '秘技', '訣字級換不好（口訣≠口技）；「秘技」是現成同義詞'),
    ('口訣', '口令', '同上；開門用的口訣＝口令，語意不變'),
    ('衙門', '官府', '衙字級換成「府門」不成詞；整詞換「官府」最直白'),
    ('磹斧兵', '擲斧兵', '原作錯字：AoE2 的 Throwing Axeman 正式譯名是「擲斧兵」'),
    # 不是缺字，但同一族的「只有遊玩才發現」：DE 把 <…> 當標記解析，不認識的可能整段吃掉
    ('<迪加>', '「迪加」', '`<迪加>任務學家` 的角括號會被 DE 的標籤解析器吃掉（同「不可用半形 <>」'
                          '那條理由）；改成引號保住名字'),
]

# ── 私用區殘留（跑在 word 之後、char 之前）──────────────────
# U+F6F3 是 Big5 造字區殘留（轉碼時落進 Unicode 私用區），同一碼位在兩處扮不同角色，
# 只能各自處理。**以碼位而非字元本身入 spec**：raw PUA 字元寫進 YAML 會變成看不見的地雷，
# 編輯器一動就壞（merge_spec 曾被原生 DEL 咬過兩次）。`after` 是錨點，換掉錨點後那一個字。
PUA = [
    ('F6F3', '新任務', '：', 'U+F6F3 在此作分隔號（「新增兩項新任務□哈囉德哈」）→ 全形冒號'),
    ('F6F3', '殺１', '　', 'U+F6F3 在此作對齊填充（「周賓殺１□4000」，原字已不可考）→ '
                          '全形空白，不編造語意。錨點帶全形１，故必須排在字級降半形之前'),
]

# ── 字級規則 ────────────────────────────────────────────────────────────────
# (缺字, 替代, 類型, 理由)
CHAR = [
    ('棧', '店', '同義', '客棧→客店；「棧」不在覆蓋表，403 處全是「客棧」相關'),
    ('鵬', '鷹', '同義', '金鵬島→金鷹島、飛鵬幫→飛鷹幫、大金鵬王→大金鷹王；同為大鳥，專名仍可辨'),
    ('闆', '板', '異體', '老闆→老板；「板」本來就是「闆」的通用替代寫法'),
    ('灸', '炙', '異體', '針灸→針炙；台港通行的替代寫法，字義同為灼燒'),
    ('櫻', '英', '同音', '蘇櫻→蘇英；ying 同音，人名讀音不變（次選：鶯、梅）'),
    ('逛', '走', '同義', '去逛逛→去走走'),
    ('藺', '林', '同音', '燒酒商人藺戰→林戰；lìn/lín 近音，仍是常見姓氏（次選：蘭）'),
    ('衲', '僧', '同義', '老衲→老僧；出家人自稱，語域不變'),
    ('爹', '父', '同義', '我爹→我父；「爸」也不在覆蓋表，只剩「父」'),
    ('箍', '環', '同義', '如意金箍棒→如意金環棒；箍＝環，且本圖既有「九環旗」用詞一致'),
    ('嵋', '眉', '異體', '峨嵋→峨眉；標準異寫，山名照樣認得'),
    ('瀛', '洋', '同義', '東瀛白衣甲→東洋白衣甲；同指日本'),
    ('竅', '鞘', '改對', '金劍出竅→金劍出鞘；原作本來就該用「鞘」（出竅是元神）'),
    ('訣', '技', '同義', '詞級規則沒吃到的殘餘一律→技（秘訣→秘技）'),
    ('搵', '找', '方言', '粵語「搵」→「找」；出現在改版記錄'),
    ('冇', '沒', '方言', '粵語「冇」→「沒」；冇錢→沒錢'),
    ('舫', '船', '同義', '畫舫→畫船'),
    ('磹', '擲', '改對', '詞級沒吃到的殘餘；見「磹斧兵」'),
    ('檐', '岩', '同音', '祭品商人東方檐→東方岩；yán 同音（「簷」也不在覆蓋表）'),
    ('刁', '雕', '同音', '刁手弓→雕手弓；diāo 同音，且與弓箭意象相合'),
    ('衙', '府', '同義', '詞級沒吃到的殘餘；見「衙門」'),
    ('ㄧ', '一', '改對', '注音符號 ㄧ(U+3127) 誤當「一」用（Big5 時代常見）；略知ㄧ二→略知一二'),
    ('０', '0', '全形', '全形數字 ０–９ 整組不在覆蓋表，一律降半形'),
    ('１', '1', '全形', '同上'),
    ('２', '2', '全形', '同上'),
    ('５', '5', '全形', '同上'),
    ('８', '8', '全形', '同上'),
    ('９', '9', '全形', '同上'),
    ('ｈ', 'h', '全形', '全形拉丁字母整組不在覆蓋表；ｈｐ→hp'),
    ('ｐ', 'p', '全形', '同上'),
    ('＊', '*', '全形', '＊雜貨店老闆外出＊→*…*；※★等替代符號也都不在覆蓋表，只剩半形'),
    ('＜', '《', '標點', '＜金庸＞→《金庸》。**不可用半形 < >**——DE 會當成顏色標籤定界符'),
    ('＞', '》', '標點', '同上'),
    ('【', '「', '標點', '【破軍】→「破軍」、【^迪加^】→「^迪加^」；招式名與人名都讀得通，'
                        '且「」《》原檔皆未使用，不會與既有用法撞'),
    ('】', '」', '標點', '同上'),
]


def apply_all(text):
    """套用全部規則。實作在 steps/s85_glyph.apply_rules（建置期跑的那份），這裡只是同一份
    裁決表餵進去——驗證與實際施作共用同一條路徑，才不會驗過了卻做出別的結果。"""
    from steps.s85_glyph import apply_rules
    return apply_rules(text, WORD, PUA, CHAR)


def validate(scenario=SCENARIO):
    """→ [(ok, 說明)]。三關：替代字自己要在覆蓋表、規則不得是空砲、套用後缺字歸零。"""
    from analysis.font_check import load_coverage, visible_texts, missing, MARKUP
    from core.scenario_io import load
    cov = load_coverage()
    out = []
    for old, new, why in WORD:
        bad = [c for c in apply_all(new) if c not in cov]
        out.append((not bad, f'詞級「{old}」→「{new}」：'
                             + (f'替代字 {bad} 自己也缺字！' if bad else '替代字全在覆蓋表')))
    for code, after, new, why in PUA:
        bad = [c for c in apply_all(new) if c not in cov]
        out.append((not bad, f'私用區 U+{code} 於「{after}」後 →「{new}」：'
                             + (f'替代字 {bad} 自己也缺字！' if bad else '替代字全在覆蓋表')))
    for old, new, kind, why in CHAR:
        bad = [c for c in new if c not in cov]
        out.append((not bad, f'字級「{old}」→「{new}」（{kind}）：'
                             + (f'替代字 {bad} 自己也缺字！' if bad else 'OK')))
    scn = load(scenario)
    miss = missing(scn, cov)
    covered = set(miss) - {''}
    ruled = {c for c, *_ in CHAR} | {chr(int(code, 16)) for code, *_ in PUA}
    orphan = sorted(covered - ruled)
    out.append((not orphan, f'實檔缺字 {len(miss)} 種都有裁決'
                            + (f'；缺裁決：{orphan}' if orphan else '')))
    dead = sorted(ruled - set(miss))
    out.append((not dead, '沒有空砲規則' + (f'；這些字實檔沒出現：{dead}' if dead else '')))
    left = {}
    for src, text in visible_texts(scn):
        for ch in MARKUP.sub('', apply_all(text)):
            if ch not in cov and ch not in '\r\n\t':
                left.setdefault(ch, src)
    out.append((not left, '套用後缺字歸零'
                          + (f'；仍缺 {[(c, s) for c, s in left.items()]}' if left else '')))
    return out


def render_md(scenario=SCENARIO):
    from analysis.font_check import load_coverage, missing
    from core.scenario_io import load
    cov = load_coverage()
    miss = missing(scn := load(scenario), cov)
    n_hanzi = sum(1 for c in cov if 0x4E00 <= ord(c) <= 0x9FFF)
    total = sum(len(v) for v in miss.values())
    L = [f'# DE 字型缺字裁決 — {Path(scenario).name}', '',
         f'DE 的 CJK 不走系統字型，而是預烘的點陣字圖集（`resources/_common/fonts/combined.txt`'
         f' 與 `combined_sansserif.txt`，兩份覆蓋實測完全相同）：共 **{len(cov)}** 字，'
         f'其中 CJK 統一漢字只有 **{n_hanzi}** 個。清單外的字**不 fallback、直接開天窗**。', '',
         f'本檔缺字 **{len(miss)} 種、{total} 處**。裁決原則：同音優先（人名招式名）→ 同義次之 →'
         f'原作本來就寫錯的順手改對 → 標點取覆蓋表內的等價形。', '',
         '⚠ 絕不可用半形 `<` `>` 代替全形＜＞：那是 DE 顏色標籤的定界符，會被引擎吃掉。', '',
         '## 字級換字', '',
         '| 缺字 | 碼位 | 處數 | 換成 | 類型 | 理由 |', '|---|---|---|---|---|---|']
    n = {c: len(v) for c, v in miss.items()}
    for old, new, kind, why in sorted(CHAR, key=lambda r: -n.get(r[0], 0)):
        L.append(f'| {old} | U+{ord(old):04X} | {n.get(old, 0)} | {new} | {kind} | {why} |')
    from analysis.font_check import suspect_tags
    L += ['', '## 詞級換字（先跑，字級換不好的才進這裡）', '',
          '| 原詞 | 換成 | 理由 |', '|---|---|---|']
    for old, new, why in WORD:
        L.append(f'| `{old}` | `{new}` | {why} |')
    L += ['', '### 私用區殘留（以碼位入 spec，不讓看不見的字元進 YAML）', '',
          '| 碼位 | 錨點 | 換成 | 理由 |', '|---|---|---|---|']
    for code, after, new, why in PUA:
        L.append(f'| U+{code} | `{after}` | `{new}` | {why} |')
    sus = suspect_tags(scn)
    L += ['', '## 順帶抓到：可疑 `<…>` 片段（不是缺字，但同族的「只有遊玩才發現」）', '',
          'DE 把 `<…>` 當標記解析，不認識的可能整段吃掉——玩家看到的是憑空少一段。', '',
          '| 片段 | 處數 | 出現處 |', '|---|---|---|']
    for frag, hits in sorted(sus.items(), key=lambda kv: -len(kv[1])):
        L.append(f'| `{frag}` | {len(hits)} | {hits[0][0]}｜…{hits[0][1]}… |')
    L += ['', '## 驗證', '']
    for ok, msg in validate(scenario):
        L.append(f'- {"✅" if ok else "❌"} {msg}')
    L += ['', '## 落地方式（尚未施作）', '',
          '1. 新增 `steps/s33_glyph.py`：對「玩家看得到的文字」逐條套 WORD→CHAR 規則。',
          '   **必須排在 `s34_messages` 之後**——s34 拿原文舊字串做防呆比對，先換字會讓它全部失配。',
          '2. `s90 終檢` 加一條不變量：套用後仍有覆蓋表外的字即 `BuildError`（把「只有遊玩才發現」'
          '變成建置期錯誤，同 s91 的思路）。',
          '3. 觸發名稱不換——玩家看不到，且多個步驟拿名稱做防呆與配對。']
    return '\n'.join(L) + '\n'


def render():
    """→ merge_spec 用的 params.glyph_fixes 區塊（已縮排）。"""
    import textwrap
    import yaml
    data = {'word': [list(r) for r in WORD],
            'pua': [list(r) for r in PUA],
            'char': [list(r) for r in CHAR]}
    return textwrap.indent(yaml.safe_dump(data, allow_unicode=True, sort_keys=False,
                                          default_flow_style=None, width=250), '    ')


def main(argv):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    scenario = next((a for a in argv[1:] if not a.startswith('--')), SCENARIO)
    results = validate(scenario)
    for ok, msg in results:
        if not ok:
            print('FAIL ' + msg)
    bad = sum(1 for ok, _ in results if not ok)
    print(f'{len(results)} 項檢查，{bad} 項不符')
    if bad:
        return 1
    if '--check' not in argv:
        out = Path('reports/字型缺字裁決.md')
        out.write_text(render_md(scenario), encoding='utf-8')
        print(f'報告：{out}')
        if '--spec' in argv:
            print('    # 【2026-09-01 DE 字型缺字換字裁決】由 tools/gen_glyph_fixes.py 產生')
            print('    glyph_fixes:')
            print(render(), end='')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))

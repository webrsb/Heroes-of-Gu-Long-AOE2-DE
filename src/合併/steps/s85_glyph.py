# -*- coding: utf-8 -*-
"""s85 字型缺字換字（params.glyph_fixes）。

DE 的 CJK 不走系統字型，而是預烘的點陣字圖集（`resources/_common/fonts/combined*.txt`）：
共 7697 字、CJK 統一漢字只有 5510 個，清單外的字**不 fallback、直接開天窗**。
本步驟把玩家看得到的文字逐條換成覆蓋表內的等價字（裁決表見 `tools/gen_glyph_fixes.py`
與 `reports/字型缺字裁決.md`）。

**為什麼排在最後（s85，s80 之後、s90 之前）**：要蓋到全部文字來源，包含 s37 新增的私訊、
s371 重命名、s372/s373 的野怪名、s39 的 ◇位 變體副本——這些都在 s34 之後才生出來。
反過來也成立：s34 拿原文舊字串做防呆比對，若換字先跑會讓它全部失配。

**不換觸發名稱**：玩家看不到（只在編輯器），且 s37/s38/s39 與多支稽核拿名稱做防呆與配對。

三張表按序套用（順序有意義）：
  word: [[舊, 新, 理由]]                     — 字級換不好的整詞換（口訣→口令，字級會變口技）
  pua:  [[碼位hex, 錨點, 新, 理由]]           — Big5 造字區殘留；以碼位入 spec，不讓 raw PUA 進 YAML
  char: [[缺字, 替代, 類型, 理由]]            — 主表
"""
from core.change import Change
from .base import Step, BuildError

FIELDS = ('instructions', 'hints', 'victory', 'loss', 'history', 'scouts')
WHY = 'DE 字圖集覆蓋外的字，遊戲中會開天窗（裁決見 reports/字型缺字裁決.md）'


def apply_rules(text, word=(), pua=(), char=()):
    """純函式：按 word → pua → char 的順序換字。"""
    for old, new, *_ in word:
        text = text.replace(old, new)
    for code, after, new, *_ in pua:
        text = text.replace(after + chr(int(code, 16)), after + new)
    for old, new, *_ in char:
        text = text.replace(old, new)
    return text


def _tables(params):
    word = [tuple(r) for r in (params.get('word') or [])]
    pua = [tuple(r) for r in (params.get('pua') or [])]
    char = [tuple(r) for r in (params.get('char') or [])]
    for r in word:
        if len(r) < 2 or not r[0]:
            raise BuildError(f'缺裁決：glyph_fixes.word 條目格式錯誤 {r!r}（需 [舊, 新, 理由]）')
    for r in pua:
        if len(r) < 3 or len(r[2]) != 1:
            raise BuildError(f'缺裁決：glyph_fixes.pua 條目格式錯誤 {r!r}（需 [碼位hex, 錨點, 單一新字, 理由]）')
        try:
            int(r[0], 16)
        except ValueError:
            raise BuildError(f'缺裁決：glyph_fixes.pua 碼位「{r[0]}」不是十六進位')
    for r in char:
        if len(r) < 2 or len(r[0]) != 1 or not r[1]:
            raise BuildError(f'缺裁決：glyph_fixes.char 條目格式錯誤 {r!r}（需 [單一缺字, 替代, 類型, 理由]）')
    return word, pua, char


def apply_glyph(scn, params):
    """就地換字，回傳 Change 列（每個文字來源一筆，內容不變者不記）。"""
    word, pua, char = _tables(params)
    changes, hits = [], {}

    def fix(label, text):
        new = apply_rules(text, word, pua, char)
        if new == text:
            return text
        for old, _, *_ in word:
            hits[old] = hits.get(old, 0) + text.count(old)
        for code, after, *_ in pua:
            hits[f'U+{code}'] = hits.get(f'U+{code}', 0) + text.count(after + chr(int(code, 16)))
        for old, *_ in char:
            if old in text:
                hits[old] = hits.get(old, 0) + text.count(old)
        changes.append(Change('s85', 'glyph', label, 'text', _snip(text), _snip(new), WHY))
        return new

    mm = scn.message_manager
    for f in FIELDS:
        cur = getattr(mm, f, None)
        if cur:
            setattr(mm, f, fix(f'劇情文字.{f}', cur))
    for p in scn.player_manager.players:
        if getattr(p, 'name', None):
            p.name = fix(f'玩家名.P{p.player_id}', p.name)
    for t in scn.trigger_manager.triggers:
        for f, tag in (('short_description', '目標'), ('description', '說明')):
            cur = getattr(t, f, None)
            if cur:
                setattr(t, f, fix(f'T{t.trigger_id}「{t.name}」{tag}', cur))
        for i, e in enumerate(t.effects):
            if getattr(e, 'message', None):
                e.message = fix(f'T{t.trigger_id}「{t.name}」E#{i}', e.message)
    summary = '、'.join(f'{k}×{v}' for k, v in sorted(hits.items(), key=lambda kv: -kv[1]))
    changes.append(Change('s85', 'glyph_summary', f'{len(changes)} 處文字', 'chars', '',
                          f'{len(hits)} 種缺字', summary))
    return changes


def _snip(text, n=48):
    one = text.replace('\r', ' ').replace('\n', ' ')
    return one[:n] + ('…' if len(one) > n else '')


class GlyphStep(Step):
    id = 's85'
    title = '字型缺字換字'
    intro = ('DE 的點陣字圖集只有 5510 個漢字、清單外不 fallback；依 params.glyph_fixes 把'
             '玩家看得到的文字換成覆蓋表內的等價字。排在最後才蓋得到 s37/s371/s373/s39 生出來的文字。')

    def apply(self, ctx):
        params = ctx.spec.params.get('glyph_fixes')
        if not params:
            return []
        return apply_glyph(ctx.base, params)

    def test_guide(self, changes):
        if not changes:
            return None
        summary = next((c for c in changes if c.kind == 'glyph_summary'), None)
        return ('字型缺字換字：' + (summary.reason if summary else '') + '\n'
                '怎麼測：單人→劇情開局看任務欄（提示）——原本開天窗的地方應該都有字了，'
                '重點看「客店」「老板」「針炙」「金鷹島」「峨眉弟子」「擲斧兵」「略知一二」'
                '與技能表的等級數字（原本全形數字整組不顯示，現在是半形 10/50/100）。\n'
                '對白抽驗：白雲城雜貨店老板、醫師教針炙、蘇英、燒酒商人林戰、老僧（少林大師）。\n'
                '異常判讀：還有開天窗＝回報那句話的完整文字（s90 缺字閘門本該擋住，'
                '漏了表示該字不在裁決表裡）；字換得看不懂＝回報原句與你想要的字。')


STEP = GlyphStep()

# -*- coding: utf-8 -*-
"""DE 字型缺字稽核：把劇情檔「玩家看得到的文字」逐字對 DE 點陣字圖集的覆蓋表比對。

為什麼需要：DE 不用系統字型算 CJK，而是預先烘好的字圖集
（`resources/_common/fonts/combined*.txt` 是它的清單）。清單裡沒有的字**不會 fallback**，
遊戲中直接開天窗——這是使用者實際看到「多處缺字」的原因，只有進遊戲才會發現，
所以要變成靜態可查（同 s90/s91 的思路）。

覆蓋表：`combined.txt` 與 `combined_sansserif.txt` 兩份實測完全相同（7697 字，
其中 CJK 統一漢字 5510 個），故任一份即可代表。格式：
    Glyph - 'A'    W(17), H(45), ...      ← ASCII 直接給字元
    Glyph - 24246  W(...), ...            ← 其餘給十進位碼位

文字來源（玩家看得到的全部）：
  - 五個劇情文字欄（instructions/hints/victory/loss/history/scouts）
  - 觸發的 short_description（目標面板）與 description
  - 效果的 message（send_chat／display_instructions／change_object_name…）
  - 玩家名稱、劇情檔名
觸發名稱**不算**——玩家看不到（只在編輯器）。

用法（在 src/合併 下）：
    python -m analysis.font_check <scenario> [fonts_dir]
"""
import re
import sys
from pathlib import Path

FONTS = Path(r'D:\Program Files (x86)\Steam\steamapps\common\AoE2DE\resources\_common\fonts')
GLYPH = re.compile(r"^Glyph - (?:'(.)'|(\d+))\s", re.M)
# DE 的顏色標籤（不顯示，故不算缺字）。**只認這七個**——寫成通用的 `<[^<>]+>` 會把
# 「差<3 且 x>5」這種比較式整段吃掉，反而藏住裡面的缺字。非顏色標籤的 `<…>` 交給
# suspect_tags() 當可疑項報出來（實例：`<迪加>任務學家`，DE 可能整段當標籤吃掉）。
COLORS = ('ORANGE', 'GREEN', 'AQUA', 'YELLOW', 'RED', 'PURPLE', 'BLUE')
MARKUP = re.compile(r'<(?:%s)>' % '|'.join(COLORS))
ANGLE = re.compile(r'<[^<>\r\n]{1,20}>')


def load_coverage(fonts_dir=FONTS):
    """→ 可顯示字元集。兩份圖集清單取聯集（實測相同，取聯集只為保險）。"""
    files = [p for p in (Path(fonts_dir) / 'combined.txt',
                         Path(fonts_dir) / 'combined_sansserif.txt') if p.exists()]
    if not files:
        raise FileNotFoundError(f'找不到字圖集清單：{fonts_dir}\\combined.txt')
    cov = set()
    for p in files:
        for a, b in GLYPH.findall(p.read_text(encoding='utf-8')):
            cov.add(a if a else chr(int(b)))
    return cov


def visible_texts(scn):
    """→ [(來源標籤, 文字)]，只收玩家看得到的。"""
    out = []
    mm = scn.message_manager
    for fld in ('instructions', 'hints', 'victory', 'loss', 'history', 'scouts'):
        v = getattr(mm, fld, None)
        if v:
            out.append((f'劇情文字.{fld}', v))
    for p in scn.player_manager.players:
        if getattr(p, 'name', None):
            out.append((f'玩家名.P{p.player_id}', p.name))
    for t in scn.trigger_manager.triggers:
        for fld, tag in (('short_description', '目標'), ('description', '說明')):
            v = getattr(t, fld, None)
            if v:
                out.append((f'T{t.trigger_id}「{t.name}」{tag}', v))
        for i, e in enumerate(t.effects):
            if getattr(e, 'message', None):
                out.append((f'T{t.trigger_id}「{t.name}」E#{i}', e.message))
    return out


def missing(scn, cov=None):
    """→ {缺字: [(來源, 前後文), …]}（前後文取該字左右各 12 字）。"""
    cov = cov or load_coverage()
    out = {}
    for src, text in visible_texts(scn):
        clean = MARKUP.sub('', text)
        for i, ch in enumerate(clean):
            if ch in cov or ch in '\r\n\t':
                continue
            out.setdefault(ch, []).append((src, clean[max(0, i - 12):i + 13]))
    return out


def suspect_tags(scn):
    """→ {`<…>` 片段: [(來源, 前後文), …]}，只收不是顏色標籤的。
    DE 把 `<…>` 當標記解析，不認識的可能整段吃掉——玩家看到的是「憑空少一段」，
    與缺字同一族的「只有遊玩才發現」。"""
    out = {}
    for src, text in visible_texts(scn):
        for m in ANGLE.finditer(text):
            if MARKUP.fullmatch(m.group(0)):
                continue
            out.setdefault(m.group(0), []).append(
                (src, text[max(0, m.start() - 10):m.end() + 10]))
    return out


def main(argv):
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    from core.scenario_io import load
    cov = load_coverage(argv[2] if len(argv) > 2 else FONTS)
    print(f'字圖集覆蓋 {len(cov)} 字（CJK 統一漢字 '
          f'{sum(1 for c in cov if 0x4E00 <= ord(c) <= 0x9FFF)} 個）')
    scn = load(argv[1])
    miss = missing(scn, cov)
    total = sum(len(v) for v in miss.values())
    print(f'缺字 {len(miss)} 種、{total} 處\n')
    for ch, hits in sorted(miss.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        print(f'U+{ord(ch):04X} 「{ch}」×{len(hits)}')
        for src, ctx in hits[:3]:
            print(f'    {src}｜…{ctx}…')
        if len(hits) > 3:
            print(f'    （另 {len(hits) - 3} 處）')
    sus = suspect_tags(scn)
    print(f'\n可疑 `<…>` 片段（非顏色標籤，DE 可能整段吃掉）：{len(sus)} 種')
    for frag, hits in sorted(sus.items(), key=lambda kv: -len(kv[1])):
        print(f'  {frag} ×{len(hits)}｜{hits[0][0]}｜…{hits[0][1]}…')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))

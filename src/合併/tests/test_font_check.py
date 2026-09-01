# -*- coding: utf-8 -*-
"""DE 字型缺字稽核：字圖集清單解析、標記剝除、玩家可見文字盤點、換字規則。
不碰真實字型檔（在遊戲安裝目錄，不是每台機器都有），全部用合成資料或版控快照。"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from types import SimpleNamespace as NS

import pytest

from analysis import font_check
from analysis.font_check import (
    GLYPH, MARKUP, visible_texts, missing, suspect_tags)
from tools.gen_glyph_fixes import WORD, CHAR, apply_all

ATLAS = """Font File Atlas Summary
-----------------------
Glyphs : 3
-----------------------

Glyph - 9    W(35), H(42), UV(0.28, 0.89)
Glyph - 'A'    W(17), H(45), UV(0.99, 0.62)
Glyph - 23458    W(29), H(26), UV(0.38, 0.98)
"""


def test_atlas_parses_both_quoted_and_numeric_forms():
    cov = {a if a else chr(int(b)) for a, b in GLYPH.findall(ATLAS)}
    assert cov == {'\t', 'A', chr(23458)}          # 23458 = 客


def test_markup_strips_only_the_seven_colour_tags():
    """顏色標籤不顯示，不算缺字；但通用的 `<[^<>]+>` 會把比較式整段吃掉、藏住裡面的缺字。"""
    assert MARKUP.sub('', '<ORANGE>老闆<GREEN>：你好') == '老闆：你好'
    assert MARKUP.sub('', '差<3 且 x>5') == '差<3 且 x>5'
    assert MARKUP.sub('', '<迪加>任務學家') == '<迪加>任務學家'


def _scn(msgs=(), triggers=()):
    return NS(message_manager=NS(**{k: v for k, v in msgs}),
              player_manager=NS(players=[NS(player_id=1, name='玩家壹')]),
              trigger_manager=NS(triggers=list(triggers)))


def test_suspect_tags_flags_non_colour_angle_brackets():
    """DE 把 <…> 當標記解析，不認識的可能整段吃掉＝玩家看到憑空少一段。"""
    t = NS(trigger_id=9, name='6大師守候', short_description='', description='',
           effects=[NS(message='<迪加>任務學家'), NS(message='<ORANGE>正常對白')])
    sus = suspect_tags(_scn(triggers=[t]))
    assert list(sus) == ['<迪加>'] and sus['<迪加>'][0][0] == 'T9「6大師守候」E#0'


def test_visible_texts_collects_panels_players_objectives_and_effects():
    t = NS(trigger_id=7, name='1棧', short_description='去客棧', description='',
           effects=[NS(message='老闆：你好'), NS(message=None)])
    got = dict(visible_texts(_scn([('instructions', '任務欄'), ('hints', '')], [t])))
    assert got['劇情文字.instructions'] == '任務欄'
    assert '劇情文字.hints' not in got                      # 空字串不收
    assert got['玩家名.P1'] == '玩家壹'
    assert got['T7「1棧」目標'] == '去客棧'
    assert 'T7「1棧」說明' not in got
    assert got['T7「1棧」E#0'] == '老闆：你好'
    assert 'T7「1棧」E#1' not in got                        # message=None 不收


def test_missing_reports_context_and_ignores_covered():
    t = NS(trigger_id=7, name='1棧', short_description='', description='',
           effects=[NS(message='<ORANGE>本客棧不提供')])
    miss = missing(_scn(triggers=[t]), cov=set('本不提供客玩家壹'))
    assert set(miss) == {'棧'}
    src, ctx = miss['棧'][0]
    assert src == 'T7「1棧」E#0' and ctx == '本客棧不提供'   # 前後文已剝掉標記


def test_word_rules_run_before_char_rules():
    """秘訣→秘技（詞級）不該被字級「訣→技」搶先變成「秘技」以外的東西；
    口訣→口令 才是字級換不好的實例（口技語意全錯）。"""
    assert apply_all('人秘訣原因') == '人秘技原因'
    assert apply_all('擁有飛魂者的口訣') == '擁有飛魂者的口令'
    assert '技' not in apply_all('的口訣')


def test_char_rules_cover_the_readability_cases():
    assert apply_all('本客棧以扣除您的技能點數５') == '本客店以扣除您的技能點數5'
    assert apply_all('＜金庸＞裡') == '《金庸》裡'          # 半形 <> 會被 DE 當標籤，必須用《》
    assert apply_all('道5　召妖　【破軍】') == '道5　召妖　「破軍」'
    assert apply_all('略知ㄧ二') == '略知一二'             # 注音 ㄧ 誤用
    assert apply_all('Lv28磹斧兵=武僧') == 'Lv28擲斧兵=武僧'
    assert apply_all('看我金劍出竅！！') == '看我金劍出鞘！！'
    assert apply_all('減少ｈｐ8萬') == '減少hp8萬'


def test_pua_leftover_handled_per_context():
    """U+F6F3 是 Big5 造字區殘留，同一碼位在兩處角色不同，只能分別處理。"""
    assert apply_all('９２１新增兩項新任務哈囉德哈') == '921新增兩項新任務：哈囉德哈'
    assert apply_all('周賓殺１4000') == '周賓殺1　4000'
    assert '' not in apply_all('新任務') + apply_all('殺１')


def test_rules_are_idempotent():
    """換字步驟重跑不得二次變形（例：換出來的字又被別條規則吃掉）。"""
    for src in ('本客棧的老闆賣針灸給蘇櫻', '【破軍】＜金庸＞ㄧ０', '老衲的如意金箍棒', '峨嵋弟子(男)'):
        once = apply_all(src)
        assert apply_all(once) == once


def test_pipeline_converges_for_every_rule():
    """每條規則的產出跑完整條管線後，不得再含任何字級規則的來源字（否則會反覆變形）。
    「替代字自己是不是缺字」由 gen_glyph_fixes.validate() 對真字圖集驗。"""
    sources = {c for c, *_ in CHAR}
    for old, new, *_ in list(WORD) + [(o, n) for o, n, _, _ in CHAR]:
        assert not (set(apply_all(new)) & sources), f'{old}→{new} 套完管線仍含缺字'


def test_find_fonts_dir_takes_first_candidate_with_combined_txt(tmp_path, monkeypatch):
    good = tmp_path / 'good'; good.mkdir(); (good / 'combined.txt').write_text('', encoding='utf-8')
    empty = tmp_path / 'empty'; empty.mkdir()          # 目錄在、但沒 combined.txt → 跳過
    monkeypatch.delenv('AOE2_FONTS_DIR', raising=False)
    monkeypatch.setattr(font_check, 'FONTS_DIRS', (r'D:\沒有這台碟', str(empty), str(good)))
    assert font_check.find_fonts_dir() == good
    monkeypatch.setenv('AOE2_FONTS_DIR', str(good))    # 環境變數蓋過候選清單
    monkeypatch.setattr(font_check, 'FONTS_DIRS', ())
    assert font_check.find_fonts_dir() == good


def test_load_coverage_falls_back_to_snapshot_without_game_install(monkeypatch):
    """沒裝遊戲的機器也要能跑 s90 缺字閘門——退回版控快照，不是炸掉。"""
    monkeypatch.delenv('AOE2_FONTS_DIR', raising=False)
    monkeypatch.setattr(font_check, 'FONTS_DIRS', ())
    cov = font_check.load_coverage()
    assert len(cov) == 7697 and sum(1 for c in cov if 0x4E00 <= ord(c) <= 0x9FFF) == 5510
    with pytest.raises(FileNotFoundError):
        font_check.load_coverage(allow_snapshot=False)

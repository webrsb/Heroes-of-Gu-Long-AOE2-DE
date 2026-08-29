import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.change import Change, TSV_HEADER, to_tsv_row

def test_tsv_row_basic():
    c = Change(step='s30', kind='effect', target='T210 效果0', field='quantity',
               old='16646156', new='+65036(class0)', reason='§3.3e 還原公式')
    assert to_tsv_row(c) == 's30\teffect\tT210 效果0\tquantity\t16646156\t+65036(class0)\t§3.3e 還原公式'

def test_tsv_header_matches_field_order():
    assert TSV_HEADER == 'step\tkind\ttarget\tfield\told\tnew\treason'

def test_tsv_escapes_tabs_and_newlines():
    c = Change('s10', 'effect', 'T1', 'message', 'a\tb', 'c\nd', 'r')
    row = to_tsv_row(c)
    assert '\t' in row and row.count('\t') == 6  # 只有 6 個分隔 tab
    assert '\n' not in row

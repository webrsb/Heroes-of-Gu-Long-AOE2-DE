import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pytest
from analysis.inventory import render_report
from analysis.dependency import GroupReport

def test_render_contains_sections_and_selection_table():
    gr = GroupReport('踢人系統', {1, 2}); gr.refs_same = 3; gr.classification = 'auto'
    gr.reasons = ['物件全數可解析、啟動邊全數可配對']
    out = render_report(
        group_reports=[gr],
        diff_rows=[('武士2', '效果0.quantity', '100', '999')],
        fuzzy_rows=[('武士2', '武士4')],
        orphans={1358: 5},
        stats={'a_total': 5232, 'b_total': 5599, 'unmatched_b': 317, 'unmatched_b_names': []})
    assert '踢人系統' in out and '圈選' in out
    assert '同名不同內容' in out and '武士2' in out
    assert '模糊配對' in out
    assert '孤兒物件' in out

@pytest.mark.slow
def test_write_report_end_to_end():
    from analysis.inventory import write_report
    assert write_report() == 0
    from pathlib import Path
    rp = Path(__file__).resolve().parents[1] / 'reports/盤點報告.md'
    body = rp.read_text(encoding='utf-8')
    assert '圈選' in body and '同名不同內容' in body

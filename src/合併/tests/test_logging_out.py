import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pathlib import Path
from core.change import Change
from core.logging_out import write_step_logs

def _c():
    return Change('s30', 'effect', 'T210 效果0', 'quantity', '16646156', '+65036', '§3.3e')

def test_writes_tsv_and_md(tmp_path):
    tsv, md = write_step_logs('s30', '攻擊力修復', '對全檔跑還原公式', [_c()], tmp_path)
    assert tsv.name == '30_攻擊力修復.tsv' and md.name == '30_攻擊力修復.md'
    lines = tsv.read_text(encoding='utf-8').splitlines()
    assert lines[0].startswith('step\t') and len(lines) == 2
    body = md.read_text(encoding='utf-8')
    assert '攻擊力修復' in body and 'effect: 1' in body and '§3.3e' in body

def test_empty_changes_still_writes(tmp_path):
    tsv, md = write_step_logs('s60', '雜項替換', '…', [], tmp_path)
    assert tsv.read_text(encoding='utf-8').strip().startswith('step\t')
    assert '本輪無異動' in md.read_text(encoding='utf-8')

def test_overwrites_same_filename(tmp_path):
    write_step_logs('s30', '攻擊力修復', 'x', [_c(), _c()], tmp_path)
    tsv, _ = write_step_logs('s30', '攻擊力修復', 'x', [_c()], tmp_path)
    assert len(tsv.read_text(encoding='utf-8').splitlines()) == 2

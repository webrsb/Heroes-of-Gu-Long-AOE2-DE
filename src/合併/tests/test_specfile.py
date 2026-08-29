import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pytest
from core.specfile import load_spec, SpecError

GOOD = '''
groups:
  - name: 幫眾系統
    action: auto
    trigger_ids: [4102, 4103]
overrides:
  - target: "T210 效果0"
    field: quantity
    value: "300"
    reason: 以劍譜5為準（使用者 2026-08-29 裁決）
params:
  boss_hp:
    targets: []
'''

def test_load_good_spec(tmp_path):
    p = tmp_path / 'merge_spec.yaml'
    p.write_text(GOOD, encoding='utf-8')
    spec = load_spec(p)
    assert spec.groups[0].name == '幫眾系統'
    assert spec.groups[0].action == 'auto'
    assert spec.groups[0].trigger_ids == [4102, 4103]
    assert spec.overrides[0].field == 'quantity'
    assert spec.params['boss_hp'] == {'targets': []}

def test_bad_action_raises_specerror(tmp_path):
    p = tmp_path / 'merge_spec.yaml'
    p.write_text(GOOD.replace('action: auto', 'action: 全搬'), encoding='utf-8')
    with pytest.raises(SpecError) as e:
        load_spec(p)
    assert '幫眾系統' in str(e.value) and '全搬' in str(e.value)

def test_missing_sections_default_empty(tmp_path):
    p = tmp_path / 'merge_spec.yaml'
    p.write_text('params: {}\n', encoding='utf-8')
    spec = load_spec(p)
    assert spec.groups == [] and spec.overrides == []

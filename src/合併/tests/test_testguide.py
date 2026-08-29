import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.change import Change
from core.testguide import StepResult, render_guide

def test_guide_contains_step_sections():
    r = [StepResult('s40', '雙0血', [Change('s40','unit','ref31245 聚魂塔','hp','—','雙0血','§5.7')],
                    '怎麼測：派兵攻擊聚魂塔\n預期：血量實際下降'),
         StepResult('s60', '雜項替換', [], None)]
    out = render_guide(r)
    assert '### 驗 s40 雙0血' in out
    assert '派兵攻擊聚魂塔' in out
    assert 's60' in out and '本輪無異動，免測' in out

def test_zero_change_step_marked_skip_even_with_guide_text():
    r = [StepResult('s10', '自動搬運', [], '怎麼測：xxx')]
    assert '本輪無異動，免測' in render_guide(r)

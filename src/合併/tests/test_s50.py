import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from steps.s50_healthbar import bar_text, thresholds

def test_bar_text_style3():
    assert bar_text('亡魂之堡', 40) == '亡魂之堡 [####______] 40%'
    assert bar_text('聚魂塔', 80) == '聚魂塔 [########__] 80%'
    assert bar_text('X', 5) == 'X [__________] 5%'

def test_bar_text_ascii_cjk_only():
    for pct in range(0, 100):
        s = bar_text('聚魂塔', pct)
        assert all(ord(ch) < 128 or '一' <= ch <= '鿿' for ch in s), s

def test_thresholds_99_down_to_1():
    th = thresholds(1000.0)
    assert th[0] == (99, 990.0) and th[-1] == (1, 10.0) and len(th) == 99

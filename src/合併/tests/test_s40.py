import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pytest
from steps.s40_boss_hp import locate_target
from steps.base import BuildError

IDX = {100: (1, 82, 3.5, 5.5), 101: (1, 82, 9.0, 9.0), 102: (2, 72, 3.5, 5.5)}

def test_locate_unique():
    assert locate_target(IDX, unit_const=82, tile=(3, 5), label='堡') == 100

def test_locate_none_raises():
    with pytest.raises(BuildError) as e:
        locate_target(IDX, unit_const=82, tile=(7, 7), label='堡')
    assert '堡' in str(e.value)

def test_locate_ambiguous_raises():
    idx = dict(IDX); idx[103] = (1, 82, 3.9, 5.1)
    with pytest.raises(BuildError):
        locate_target(idx, unit_const=82, tile=(3, 5), label='堡')

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pytest
from types import SimpleNamespace as NS
from steps.s60_misc import apply_replacement
from steps.base import BuildError

def _units(*consts):
    return [NS(reference_id=i, unit_const=c, x=1.0, y=2.0) for i, c in enumerate(consts)]

def test_replaces_matching_const():
    us = _units(436, 100)
    changes = apply_replacement(us, {'label': '船', 'find': {'unit_const': 436},
                                     'to_const': 2353, 'expect_count': 1, 'reason': 'r'})
    assert us[0].unit_const == 2353 and us[1].unit_const == 100
    assert len(changes) == 1 and changes[0].field == 'unit_const'

def test_count_mismatch_raises():
    with pytest.raises(BuildError):
        apply_replacement(_units(436, 436), {'label': '船', 'find': {'unit_const': 436},
                                             'to_const': 2353, 'expect_count': 1, 'reason': 'r'})

def test_expect_zero_is_noop():
    us = _units(100)
    assert apply_replacement(us, {'label': '船', 'find': {'unit_const': 436},
                                  'to_const': 2353, 'expect_count': 0, 'reason': 'r'}) == []

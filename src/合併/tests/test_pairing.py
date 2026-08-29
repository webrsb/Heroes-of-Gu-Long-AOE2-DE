import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from types import SimpleNamespace as NS
from analysis.pairing import pair_triggers

def _t(tid, name, etypes, q=0):
    effs = [NS(effect_type=et, quantity=q, tribute_list=None, object_list_unit_id=None,
               source_player=None, target_player=None, technology=None, operation=None,
               object_attributes=None, area_x1=None, area_y1=None, area_x2=None,
               area_y2=None, location_x=None, location_y=None,
               trigger_id=-1, selected_object_ids=[], message='') for et in etypes]
    return NS(trigger_id=tid, name=name, conditions=[], effects=effs)

def test_name_match_first():
    a = [_t(0, '幫眾', [1])]; b = [_t(0, '幫眾', [2])]  # 內容不同也照名配
    pt = pair_triggers(a, b)
    assert pt.a2b == {0: 0} and pt.method[0] == 'name'

def test_fingerprint_match_for_renamed():
    a = [_t(0, '8城名', [5], q=7)]; b = [_t(0, '8城', [5], q=7)]
    pt = pair_triggers(a, b)
    assert pt.a2b == {0: 0} and pt.method[0] == 'fp'

def test_fuzzy_by_type_signature():
    a = [_t(0, '武士2', [5], q=1)]; b = [_t(0, '武士4', [5], q=999)]
    pt = pair_triggers(a, b)
    assert pt.a2b == {0: 0} and pt.method[0] == 'fuzzy'

def test_duplicate_names_not_name_matched():
    a = [_t(0, '少林寺', [1], q=1), _t(1, '少林寺', [2], q=2)]
    b = [_t(0, '少林寺', [1], q=1)]
    pt = pair_triggers(a, b)
    assert pt.method.get(0) == 'fp'      # 靠指紋配上
    assert 1 in pt.unmatched_a

def test_unmatched_collected():
    a = [_t(0, '獨有A', [9], q=1)]; b = [_t(0, '獨有B', [8], q=1)]
    pt = pair_triggers(a, b)
    assert pt.unmatched_a == [0] and pt.unmatched_b == [0]

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from types import SimpleNamespace as NS
from analysis.grouping import activation_edges, group_ids, group_label
from AoE2ScenarioParser.datasets.effects import EffectId

def _t(tid, name, act_targets=()):
    effs = [NS(effect_type=int(EffectId.ACTIVATE_TRIGGER), trigger_id=x) for x in act_targets]
    return NS(trigger_id=tid, name=name, conditions=[], effects=effs)

def test_edges_extracted():
    ts = [_t(0, 'a', [1]), _t(1, 'b'), _t(2, 'c', [0])]
    assert set(activation_edges(ts)) == {(0, 1), (2, 0)}

def test_grouping_within_candidates_only():
    edges = [(0, 1), (1, 5)]          # 5 不在候選集
    gs = group_ids({0, 1, 2}, edges)
    assert sorted(map(sorted, gs)) == [[0, 1], [2]]

def test_group_label_common_prefix():
    ts = {0: _t(0, '踢2p'), 1: _t(1, '踢3p')}
    assert group_label(ts, {0, 1}) == '踢'

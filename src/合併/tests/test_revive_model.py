# -*- coding: utf-8 -*-
"""T2: ReviveSpec 載入與驗證。"""
import pytest
from core.revive_model import load_revive
from steps.base import BuildError

BASE = dict(lives=3, respawn=[77.5, 103.5],
            displays={1: [78.5, 108.5], 2: [80.5, 108.5], 3: [82.5, 108.5],
                      4: [83.5, 109.5], 5: [83.5, 111.5], 6: [83.5, 113.5]},
            hero_refs={1: 0, 2: 1, 3: 2, 4: 502, 5: 7, 6: 45117},
            retired=[1805, 1806, 1807, 1808, 1809, 1810,
                     3821, 3822, 3823, 3824, 3825, 3826])


def test_load_ok():
    r = load_revive(BASE)
    assert r.lives == 3
    assert r.respawn == (77.5, 103.5)
    assert r.displays[5] == (83.5, 111.5)
    assert r.hero_refs[6] == 45117
    assert 3821 in r.retired


def test_missing_display_raises():
    bad = dict(BASE, displays={k: v for k, v in BASE['displays'].items() if k != 5})
    with pytest.raises(BuildError):
        load_revive(bad)


def test_lives_too_small_raises():
    with pytest.raises(BuildError):
        load_revive(dict(BASE, lives=1))


def test_missing_key_raises():
    bad = {k: v for k, v in BASE.items() if k != 'respawn'}
    with pytest.raises(BuildError):
        load_revive(bad)


def test_hero_refs_must_cover_six():
    bad = dict(BASE, hero_refs={1: 0})
    with pytest.raises(BuildError):
        load_revive(bad)

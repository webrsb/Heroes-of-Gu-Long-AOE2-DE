# -*- coding: utf-8 -*-
"""共用假件工廠（plan v2 檔案結構）：以 SimpleNamespace 模擬 trigger/effect/condition，
欄位名對齊 AoE2ScenarioParser 實名。用法：測試函式收 fixture `f`。"""
import pytest
from types import SimpleNamespace as NS

_EFF_BASE = dict(source_player=-1, target_player=-1, object_list_unit_id=-1,
                 location_object_reference=-1, trigger_id=-1, quantity=None,
                 area_x1=-1, area_y1=-1, area_x2=-1, area_y2=-1)
_COND_BASE = dict(unit_object=-1, next_object=-1, source_player=-1, object_list=-1,
                  timer=-1, quantity=-1,
                  area_x1=-1, area_y1=-1, area_x2=-1, area_y2=-1)


class Factory:
    def __init__(self):
        self._next = 0

    # ---- 觸發/管理器 ----
    def trig(self, conds=(), effects=(), enabled=True, looping=False, name=''):
        t = NS(trigger_id=self._next, name=name, enabled=1 if enabled else 0,
               looping=1 if looping else 0,
               conditions=list(conds), effects=list(effects))
        self._next += 1
        return t

    def tm(self, trigs):
        import copy
        trigs = list(trigs)
        tm = NS(triggers=trigs,
                triggers_by_id={t.trigger_id: t for t in trigs})

        def copy_trigger(tid, append_after_source=True, add_suffix=True):
            assert append_after_source is False and add_suffix is False,                 'copy_trigger 必須用 append_after_source=False, add_suffix=False（鐵律）'
            src = tm.triggers_by_id[tid]
            v = copy.deepcopy(src)
            v.trigger_id = max(tm.triggers_by_id) + 1
            tm.triggers.append(v)
            tm.triggers_by_id[v.trigger_id] = v
            return v

        tm.copy_trigger = copy_trigger
        return tm

    # ---- 效果 ----
    def _eff(self, etype, **kw):
        d = dict(_EFF_BASE, effect_type=etype, selected_object_ids=[])
        d.update(kw)
        return NS(**d)

    def eff_rename(self, sel, sp=-1, message=''):
        return self._eff(26, selected_object_ids=list(sel), source_player=sp, message=message)

    def eff_damage(self, sel, sp=-1, quantity=0):
        return self._eff(24, selected_object_ids=list(sel), source_player=sp, quantity=quantity)

    def eff_hp(self, sel, sp=-1, quantity=0):
        return self._eff(27, selected_object_ids=list(sel), source_player=sp, quantity=quantity)

    def eff_attack(self, sel, sp=-1):
        return self._eff(28, selected_object_ids=list(sel), source_player=sp)

    def eff_stop(self, sel, sp=-1):
        return self._eff(29, selected_object_ids=list(sel), source_player=sp)

    def eff_task(self, sel=(), sp=-1, locref=-1, x=-1, y=-1):
        return self._eff(12, selected_object_ids=list(sel), source_player=sp,
                         location_object_reference=locref, location_x=x, location_y=y)

    def eff_remove(self, sel=(), sp=-1, olu=-1, area=None):
        kw = dict(selected_object_ids=list(sel), source_player=sp, object_list_unit_id=olu)
        if area:
            kw.update(area_x1=area[0], area_y1=area[1], area_x2=area[2], area_y2=area[3])
        return self._eff(15, **kw)

    def eff_chat(self, sp=-1, message=''):
        return self._eff(3, source_player=sp, message=message)

    def eff_tribute(self, sp=-1, tp=-1, quantity=0):
        return self._eff(5, source_player=sp, target_player=tp, quantity=quantity)

    def eff_ownership(self, sel, sp=-1, tp=-1):
        return self._eff(18, selected_object_ids=list(sel), source_player=sp, target_player=tp)

    def eff_create(self, sp=-1, olu=-1, x=-1, y=-1):
        return self._eff(11, source_player=sp, object_list_unit_id=olu, location_x=x, location_y=y)

    def eff_activate(self, tid):
        return self._eff(8, trigger_id=tid)

    def eff_deactivate(self, tid):
        return self._eff(9, trigger_id=tid)

    # ---- 條件 ----
    def _cond(self, ctype, **kw):
        d = dict(_COND_BASE, condition_type=ctype)
        d.update(kw)
        return NS(**d)

    def cond_destroy(self, ref):
        return self._cond(6, unit_object=ref)

    def cond_bring_area(self, ref, area=(-1, -1, -1, -1)):
        return self._cond(1, unit_object=ref,
                          area_x1=area[0], area_y1=area[1], area_x2=area[2], area_y2=area[3])

    def cond_bring_obj(self, ref, next_ref):
        return self._cond(2, unit_object=ref, next_object=next_ref)

    def cond_area(self, sp=-1, object_list=-1, area=(-1, -1, -1, -1), qty=1):
        return self._cond(5, source_player=sp, object_list=object_list, quantity=qty,
                          area_x1=area[0], area_y1=area[1], area_x2=area[2], area_y2=area[3])

    def cond_accumulate(self, sp=-1, qty=0):
        return self._cond(8, source_player=sp, quantity=qty)

    def cond_timer(self, timer):
        return self._cond(10, timer=timer)


@pytest.fixture
def f():
    return Factory()

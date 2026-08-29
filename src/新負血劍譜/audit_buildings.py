# -*- coding: utf-8 -*-
"""全面盤點：哪些建築物會被灌血 / 改上限（含區域指定的效果）"""
import sys, collections
sys.stdout.reconfigure(encoding='utf-8')
from AoE2ScenarioParser.scenarios.aoe2_de_scenario import AoE2DEScenario
from AoE2ScenarioParser.datasets.buildings import BuildingInfo
from AoE2ScenarioParser.datasets.units import UnitInfo
from AoE2ScenarioParser.datasets.heroes import HeroInfo
from AoE2ScenarioParser.datasets.other import OtherInfo

SRC = r'F:\aoe2de\src\- 古龍 ９２１ 新負血劍譜５ -utf8.aoe2scenario'
CHANGE_HP, DAMAGE = 27, 24
BLD = {b.ID for b in BuildingInfo}

def nm(i):
    for ds in (BuildingInfo, UnitInfo, HeroInfo, OtherInfo):
        try: return ds.from_id(i).name
        except Exception: pass
    return '??%d' % i

s = AoE2DEScenario.from_file(SRC)
objs = []                       # (ref, player, const, x, y)
for p in range(9):
    for u in s.unit_manager.units[p]:
        objs.append((u.reference_id, p, u.unit_const, u.x, u.y))
by_ref = {o[0]: o for o in objs}

def targets(e):
    """回傳這個效果實際命中的物件 ref 清單"""
    if e.selected_object_ids:
        return [r for r in e.selected_object_ids if r in by_ref]
    sp = e.source_player
    ol = e.object_list_unit_id
    x1, y1, x2, y2 = e.area_x1, e.area_y1, e.area_x2, e.area_y2
    has_area = x1 != -1 and y1 != -1 and x2 != -1 and y2 != -1
    out = []
    for ref, p, const, x, y in objs:
        if sp != -1 and p != sp: continue
        if ol != -1 and const != ol: continue
        if has_area and not (x1 <= int(x) <= x2 and y1 <= int(y) <= y2): continue
        out.append(ref)
    return out

heal = collections.defaultdict(int)     # 負傷害合計（灌血）
hurt = collections.defaultdict(int)
maxd = collections.defaultdict(int)     # max HP 變動合計
src  = collections.defaultdict(list)
for t in s.trigger_manager.triggers:
    for e in t.effects:
        if e.effect_type not in (CHANGE_HP, DAMAGE): continue
        tg = targets(e)
        if len(tg) > 400: continue      # 全圖無過濾效果另案處理
        for r in tg:
            if e.effect_type == CHANGE_HP:
                maxd[r] += e.quantity
                src[r].append(('maxHP', t.trigger_id, t.name, e.quantity))
            elif e.quantity < 0:
                heal[r] += e.quantity
                src[r].append(('heal', t.trigger_id, t.name, e.quantity))
            else:
                hurt[r] += e.quantity

refs = set(heal) | set(maxd)
rows = []
for r in refs:
    ref, p, const, x, y = by_ref[r]
    rows.append((const in BLD, heal.get(r, 0), r, p, const, nm(const), x, y,
                 maxd.get(r, 0), hurt.get(r, 0)))
rows.sort(key=lambda t: (not t[0], t[1]))

print('=== 建築物（會被 HP 效果影響的） ===')
print('%-8s %-3s %-6s %-22s %-14s %-12s %-12s %s' %
      ('ref','P','const','名稱','座標','ΔmaxHP','灌血合計','正傷害'))
nb = 0
for isb, h, r, p, const, name, x, y, md, hu in rows:
    if not isb: continue
    nb += 1
    print('%-8s %-3s %-6s %-22s %-14s %-12s %-12s %s' %
          (r, p, const, name[:20], '(%g,%g)' % (x, y), md, h, hu))
print('建築物合計 %d 個' % nb)

print()
print('=== 灌血量最大的建築物：效果明細 ===')
for isb, h, r, p, const, name, x, y, md, hu in rows:
    if not isb or h > -10000: continue
    print('--- ref=%s P%d %s (%g,%g)  ΔmaxHP=%s 灌血=%s' % (r, p, name, x, y, md, h))
    for kind, tid, tname, q in src[r]:
        print('      %-6s [%d] %-14s qty=%s' % (kind, tid, tname[:14], q))

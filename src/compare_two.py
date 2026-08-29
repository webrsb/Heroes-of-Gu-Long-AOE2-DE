# -*- coding: utf-8 -*-
"""把整套 DE 遷移檢查清單同時跑在兩份劇本上"""
import sys, collections
sys.stdout.reconfigure(encoding='utf-8')
from AoE2ScenarioParser.scenarios.aoe2_de_scenario import AoE2DEScenario
from AoE2ScenarioParser.datasets.buildings import BuildingInfo
from AoE2ScenarioParser.datasets.units import UnitInfo
from AoE2ScenarioParser.datasets.heroes import HeroInfo
from AoE2ScenarioParser.datasets.other import OtherInfo

KNOWN = set()
for ds in (BuildingInfo, UnitInfo, HeroInfo, OtherInfo):
    KNOWN |= {x.ID for x in ds}
BLD = {b.ID for b in BuildingInfo}

FILES = [
    ('劍譜5', r'F:\aoe2de\src\- 古龍 ９２１ 新負血劍譜５ -utf8.aoe2scenario'),
    ('無法無天11', r'C:\Users\Ricky\Games\Age of Empires 2 DE'
                r'\76561198023399153\resources\_common\scenario\古龍(無法無天_11).aoe2scenario'),
]

def audit(path):
    s = AoE2DEScenario.from_file(path)
    tm = s.trigger_manager
    objs = []
    for p in range(9):
        for u in s.unit_manager.units[p]:
            objs.append((u.reference_id, p, u.unit_const, u.x, u.y))
    by_ref = {o[0]: o for o in objs}
    r = collections.OrderedDict()
    r['觸發器'] = len(tm.triggers)
    r['效果'] = sum(len(t.effects) for t in tm.triggers)
    r['條件'] = sum(len(t.conditions) for t in tm.triggers)
    r['物件'] = len(objs)

    atk_bad = atk_all = 0
    trib_neg = trib_m1 = 0
    task_noloc = task_noloc_loop = 0
    kr = vis = notvis = 0
    hp_over = 0
    dmg_m1 = 0
    for t in tm.triggers:
        for c in t.conditions:
            if c.condition_type == 8 and c.attribute == 44: kr += 1
            if c.condition_type == 15: vis += 1
            if c.condition_type == 16: notvis += 1
        for e in t.effects:
            if e.effect_type == 28:
                atk_all += 1
                if e.quantity is not None and e.quantity >= 65536: atk_bad += 1
            if e.effect_type == 5:
                if e.quantity is not None and e.quantity < 0:
                    trib_neg += 1
                    if e.quantity == -1: trib_m1 += 1
            if e.effect_type == 12 and e.location_x == -1 and e.location_y == -1:
                task_noloc += 1
                if t.looping: task_noloc_loop += 1
            if e.effect_type == 27 and e.quantity is not None and abs(e.quantity) > 32767:
                hp_over += 1
            if e.effect_type == 24 and e.quantity == -1: dmg_m1 += 1
    r['攻擊效果(28)'] = atk_all
    r['攻擊被切分(>=65536)'] = atk_bad
    r['負進貢'] = trib_neg
    r['負進貢 = -1（失效）'] = trib_m1
    r['Damage = -1'] = dmg_m1
    r['無座標 TaskObject'] = task_noloc
    r['　其中循環'] = task_noloc_loop
    r['Kill Ratio'] = kr
    r['Object Visible(15)'] = vis
    r['Object NotVisible(16)'] = notvis
    r['Change HP 絕對值 > 32767'] = hp_over

    # 建築物灌血
    def targets(e):
        if e.selected_object_ids:
            return [x for x in e.selected_object_ids if x in by_ref]
        sp, ol = e.source_player, e.object_list_unit_id
        x1, y1, x2, y2 = e.area_x1, e.area_y1, e.area_x2, e.area_y2
        ha = x1 != -1 and y1 != -1 and x2 != -1 and y2 != -1
        out = []
        for ref, p, const, x, y in objs:
            if sp != -1 and p != sp: continue
            if ol != -1 and const != ol: continue
            if ha and not (x1 <= int(x) <= x2 and y1 <= int(y) <= y2): continue
            out.append(ref)
        return out
    heal = collections.defaultdict(int)
    for t in tm.triggers:
        for e in t.effects:
            if e.effect_type != 24 or e.quantity is None or e.quantity >= 0: continue
            tg = targets(e)
            if len(tg) > 400: continue
            for x in tg: heal[x] += e.quantity
    bl = [x for x in heal if by_ref[x][2] in BLD]
    unk = sorted({by_ref[x][2] for x in heal if by_ref[x][2] not in KNOWN})
    r['被灌血的【已知】建築'] = len(bl)
    r['被灌血的未知 const'] = str(unk)
    # 未知 ID 總覽
    used = {o[2] for o in objs}
    for t in tm.triggers:
        for e in t.effects:
            if e.object_list_unit_id not in (None, -1): used.add(e.object_list_unit_id)
    r['用到的未知物件 ID 數'] = len(used - KNOWN)
    return r, sorted(used - KNOWN)

res = {}
unks = {}
for label, path in FILES:
    res[label], unks[label] = audit(path)

keys = list(res[FILES[0][0]].keys())
w = max(len(k) for k in keys) + 2
print('%-*s %-22s %s' % (w, '項目', FILES[0][0], FILES[1][0]))
print('-' * (w + 46))
for k in keys:
    a, b = res[FILES[0][0]][k], res[FILES[1][0]][k]
    mark = '' if a == b else '   <<<'
    print('%-*s %-22s %s%s' % (w, k, a, b, mark))
print()
A, B = unks[FILES[0][0]], unks[FILES[1][0]]
print('未知 ID：劍譜5 有 %d 個、無法無天11 有 %d 個' % (len(A), len(B)))
print('  只在劍譜5   :', sorted(set(A) - set(B)))
print('  只在無法無天11:', sorted(set(B) - set(A)))
print('  兩者共有     :', len(set(A) & set(B)), '個')

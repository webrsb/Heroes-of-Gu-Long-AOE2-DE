# -*- coding: utf-8 -*-
"""s38 選職業前置（spec §四/§五）：本體改造為展示英雄、備身與容器生成、職業名萃取、
初始化觸發（改名/凍結/備身轉Gaia/展示無敵迴圈）。
產出 ctx.notes['revive']＝{spec, life_refs, containers, class_names}；選角/復活鏈由 s39 接手。"""
import re
from core.change import Change
from .base import trig_by_id, Step, BuildError

INVIS = 1291
_NAME_RE = re.compile(r'<[^>]*>')


def extract_class_names(tm, rspec) -> dict:
    """自 X死 兩世代觸發萃取職業名：{cid: (第一世代名, 轉生世代名)}。
    T3821–3826＝第一世代（刀客…）、T1805–1810＝轉生世代（刀俠…）。"""
    def name_of(tid):
        t = trig_by_id(tm, tid)
        if t is None:
            raise BuildError(f'缺裁決：職業名萃取失敗——T{tid} 不存在')
        for e in t.effects:
            msg = getattr(e, 'message', None) or ''
            clean = _NAME_RE.sub('', msg)
            if '已死亡' in clean:
                return clean.split('已死亡')[0].strip()
        raise BuildError(f'缺裁決：T{tid} 找不到「…已死亡」訊息，無法萃取職業名')

    return {cid: (name_of(3820 + cid), name_of(1804 + cid)) for cid in range(1, 7)}


def _move_owner(um, unit, new_player):
    unit.player = new_player          # 真 parser：setter 自帶列表搬移；假件：純屬性
    if unit not in um.units[new_player]:
        for p in range(9):
            if p != new_player and unit in um.units[p]:
                um.units[p].remove(unit)
        um.units[new_player].append(unit)


def setup_bodies(um, tm, rspec, extract=extract_class_names, mirrors=None, survival=None):
    """本體→P8＋展示位；備身×(lives−1)/職業（P8 建檔、駐各自 1291 容器疊重生點）；
    鏡像預設 P8＋每位玩家保命隱形物件（阿提拉手法）；初始化觸發。回傳 notes dict。"""
    changes = []
    by_ref = {u.reference_id: u for p in range(9) for u in um.units[p]}
    if by_ref[rspec.hero_refs[5]].unit_const == 94:
        raise BuildError('缺裁決：P5 本體仍是 const94——s35 換皮未先執行（步驟順序異常）')

    # 角落鏡像開場預設 P8（選角時才轉讓給入座玩家；2026-08-30 裁決）
    for cid, ref in sorted({int(k): int(v) for k, v in (mirrors or {}).items()}.items()):
        u = by_ref.get(ref)
        if u is None:
            raise BuildError(f'缺裁決：鏡像 ref{ref}（職業{cid}）不存在')
        old_p = u.player
        _move_owner(um, u, 8)
        changes.append(Change('s38', 'unit_field', f'ref{ref}', 'owner',
                              f'P{old_p}', 'P8', f'職業{cid}鏡像預設P8'))
    # 保命隱形物件：玩家無單位時擋征服判負（C1_Attila_1 官方手法，837 不保命）
    if survival:
        sx, sy = survival['cell']
        sc = int(survival['const'])
        for slot in range(1, 7):
            u = um.add_unit(player=slot, unit_const=sc, x=float(sx), y=float(sy))
            changes.append(Change('s38', 'unit_add', f'ref{u.reference_id}', 'unit',
                                  '', f'const{sc}', f'位{slot}保命隱形物件'))

    class_names = extract(tm, rspec)
    life_refs, containers = {}, {}
    rx, ry = rspec.respawn
    for cid in range(1, 7):
        hero = by_ref[rspec.hero_refs[cid]]
        dx, dy = rspec.displays[cid]
        old = (hero.x, hero.y, hero.player)
        hero.x, hero.y = dx, dy
        _move_owner(um, hero, 8)
        changes.append(Change('s38', 'unit_field', f'ref{hero.reference_id}', 'owner/pos',
                              str(old), f'P8@({dx},{dy})', f'職業{cid}展示英雄'))
        life_refs[cid] = [hero.reference_id]
        containers[cid] = []
        for L in range(2, rspec.lives + 1):
            box = um.add_unit(player=0, unit_const=INVIS, x=rx, y=ry)
            spare = um.add_unit(player=8, unit_const=hero.unit_const, x=rx, y=ry,
                                garrisoned_in_id=box.reference_id)
            containers[cid].append(box.reference_id)
            life_refs[cid].append(spare.reference_id)
            changes.append(Change('s38', 'unit_add',
                                  f'ref{spare.reference_id}駐ref{box.reference_id}', 'unit',
                                  '', f'const{hero.unit_const}', f'職業{cid}第{L}命備身+容器'))

    # 廣場視野：每位數顆地圖顯示器（使用者 2026-08-30 存檔示範：const837 @廣場）。
    # 837 視野半徑約 4 格，六英雄展示帶 (78.5–83.5, 108.5–113.5) 需三顆才蓋滿（上角槍/棍客 2026-08-30 實測在黑幕）
    navigators = {}
    nav_cells = getattr(rspec, 'navigator_cells', [(80.5, 110.5), (81.5, 112.5)])
    for slot in range(1, 7):
        refs = []
        for (nx, ny) in nav_cells:
            nav = um.add_unit(player=slot, unit_const=837, x=nx, y=ny)
            refs.append(nav.reference_id)
        navigators[slot] = refs
        changes.append(Change('s38', 'unit_add', f'refs{refs}', 'unit',
                              '', f'const837×{len(nav_cells)}', f'位{slot}廣場視野顯示器'))

    t = tm.add_trigger('選角初始化', enabled=True, looping=False)
    t.new_condition.timer(timer=0)
    for cid in range(1, 7):
        t.new_effect.change_object_caption(selected_object_ids=[rspec.hero_refs[cid]],
                                           message=class_names[cid][0])   # 血條系統手法：浮動字幕
        t.new_effect.freeze_object(source_player=8,
                                   selected_object_ids=[rspec.hero_refs[cid]])
        for ref in life_refs[cid][1:]:
            t.new_effect.change_ownership(source_player=8, target_player=0,
                                          selected_object_ids=[ref])
    t.new_effect.display_instructions(
        message='<GREEN>請點選廣場上的職業英雄進行選角', display_time=600)
    changes.append(Change('s38', 'trigger_add', '選角初始化', 'trigger', '', '新增',
                          'caption職業名/凍結/備身轉Gaia/領航員/選角提示600秒'))

    hero_consts = {cid: by_ref[rspec.hero_refs[cid]].unit_const for cid in range(1, 7)}
    rspec.hero_consts = hero_consts
    return dict(spec=rspec, life_refs=life_refs, containers=containers,
                class_names=class_names, changes=changes, hero_consts=hero_consts,
                init_tid=t.trigger_id, navigators=navigators)


class ChooseStep(Step):
    id = 's38'
    title = '選職業前置'
    intro = '展示英雄/備身/容器/職業名；無 revive 參數時跳過。'

    def apply(self, ctx):
        params = ctx.spec.params.get('revive')
        if not params:
            return []
        from core.revive_model import load_revive
        rspec = load_revive(params)
        out = setup_bodies(ctx.base.unit_manager, ctx.base.trigger_manager, rspec,
                           mirrors=params.get('mirrors'), survival=params.get('survival'))
        ctx.notes['revive'] = out
        return out['changes']

    def test_guide(self, changes):
        return ('選職業前置：六展示英雄站廣場（P8、凍結、職業名 caption、殺不死）；'
                '重生點應乾淨無兵（備身全在隱形容器）。\n'
                '陽性對照：點展示英雄看數值正常。')


STEP = ChooseStep()

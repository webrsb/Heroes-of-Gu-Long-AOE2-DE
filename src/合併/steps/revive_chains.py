# -*- coding: utf-8 -*-
"""T9a：復活鏈建造（spec §五/§七/§七之三 v4）——選角觸發、watch/timer/final、
訊息三態（讀騎馬旗/轉生旗自選）、馬騎監視 per (C,S,L)、啟動器分塊。
v4：永久騎馬旗；監視純 destroy 條件（上馬由 X馬3 顯式停用當前監視）；馬亡旗機制刪除。"""
from types import SimpleNamespace as NS
from core.change import Change

FLAG_CONST = 720          # 角落旗標單位（地圖原生慣用法：NINE_BANDS）
REVEALER = 837


def build_chains(tm, rv):
    """rv 必備鍵：spec(lives/respawn/hero_refs/displays)、life_refs、containers、
    class_names{cid:(客名,俠名)}、invuln_tids、base_hp、enable_lists、
    mount{cid:{mount_ref,flag_cell,rebirth_cell,final_cell}}、classes、slots。
    可選 dl_hooks{(cid,slot):{'watch_activate':[tid],'timer_deactivate':[tid],
    'timer_activate':[tid]}}。"""
    spec = rv['spec']
    lives = spec.lives
    life = rv['life_refs']
    boxes = rv['containers']
    names = rv['class_names']
    mount = rv['mount']
    classes = rv.get('classes', tuple(sorted(life)))
    slots = rv.get('slots', (1, 2, 3, 4, 5, 6))
    hooks = rv.get('dl_hooks', {})
    out = NS(select={}, watch={}, timer={}, final={}, horse={},
             msgs={}, final_msgs={}, activators={}, changes=[])

    def new(name, reason='復活鏈'):
        t = tm.add_trigger(name, enabled=False, looping=False)
        out.changes.append(Change('s39', 'trigger_add', name, 'trigger', '',
                                  f'T{t.trigger_id}', reason))
        return t

    def flag_cond(t, cell, present=True):
        c = t.new_condition.objects_in_area(
            quantity=1, source_player=0, object_list=FLAG_CONST,
            area_x1=cell[0], area_y1=cell[1], area_x2=cell[0], area_y2=cell[1])
        if not present:
            c.inverted = 1
        return c

    def create_flag(t, cell):
        t.new_effect.create_object(source_player=0, object_list_unit_id=FLAG_CONST,
                                   location_x=cell[0], location_y=cell[1])

    def msg_trio(cid, s, tag, fmt):
        g1, g2 = names[cid]
        m = mount[cid]
        trio = []
        for label, txt, conds in (
                ('步', fmt.format(名=g1), [('flag_cell', False), ('rebirth_cell', False)]),
                ('俠', fmt.format(名=g2), [('flag_cell', False), ('rebirth_cell', True)]),
                ('馬', fmt.format(名='馬騎' + g2), [('flag_cell', True)])):
            mt = new(f'訊{cid}位{s}{tag}{label}', '死亡訊息三態')
            for key, present in conds:
                flag_cond(mt, m[key], present)
            mt.new_effect.display_instructions(message=txt, display_time=10)
            trio.append(mt.trigger_id)
        return trio

    for cid in classes:
        m = mount[cid]
        for s in slots:
            hk = hooks.get((cid, s), {})
            # ---- final（第 lives 次死亡）----
            fin = new(f'命盡{cid}位{s}')
            fin.new_condition.destroy_object(unit_object=life[cid][lives - 1])
            trio = msg_trio(cid, s, '終', '<RED>{名}已死亡')
            for x in trio:
                fin.new_effect.activate_trigger(trigger_id=x)
            fin.new_effect.create_object(source_player=s, object_list_unit_id=REVEALER,
                                         location_x=int(spec.respawn[0]),
                                         location_y=int(spec.respawn[1]))
            create_flag(fin, m['final_cell'])
            for x in hk.get('watch_activate', []):
                fin.new_effect.activate_trigger(trigger_id=x)
            out.final[(cid, s)] = fin.trigger_id
            out.final_msgs[(cid, s)] = trio
            # ---- watch/timer，L 由高到低串鏈 ----
            next_tid = fin.trigger_id
            for L in range(lives - 1, 0, -1):
                tmr = new(f'重生{cid}位{s}命{L}')
                tmr.new_condition.timer(timer=10)
                tmr.new_effect.change_ownership(source_player=0, target_player=s,
                                                selected_object_ids=[life[cid][L]])
                tmr.new_effect.remove_object(source_player=0,
                                             selected_object_ids=[boxes[cid][L - 1]])
                for x in hk.get('timer_deactivate', []):
                    tmr.new_effect.deactivate_trigger(trigger_id=x)
                for x in hk.get('timer_activate', []):
                    tmr.new_effect.activate_trigger(trigger_id=x)
                tmr.new_effect.activate_trigger(trigger_id=next_tid)
                out.timer[(cid, s, L)] = tmr.trigger_id

                w = new(f'監視{cid}位{s}命{L}')
                w.new_condition.destroy_object(unit_object=life[cid][L - 1])
                trio = msg_trio(cid, s, f'命{L}', '<RED>{名}已受傷，10秒後重生(%d)' % L)
                for x in trio:
                    w.new_effect.activate_trigger(trigger_id=x)
                for x in hk.get('watch_activate', []):
                    w.new_effect.activate_trigger(trigger_id=x)
                w.new_effect.activate_trigger(trigger_id=tmr.trigger_id)
                out.watch[(cid, s, L)] = w.trigger_id
                out.msgs[(cid, s, L)] = trio
                next_tid = w.trigger_id
            # ---- 馬騎監視 per 命（由 X馬3◇命L 啟動；預置馬騎死→該命的重生計時）----
            for L in range(1, lives):
                hw = new(f'馬監視{cid}位{s}命{L}')
                hw.new_condition.destroy_object(unit_object=m['mount_ref'])
                for x in out.msgs[(cid, s, L)]:
                    hw.new_effect.activate_trigger(trigger_id=x)
                hw.new_effect.activate_trigger(trigger_id=out.timer[(cid, s, L)])
                out.horse[(cid, s, L)] = hw.trigger_id
            hwf = new(f'馬監視{cid}位{s}終')
            hwf.new_condition.destroy_object(unit_object=m['mount_ref'])
            for x in out.final_msgs[(cid, s)]:
                hwf.new_effect.activate_trigger(trigger_id=x)
            hwf.new_effect.create_object(source_player=s, object_list_unit_id=REVEALER,
                                         location_x=int(spec.respawn[0]),
                                         location_y=int(spec.respawn[1]))
            create_flag(hwf, m['final_cell'])
            out.horse[(cid, s, lives)] = hwf.trigger_id
            # ---- 啟動器（enable_lists 分塊 ≤200）----
            acts = []
            lst = rv['enable_lists'].get((cid, s), [])
            for i in range(0, len(lst), 200):
                a = new(f'啟動{cid}位{s}#{i // 200}')
                for x in lst[i:i + 200]:
                    a.new_effect.activate_trigger(trigger_id=x)
                acts.append(a.trigger_id)
            out.activators[(cid, s)] = acts

    # ---- 選角（先建全數，後補互斥停用）----
    for cid in classes:
        for s in slots:
            sel = tm.add_trigger(f'選角{cid}位{s}', enabled=True, looping=False)
            out.changes.append(Change('s39', 'trigger_add', f'選角{cid}位{s}', 'trigger',
                                      '', f'T{sel.trigger_id}', '選角'))
            sel.new_condition.object_selected_multiplayer(
                unit_object=spec.hero_refs[cid], source_player=s)
            sel.new_effect.change_ownership(source_player=8, target_player=s,
                                            selected_object_ids=[spec.hero_refs[cid]])
            sel.new_effect.change_object_hp(quantity=rv['base_hp'][cid], operation=1,
                                            source_player=-1,
                                            selected_object_ids=[spec.hero_refs[cid]])
            sel.new_effect.deactivate_trigger(trigger_id=rv['invuln_tids'][cid])
            sel.new_effect.activate_trigger(
                trigger_id=out.watch[(cid, s, 1)] if lives > 1 else out.final[(cid, s)])
            for a in out.activators[(cid, s)]:
                sel.new_effect.activate_trigger(trigger_id=a)
            sel.new_effect.display_instructions(
                message=f'<GREEN>玩家{s} 選擇了 {names[cid][0]}', display_time=8)
            out.select[(cid, s)] = sel.trigger_id
    for cid in classes:
        for s in slots:
            sel = tm.triggers_by_id[out.select[(cid, s)]]
            for cid2 in classes:
                for s2 in slots:
                    if (cid2, s2) != (cid, s) and (cid2 == cid or s2 == s):
                        sel.new_effect.deactivate_trigger(trigger_id=out.select[(cid2, s2)])
    return out

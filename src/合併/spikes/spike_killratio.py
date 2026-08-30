# -*- coding: utf-8 -*-
"""Kill Ratio（屬性 44）死亡回歸 spike（2026-08-30）。
問題：獎勵條件 KR≥1、KR＝擊殺−損失；英雄死亡算損失 → 復活後 KR 負值 → 獎勵停擺。
驗證 DE 的 Modify Resource 能否直接改屬性 44（SET 歸零／ADD 補償），含陽性對照。
用法: python spike_killratio.py <template> <輸出>"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from AoE2ScenarioParser.scenarios.aoe2_de_scenario import AoE2DEScenario
from AoE2ScenarioParser.datasets.players import PlayerId

KNIGHT, MILITIA, VILLAGER = 38, 74, 83
KR, KILLS, GOLD = 44, 20, 3
SET, ADD = 1, 2
P0, P1, P2 = PlayerId.GAIA, PlayerId.ONE, PlayerId.TWO


def main(src, out):
    scn = AoE2DEScenario.from_file(src)
    um, tm = scn.unit_manager, scn.trigger_manager
    cx = scn.map_manager.map_width // 2

    def add(player, const, x, y):
        return um.add_unit(player=player, unit_const=const, x=x + .5, y=y + .5).reference_id

    def trig(name, timer=None, enabled=True, looping=False):
        t = tm.add_trigger(name, enabled=enabled, looping=looping)
        if timer is not None:
            t.new_condition.timer(timer=timer)
        return t

    def chat(t, m):
        t.new_effect.send_chat(source_player=P1, message=m)

    add(P1, KNIGHT, cx, cx)
    victim = add(P1, VILLAGER, cx - 12, cx - 12)          # 遠離戰場，t40 被殺＝模擬英雄死亡
    for i in range(6):
        add(P2, MILITIA, cx + 4 + (i % 3) * 2, cx + 4 + (i // 3) * 2)

    t = trig('t0設定', 0)
    t.new_effect.change_diplomacy(diplomacy=3, source_player=P1, target_player=P2)
    t.new_effect.change_diplomacy(diplomacy=3, source_player=P2, target_player=P1)
    t.new_effect.change_object_stance(source_player=P2, object_list_unit_id=MILITIA,
                                      attack_stance=3, area_x1=0, area_y1=0,
                                      area_x2=cx * 2, area_y2=cx * 2)
    chat(t, '★KR spike：用騎士殺 P2 民兵（不還手）。每殺 1 隻應出現恰好 1 行[R]')

    r = trig('R獎勵循環', looping=True)
    r.new_condition.accumulate_attribute(quantity=1, attribute=KR, source_player=P1)
    r.new_condition.timer(timer=1)
    r.new_effect.tribute(quantity=-10, tribute_list=GOLD, source_player=P1, target_player=P0)
    chat(r, '[R] 擊殺獎勵 +10金 → KR SET 0')
    r.new_effect.modify_resource(quantity=0, tribute_list=KR, source_player=P1, operation=SET)

    p = trig('P陽性對照')
    p.new_condition.accumulate_attribute(quantity=1, attribute=KR, source_player=P1)
    chat(p, '[P] 陽性對照：KR≥1 條件成立過（第一次擊殺）')
    for n in (1, 2, 3, 4):
        k = trig(f'K{n}')
        k.new_condition.accumulate_attribute(quantity=n, attribute=KILLS, source_player=P1)
        chat(k, f'[K{n}] 屬性20 累計擊殺≥{n}（對照：死亡不應影響此值）')

    d = trig('D模擬死亡', 40)
    d.new_effect.kill_object(source_player=P1, selected_object_ids=[victim])
    chat(d, '[D] t40 己方村民陣亡＝模擬英雄死亡。接著殺 1 隻：無[R]→死亡扣KR確認；再殺 1 隻應有[R]')

    c = trig('C補償', 80)
    c.new_effect.modify_resource(quantity=2, tribute_list=KR, source_player=P1, operation=ADD)
    chat(c, '[C] t80 KR ADD +2（未擊殺）：若立刻出現 1 行[R]→ ADD 有效＝修法可行；若刷屏→SET 無效')

    for s in (20, 40, 60, 80, 100):
        chat(trig(f'心跳{s}', s), f'--- t{s} ---')

    tm.legacy_execution_order = True
    scn.write_to_file(out)
    print('已寫出', out)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])

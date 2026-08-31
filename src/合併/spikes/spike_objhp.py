# -*- coding: utf-8 -*-
"""OBJECT_HP 條件 spike（2026-08-31）：東碼頭「精力不足封鎖」在遊戲內完全沒攔到（血不夠照樣扣、當場死），
四件未實證的事一次驗清：

A 比較方向  —— `comparison` 是「HP <op> quantity」還是反過來（quantity <op> HP）。
B 大數值    —— 十萬／二十萬級的 HP 是否照樣比得動（本體英雄血是百萬級）。
C OR 展開   —— s39 會把單 ref 的 HP 條件展開成「本體 OR 備身1 OR 備身2」，
              「≤ 才封鎖」的極性在滿血備身在場時是否仍只由低血那具決定。
D 同 tick 順序 —— A 觸發同時啟動 B(小id) 與 C(大id)，C 停用 B；B 會不會已經先跑掉？
              （封鎖器 id 一定比原作扣費觸發大，這決定封鎖能不能來得及。）

看法：每項條件成立就發一句帶編號的訊息。開場印「應該出現哪些編號」，t=20 印對帳表。
陽性對照：A1／A4／B2／C1／D1 必須出現；A2／A3／C2 必須不出現。
用法: python spikes/spike_objhp.py <template> <輸出>"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, __file__.rsplit('spikes', 1)[0])
from core.scenario_io import load, write_out, deploy

MILITIA, FLAG = 74, 600
P1 = 1
ADD, SET = 2, 1
EQUAL, LESS, LARGER, LE, GE = 0, 1, 2, 3, 4      # Comparison
TH = 100000                                       # 門檻（＝東碼頭票價）


def main(src, out):
    scn = load(src)
    um, tm, mm = scn.unit_manager, scn.trigger_manager, scn.map_manager
    cx = mm.map_width // 2
    y = cx - 10

    def add(const, x, yy, p=P1):
        return um.add_unit(player=p, unit_const=const, x=x + .5, y=yy + .5).reference_id
    # U1 低血（≈5 萬）、U2 高血（≈15 萬）、U3 滿血備身替身（≈20 萬）、U4 預設小血（40）
    U1, U2, U3, U4 = (add(MILITIA, cx - 4, y), add(MILITIA, cx - 2, y),
                      add(MILITIA, cx, y), add(MILITIA, cx + 2, y))
    add(FLAG, cx - 4, y + 2, p=0)

    def trig(name, timer=None, enabled=True, looping=False):
        t = tm.add_trigger(name, enabled=enabled, looping=looping)
        if timer is not None:
            t.new_condition.timer(timer=timer)
        return t

    def chat(t, m):
        t.new_effect.send_chat(source_player=P1, message=m)

    # ---- 佈置：拉高上限再打傷（改血上限在 DE 會同步加當前血）----
    t = trig('佈置', 0)
    for r in (U1, U2, U3):
        t.new_effect.change_object_hp(source_player=P1, selected_object_ids=[r],
                                      quantity=200000, operation=ADD)
    t.new_effect.damage_object(source_player=P1, selected_object_ids=[U1], quantity=150000)
    t.new_effect.damage_object(source_player=P1, selected_object_ids=[U2], quantity=50000)
    t.new_effect.change_object_name(source_player=P1, selected_object_ids=[U1], message='U1 低血 5萬')
    t.new_effect.change_object_name(source_player=P1, selected_object_ids=[U2], message='U2 高血 15萬')
    t.new_effect.change_object_name(source_player=P1, selected_object_ids=[U3], message='U3 滿血 20萬(備身)')
    t.new_effect.change_object_name(source_player=P1, selected_object_ids=[U4], message='U4 預設 40')
    chat(t, 'HP條件spike：四隻民兵已設好血量（點選看名字與血條）。應出現 A1 A4 B2 C1 D1；不應出現 A2 A3 C2')

    def hp_case(label, ref, cmp_, qty, msg, timer=5):
        t = trig(label, timer)
        t.new_condition.object_hp(unit_object=ref, quantity=qty, comparison=cmp_)
        chat(t, msg)

    # ---- A 比較方向（門檻 10 萬）----
    hp_case('A1', U1, LE, TH, 'A1 出現＝U1(5萬) 判定「HP ≤ 10萬」成立（比較方向＝HP op quantity，正確）')
    hp_case('A2', U1, GE, TH, 'A2 出現＝U1(5萬) 竟然「HP ≥ 10萬」成立 → 比較方向是反的！')
    hp_case('A3', U2, LE, TH, 'A3 出現＝U2(15萬) 竟然「HP ≤ 10萬」成立 → 比較方向是反的！')
    hp_case('A4', U2, GE, TH, 'A4 出現＝U2(15萬) 判定「HP ≥ 10萬」成立（正確）')
    # ---- B 大數值 vs 小數值 ----
    hp_case('B1', U4, LE, 20, 'B1 出現＝U4(40血) 判定「HP ≤ 20」成立 → 小數值也反了')
    hp_case('B2', U4, GE, 20, 'B2 出現＝U4(40血) 判定「HP ≥ 20」成立（小數值正常）')
    # ---- C OR 展開後的「≤ 才封鎖」極性（模擬 s39 展開形狀）----
    t = trig('C1', 5)
    t.new_condition.object_hp(unit_object=U1, quantity=TH, comparison=LE)
    t.new_condition.or_()
    t.new_condition.object_hp(unit_object=U3, quantity=TH, comparison=LE)
    chat(t, 'C1 出現＝「低血本體 OR 滿血備身」的 ≤ 判定成立（極性可用，封鎖器邏輯正確）')
    t = trig('C2', 5)
    t.new_condition.object_hp(unit_object=U2, quantity=TH, comparison=LE)
    t.new_condition.or_()
    t.new_condition.object_hp(unit_object=U3, quantity=TH, comparison=LE)
    chat(t, 'C2 出現＝高血本體＋滿血備身也被 ≤ 判定成立 → 會誤擋（極性不可用）')
    # ---- D 同 tick 啟動順序：大 id 的封鎖器攔不攔得住小 id 的扣費 ----
    d_small = trig('D甲扣費', enabled=False)          # 先建＝小 id（模擬原作扣費 T3750）
    chat(d_small, 'D1 出現＝小id「扣費」在同 tick 已經跑掉，大id 封鎖器攔不住（封鎖必須早一個 tick）')
    d_big = trig('D乙封鎖', enabled=False)            # 後建＝大 id（模擬我們的封鎖器）
    d_big.new_effect.deactivate_trigger(trigger_id=d_small.trigger_id)
    chat(d_big, 'D2 封鎖器執行（無論 D1 有沒有出現都會印）')
    t = trig('D起', 12)
    t.new_effect.activate_trigger(trigger_id=d_small.trigger_id)
    t.new_effect.activate_trigger(trigger_id=d_big.trigger_id)
    chat(t, 't12 D組：同時啟動「扣費(小id)」與「封鎖(大id)」，看 D1 會不會出現')

    t = trig('對帳', 20)
    chat(t, 't20 回報：A1~A4／B1 B2／C1 C2／D1 D2 各有沒有出現。'
            '正常應為 A1✓A2✗A3✗A4✓ B1✗B2✓ C1✓C2✗ D1✓D2✓')

    write_out(scn, out)
    print(f'完成: {out}（觸發 {len(tm.triggers)} 支）')
    print('部署:', deploy(out))


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])

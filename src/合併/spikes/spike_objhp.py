# -*- coding: utf-8 -*-
"""血量條件 spike v2（2026-08-31）：東碼頭「精力不足封鎖」在遊戲內完全沒攔到（血不夠照樣扣、當場死）。

v1 作廢的教訓：v1 用 `Change Object HP ADD 200000` 想造 20 萬上限——**上限是 int16、天花板 32767**
（`古龍921_DE遷移記錄.md`：超過一點就回繞致死；南宮尾葉四人溢位即此），20 萬回繞成 3392，
再打 15 萬傷害 → 單位開場就死，整個 v1 量不到東西。
v2 照本體真實模型佈置：**上限留在 int16 小值（+32000），當前血量用負傷害灌到幾十萬**（float32、單位不夾）。

驗五件事：
A 門檻 100,000（超過 int16）—— OBJECT_HP 的 quantity 吃不吃這麼大的數；這是封鎖器沒攔到的第一嫌疑。
E 門檻 30,000（int16 內）—— 同樣的條件換成小門檻是否正常，用來分辨「條件壞」還是「數值太大」。
C 跨命 OR 極性 —— s39 會把單 ref 的 HP 條件展開成「本體 OR 備身」，「≤ 才封鎖」是否只由低血那具決定。
F 變數路線 —— `MODIFY_VARIABLE_BY_ATTRIBUTE` 讀 HIT_POINTS 進變數（**按玩家＋單位種類選取、不吃 ref**，
  可免疫 OR 展開），再用 `VARIABLE_VALUE` 比 100,000。若 A 失敗、F 成功，封鎖器就改走這條。
D 同 tick 啟動順序 —— 大 id 的封鎖器攔不攔得住小 id 的扣費（封鎖器 id 必然大於原作扣費觸發）。

用法: python spikes/spike_objhp.py <template> <輸出>"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, __file__.rsplit('spikes', 1)[0])
from core.scenario_io import load, write_out, deploy

MILITIA, SPEARMAN, ARCHER, FLAG = 74, 93, 4, 600
P1 = 1
ADD, SET = 2, 1
EQUAL, LESS, LARGER, LE, GE = 0, 1, 2, 3, 4      # Comparison
BIG, SMALL = 100000, 30000                        # 兩個門檻：超 int16／int16 內
V_LOW, V_HIGH = 90, 91                            # 變數 id（避開 s375 killvar 佔用區）


def main(src, out):
    scn = load(src)
    um, tm, mm = scn.unit_manager, scn.trigger_manager, scn.map_manager
    cx = mm.map_width // 2
    y = cx - 10

    def add(const, x, yy, p=P1):
        return um.add_unit(player=p, unit_const=const, x=x + .5, y=yy + .5).reference_id
    U1, U2, U3, U4 = (add(MILITIA, cx - 6, y), add(MILITIA, cx - 4, y),
                      add(MILITIA, cx - 2, y), add(MILITIA, cx, y))
    F_LOW, F_HIGH = add(SPEARMAN, cx + 3, y), add(ARCHER, cx + 5, y)
    add(FLAG, cx - 6, y + 2, p=0)
    tm.add_variable('血低', V_LOW)
    tm.add_variable('血高', V_HIGH)

    def trig(name, timer=None, enabled=True, looping=False):
        t = tm.add_trigger(name, enabled=enabled, looping=looping)
        if timer is not None:
            t.new_condition.timer(timer=timer)
        return t

    def chat(t, m):
        t.new_effect.send_chat(source_player=P1, message=m)

    # ---- 佈置：上限只加到 int16 安全區；當前血量用負傷害灌大 ----
    t = trig('佈置', 0)
    for r in (U1, U2, U3, U4, F_LOW, F_HIGH):
        t.new_effect.change_object_hp(source_player=P1, selected_object_ids=[r],
                                      quantity=32000, operation=ADD)
    for r, heal in ((U1, -50000), (U2, -150000), (U3, -150000), (F_LOW, -50000), (F_HIGH, -150000)):
        t.new_effect.damage_object(source_player=P1, selected_object_ids=[r], quantity=heal)
    for r, nm in ((U1, 'U1 約5萬'), (U2, 'U2 約15萬'), (U3, 'U3 約15萬(當備身)'), (U4, 'U4 約3萬2(未灌)'),
                  (F_LOW, 'F低 長槍兵 約5萬'), (F_HIGH, 'F高 弓兵 約15萬')):
        t.new_effect.change_object_name(source_player=P1, selected_object_ids=[r], message=nm)
    chat(t, '血量條件spike v2：六隻已灌好血（點選看名字與血量）。上限一律 int16 安全值，當前血量用負傷害灌大')

    def hp_case(label, ref, cmp_, qty, msg, timer=6):
        t = trig(label, timer)
        t.new_condition.object_hp(unit_object=ref, quantity=qty, comparison=cmp_)
        chat(t, msg)

    # ---- A：門檻 100,000（超過 int16）----
    hp_case('A1', U1, LE, BIG, 'A1 ✓ U1(5萬) ≤10萬 成立 → 大門檻可用（封鎖器問題不在數值）')
    hp_case('A2', U2, LE, BIG, 'A2 ✗ U2(15萬) 竟然 ≤10萬 成立 → 大門檻語意壞了')
    hp_case('A3', U2, GE, BIG, 'A3 ✓ U2(15萬) ≥10萬 成立')
    hp_case('A4', U1, GE, BIG, 'A4 ✗ U1(5萬) 竟然 ≥10萬 成立 → 比較方向相反')
    # ---- E：門檻 30,000（int16 內）——用來分辨「條件壞」還是「數值太大」----
    hp_case('E1', U4, LE, SMALL, 'E1 ✓ U4(3萬2) ≤3萬 不該成立…出現代表小門檻也怪（見對帳說明）')
    hp_case('E2', U1, GE, SMALL, 'E2 ✓ U1(5萬) ≥3萬 成立（小門檻正常）')
    hp_case('E3', U1, LE, SMALL, 'E3 ✗ U1(5萬) 竟然 ≤3萬 成立 → 比較方向相反')
    # ---- C：跨命 OR 極性（模擬 s39 展開形狀）----
    def or_case(label, a, b, qty, msg):
        t = trig(label, 6)
        t.new_condition.object_hp(unit_object=a, quantity=qty, comparison=LE)
        t.new_condition.or_()
        t.new_condition.object_hp(unit_object=b, quantity=qty, comparison=LE)
        chat(t, msg)
    or_case('C1', U1, U3, BIG, 'C1 ✓「低血本體 OR 高血備身」≤10萬 成立 → 極性可用')
    or_case('C2', U2, U3, BIG, 'C2 ✗ 高血本體＋高血備身也成立 → 極性不可用（會誤擋）')
    or_case('C3', U4, U3, SMALL, 'C3 ✓ 小門檻版：低血(U4) OR 高血(U3) ≤3萬 成立')
    or_case('C4', U1, U3, SMALL, 'C4 ✗ 小門檻版：兩者都高於 3萬 卻成立 → 極性不可用')
    # ---- F：變數路線（不吃 ref，按玩家＋單位種類讀 HP）----
    t = trig('F讀取', 8)
    t.new_effect.modify_variable_by_attribute(source_player=P1, object_list_unit_id=SPEARMAN,
                                              object_attributes=0, operation=SET, variable=V_LOW)
    t.new_effect.modify_variable_by_attribute(source_player=P1, object_list_unit_id=ARCHER,
                                              object_attributes=0, operation=SET, variable=V_HIGH)
    chat(t, 't8 F：已把長槍兵(5萬)與弓兵(15萬)的 HP 讀進變數')
    t = trig('F1', 10)
    t.new_condition.variable_value(variable=V_LOW, quantity=BIG, comparison=LE)
    chat(t, 'F1 ✓ 變數(長槍兵 5萬) ≤10萬 成立 → 變數路線可用')
    t = trig('F2', 10)
    t.new_condition.variable_value(variable=V_HIGH, quantity=BIG, comparison=LE)
    chat(t, 'F2 ✗ 變數(弓兵 15萬) 竟然 ≤10萬 成立 → 變數沒讀到真血量')
    t = trig('F3', 10)
    t.new_condition.variable_value(variable=V_HIGH, quantity=BIG, comparison=GE)
    chat(t, 'F3 ✓ 變數(弓兵 15萬) ≥10萬 成立')
    # ---- D：同 tick 啟動順序 ----
    d_small = trig('D甲扣費', enabled=False)          # 先建＝小 id（模擬原作扣費 T3750）
    chat(d_small, 'D1 出現＝小id「扣費」同 tick 已跑掉，大id 封鎖器攔不住（封鎖必須早一個 tick）')
    d_big = trig('D乙封鎖', enabled=False)            # 後建＝大 id（模擬封鎖器）
    d_big.new_effect.deactivate_trigger(trigger_id=d_small.trigger_id)
    chat(d_big, 'D2 封鎖器執行（必出現）')
    t = trig('D起', 14)
    t.new_effect.activate_trigger(trigger_id=d_small.trigger_id)
    t.new_effect.activate_trigger(trigger_id=d_big.trigger_id)
    chat(t, 't14 D組：同時啟動「扣費(小id)」與「封鎖(大id)」')

    t = trig('對帳', 20)
    chat(t, 't20 回報 A1~A4／E1~E3／C1~C4／F1~F3／D1 D2 各有沒有出現。'
            '正常＝A1 A3 ✓、A2 A4 ✗；E2 ✓、E1 E3 ✗；C1 C3 ✓、C2 C4 ✗；F1 F3 ✓、F2 ✗；D1 D2 都出現。'
            '另請點 U4 回報它的血量數字（驗上限 int16 天花板）')

    write_out(scn, out)
    print(f'完成: {out}（觸發 {len(tm.triggers)} 支）')
    print('部署:', deploy(out))


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])

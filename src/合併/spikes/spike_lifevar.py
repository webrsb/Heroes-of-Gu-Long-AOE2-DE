# -*- coding: utf-8 -*-
"""命旗變數化前置實測：`Variable Value`（變數 vs 常數）在 DE 到底能不能當閘門？（2026-09-01）

起因：命旗（Gaia 720 九環旗 @ life_cells）落在原作技能表格上，選完角色後那根桿子遮住
「佛」那一格，且 720 就是原作的任務道具，玩家看到會以為觸發了什麼（使用者 2026-09-01 回報）。
移欄查無好格（角落只剩 229/239 兩欄乾淨、外圍 204-208 在極練場活動區內），故改走變數。

**已知與未知**：`spike_killvar` 已實證「兩法皆過」（`merge_spec.yaml` killvar 段），
所以 `Compare Variables`（變數 vs 變數）、`Variable Value` 的 **≥ 對常數**、
`Change Variable ADD`、`Modify Variable by Resource/Variable` 都算驗過了。
命旗變數化多出來的四件事沒人驗過，正是這支要測的：
**EQUAL 比較**（命數是等值選路，不是門檻）、**SET 覆寫**（換命要蓋掉舊值，killvar 只用 ADD）、
**開場停用後才被 Activate 的觸發**吃不吃得到閘、**looping 觸發**每輪讀不讀得到。
（`spike_objhp` 曾以「變數路線作廢」收尾，但那支的敗因歸給 `MODIFY_VARIABLE_BY_ATTRIBUTE`
讀不到血量；本 spike 把寫入與讀取從任何屬性讀取中隔離，順便替那個歸因補一道交叉驗證。）

驗四件事（對應命旗的四種用法）：
  1. SET 寫入後 `Variable Value EQUAL` 讀得到           → 選角建第1命旗
  2. 再 SET 覆寫後，舊值不再成立、新值成立               → 換命：撤舊旗建新旗
  3. SET 0 後回到零                                      → 末命撤旗
  4. **開場停用、後來才被 Activate 的觸發**也讀得到      → ◇命 副本由復活鏈啟動後才吃閘
  5. **looping 觸發**的變數條件每輪都成立               → 原作 18 支迴圈觸發也帶命旗條件
陽性對照：同一時刻用「Gaia 720 單格」旗閘做一模一樣的判斷（[B*] 行）。
旗閘有出、變數閘沒出 ＝ 變數路線壞；兩者都沒出 ＝ 測試檔本身壞掉（別誤判）。

用法: python spikes/spike_lifevar.py <template> <輸出>
      python spikes/spike_lifevar.py "C:/.../scenario/0_E3_Scenario.aoe2scenario" out/SPIKE變數閘.aoe2scenario
"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, __file__.rsplit('spikes', 1)[0])
from core.scenario_io import load, write_out, deploy

FLAG, MILITIA = 720, 74                      # 720＝九環旗（現行命旗常數）
EQUAL, GE = 0, 4                             # Comparison
SET = 1                                      # Operation
V = 21                                       # 受測變數（命數）


def main(src, out):
    scn = load(src)
    um, tm, mm = scn.unit_manager, scn.trigger_manager, scn.map_manager
    tm.add_variable('命數測試', variable_id=V)
    cx = mm.map_width // 2
    cy = cx - 8
    A, B = (cx - 3, cy), (cx + 3, cy)        # 對照旗的兩個格子（模擬 life_cells[0]/[1]）
    loop_target = um.add_unit(player=0, unit_const=MILITIA,
                              x=cx + .5, y=cy + 4.5).reference_id

    def trig(name, timer=None, enabled=True, looping=False):
        t = tm.add_trigger(name, enabled=enabled, looping=looping)
        if timer is not None:
            t.new_condition.timer(timer=timer)
        return t

    def chat(t, m):
        t.new_effect.send_chat(source_player=1, message=m)

    def var_cond(t, value, comparison=EQUAL):
        t.new_condition.variable_value(variable=V, quantity=value, comparison=comparison)

    def flag_cond(t, cell):
        t.new_condition.objects_in_area(quantity=1, source_player=0, object_list=FLAG,
                                        area_x1=cell[0], area_y1=cell[1],
                                        area_x2=cell[0], area_y2=cell[1])

    def set_var(t, value):
        t.new_effect.change_variable(variable=V, quantity=value, operation=SET)

    def make_flag(t, cell):
        t.new_effect.create_object(source_player=0, object_list_unit_id=FLAG,
                                   location_x=cell[0], location_y=cell[1])

    def drop_flag(t, cell):
        t.new_effect.remove_object(source_player=0, object_list_unit_id=FLAG,
                                   area_x1=cell[0], area_y1=cell[1],
                                   area_x2=cell[0], area_y2=cell[1])

    # ---- t0/t2：開場與通道對照 ----
    t = trig('開場', 0)
    t.new_effect.change_object_hp(source_player=-1, selected_object_ids=[loop_target],
                                  quantity=30000, operation=2)
    t.new_effect.change_object_name(source_player=-1, selected_object_ids=[loop_target],
                                    message='迴圈靶（掉血＝looping 變數條件有效）')
    chat(t, '變數閘測試：全程約 25 秒，看聊天列的標籤。[A*]＝變數閘、[B*]＝旗閘（陽性對照）、[X*]＝異常')
    chat(trig('通道對照', 2), '[P] 訊息通道正常——以下若 [A*] 全無但 [B*] 有，就是變數路線壞')

    # ---- t3：寫 V=1（模擬選角建第1命旗）----
    t = trig('寫V1', 3)
    set_var(t, 1)
    make_flag(t, A)
    late = trig('晚啟讀V2', enabled=False)           # 開場停用，t9 才啟動（模擬 ◇命 副本）
    var_cond(late, 2)
    chat(late, '[A3] 後啟觸發讀到 V==2——復活鏈啟動後才吃閘的用法成立')
    loop = trig('迴圈讀V2', enabled=False, looping=True)
    var_cond(loop, 2)
    loop.new_effect.damage_object(source_player=-1, selected_object_ids=[loop_target],
                                  quantity=100)
    t.new_effect.deactivate_trigger(trigger_id=loop.trigger_id)   # 先確保停用態明確

    # ---- t6：讀 V=1（四種判讀）----
    t = trig('讀V1', 6)
    var_cond(t, 1)
    chat(t, '[A1] V==1 讀到——Variable Value（變數 vs 常數）EQUAL 有效')
    t = trig('讀V1GE', 6)
    var_cond(t, 1, GE)
    chat(t, '[A>=] V>=1 讀到——LARGER_OR_EQUAL 有效')
    t = trig('讀旗A', 6)
    flag_cond(t, A)
    chat(t, '[B1] 旗A 讀到——旗閘（陽性對照）有效')
    t = trig('誤讀V2', 6)
    var_cond(t, 2)
    chat(t, '[X1] 異常：V==2 在 V 應為 1 時也成立（EQUAL 沒在比較，條件恆真）')

    # ---- t9：SET 覆寫成 2（模擬換命：撤舊旗、建新旗）＋啟動後啟/迴圈觸發 ----
    t = trig('寫V2', 9)
    set_var(t, 2)
    drop_flag(t, A)
    make_flag(t, B)
    t.new_effect.activate_trigger(trigger_id=late.trigger_id)
    t.new_effect.activate_trigger(trigger_id=loop.trigger_id)

    # ---- t12：讀 V=2、驗舊值已被覆寫 ----
    t = trig('讀V2', 12)
    var_cond(t, 2)
    chat(t, '[A2] V==2 讀到——SET 覆寫有效（換命語意成立）')
    t = trig('殘V1', 12)
    var_cond(t, 1)
    chat(t, '[X2] 異常：V==1 仍成立——SET 沒覆寫（命旗變數化不可用）')
    t = trig('讀旗B', 12)
    flag_cond(t, B)
    chat(t, '[B2] 旗B 讀到、旗A 已撤——旗閘轉移正常')

    # ---- t15：SET 0（模擬末命撤旗）----
    t = trig('寫V0', 15)
    set_var(t, 0)
    drop_flag(t, B)
    t.new_effect.deactivate_trigger(trigger_id=loop.trigger_id)

    # ---- t18：驗歸零 ----
    t = trig('讀V0', 18)
    var_cond(t, 0)
    chat(t, '[A0] V==0 讀到——歸零有效（末命熄火語意成立）')
    t = trig('殘V2', 18)
    var_cond(t, 2)
    chat(t, '[X3] 異常：V==2 仍成立——歸零無效')
    t = trig('殘旗B', 18)
    flag_cond(t, B)
    chat(t, '[XB] 異常：旗B 仍在——連旗閘都不準，測試檔本身有問題')

    # ---- t21：對帳 ----
    chat(trig('對帳', 21),
         '對帳：點畫面中央的「迴圈靶」看血量。少於 30000＝[A迴] looping 變數條件有效；'
         '整數 30000＝looping 沒吃到變數條件。應出現 [P][A1][A>=][B1][A2][A3][B2][A0]，'
         '一個 [X*] 都不該有')
    write_out(scn, out)
    print(f'完成: {out}（觸發 {len(tm.triggers)} 支、變數 V{V}）')
    print('部署:', deploy(out))


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])

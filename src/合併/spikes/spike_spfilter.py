# -*- coding: utf-8 -*-
"""source_player 是否過濾 selected_object_ids？（2026-09-01，攻略 session D12 指定的實測）

起因：`T4360「6大2」E#9` 回復大環丹商販（ref 43835）寫 `sp=0`，1–5P 同位皆 `sp=8`；
但開場觸發 `T1「名」E#59` 已把該商販由 P8 轉給 Gaia(0)。誰對，取決於一件沒人實證過的事：
**效果已用 selected_object_ids 指名目標時，source_player 欄位還會不會當成過濾條件？**
- 若會過濾 → 錯的是 1–5P（sp=8 指不到 Gaia 的商販，回血無效）
- 若不過濾 → 六支都有效，差異純屬寫法，維持原樣即可

做法：一隻 Gaia 民兵（改名標記），三支 timer 觸發各對它下 `Damage Object`，
sel 都指同一隻、只有 sp 不同（8／0／-1），傷害值刻意不同以便從血量反推誰生效。
陽性對照：sp=-1 那支（本專案慣用的中性寫法）必須生效，否則整個測試檔作廢。

用法: python spikes/spike_spfilter.py <template> <輸出>"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, __file__.rsplit('spikes', 1)[0])
from core.scenario_io import load, write_out, deploy

MILITIA, FLAG = 74, 600


def main(src, out):
    scn = load(src)
    um, tm, mm = scn.unit_manager, scn.trigger_manager, scn.map_manager
    cx = mm.map_width // 2
    y = cx - 10

    def add(p, const, x, yy):
        return um.add_unit(player=p, unit_const=const, x=x + .5, y=yy + .5).reference_id
    target = add(0, MILITIA, cx, y)              # Gaia 所有，模擬大環丹商販
    add(1, FLAG, cx, y + 2)

    def trig(name, timer):
        t = tm.add_trigger(name, enabled=True, looping=False)
        t.new_condition.timer(timer=timer)
        return t

    def chat(t, m):
        t.new_effect.send_chat(source_player=1, message=m)

    t = trig('開場', 0)
    t.new_effect.change_object_hp(source_player=-1, selected_object_ids=[target],
                                  quantity=30000, operation=2)      # 上限拉到 int16 安全區
    t.new_effect.change_object_name(source_player=-1, selected_object_ids=[target],
                                    message='靶子 Gaia民兵')
    chat(t, 'sp過濾測試：畫面中央的 Gaia 民兵是靶子（上限已拉到約 3 萬）。點它看血量，依序在 t5/t10/t15 各挨一次傷害')

    for sec, sp, dmg, label in ((5, 8, 1000, 'A sp=8（模擬 1–5P 寫法：物主其實是 Gaia）'),
                                (10, 0, 200, 'B sp=0（模擬 6P 寫法：與物主一致）'),
                                (15, -1, 30, 'C sp=-1（本專案中性寫法＝陽性對照，必須生效）')):
        t = trig(label[:6], sec)
        t.new_effect.damage_object(source_player=sp, selected_object_ids=[target], quantity=dmg)
        chat(t, f't{sec} 已下 {label}，傷害 {dmg}')

    t = trig('對帳', 20)
    chat(t, 't20 點靶子回報血量：扣 1230＝三支全生效（sp 不過濾）／扣 230＝A 無效（sp 會過濾，'
            '1–5P 那種寫法指不到 Gaia 物件）／只扣 30＝只有中性寫法有效')
    write_out(scn, out)
    print(f'完成: {out}（觸發 {len(tm.triggers)} 支）')
    print('部署:', deploy(out))


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])

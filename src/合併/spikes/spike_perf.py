# -*- coding: utf-8 -*-
"""效能壓測：往 template 灌 30,000 支觸發，模擬方案二全矩陣的負載形狀。
組成：24,000 支停用（等選角啟動的家族）＋3,000 支啟用循環（常駐系統）
＋3,000 支啟用非循環（等條件成立）。條件用不會成立的區域檢查（P8 無單位），
效果掛聊天（永不執行）。心跳觸發 t=5/60 各報一次，證明觸發引擎在跑。
用法: python spike_perf.py <template> <輸出> [停用數 循環數 待命數]"""
import sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from AoE2ScenarioParser.scenarios.aoe2_de_scenario import AoE2DEScenario
from AoE2ScenarioParser.datasets.players import PlayerId

def main(src, out):
    t0 = time.time()
    scn = AoE2DEScenario.from_file(src)
    tm = scn.trigger_manager

    t = tm.add_trigger('心跳5', enabled=True)
    t.new_condition.timer(timer=5)
    t.new_effect.send_chat(source_player=PlayerId.ONE, message='壓測檔：觸發引擎運作中(t=5)')
    t = tm.add_trigger('心跳60', enabled=True)
    t.new_condition.timer(timer=60)
    t.new_effect.send_chat(source_player=PlayerId.ONE, message='壓測檔：t=60 心跳正常，請回報讀圖秒數與流暢度')

    def dummy(name, enabled, looping, i):
        t = tm.add_trigger(name, enabled=enabled, looping=looping)
        x = (i * 7) % 110
        y = (i * 13) % 110
        t.new_condition.objects_in_area(quantity=99, source_player=PlayerId.EIGHT,
                                        area_x1=x, area_y1=y, area_x2=x + 3, area_y2=y + 3)
        t.new_effect.send_chat(source_player=PlayerId.ONE, message=f'dummy{i}')

    import sys as _s
    n_off, n_loop, n_wait = (int(_s.argv[3]), int(_s.argv[4]), int(_s.argv[5]))         if len(_s.argv) > 5 else (24000, 3000, 3000)
    for i in range(n_off):
        dummy(f'家族停用{i}', False, False, i)
    for i in range(n_loop):
        dummy(f'常駐循環{i}', True, True, i)
    for i in range(n_wait):
        dummy(f'待命{i}', True, False, i)

    tm.legacy_execution_order = True
    scn.write_to_file(out)
    print(f'完成: {out}（觸發 {len(tm.triggers)} 支，產檔 {time.time()-t0:.0f} 秒）')

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])

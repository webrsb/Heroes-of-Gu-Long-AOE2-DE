# -*- coding: utf-8 -*-
"""AoC 1.21z dat 目標式單位解析（VER 5.7 / GV_TC 欄位序，依 Tapsa genieutils 源碼移植）。
掃描 (type,name_len,id) 錨點 → 前向解析 → CopyID 驗證。"""
import io, sys, zlib, struct
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

d = zlib.decompressobj(-15).decompress(
    open(r'G:\archive\game\aoe2\Age of Empires II\Data\empires2_x1_p1.dat', 'rb').read())

TARGETS = {4: '弓兵(對照)', 74: '民兵(對照)', 37: '未知37', 94: '拳94', 95: '城門95',
           573: '未知573', 817: '雕像817', 837: '顯示器837',
           845: '刀845', 432: '劍432', 752: '槍752', 428: '棍428', 765: '暗765'}

def u8(o): return d[o], o + 1
def i16(o): return struct.unpack_from('<h', d, o)[0], o + 2
def i32(o): return struct.unpack_from('<i', d, o)[0], o + 4
def f32(o): return struct.unpack_from('<f', d, o)[0], o + 4

def parse(pos):
    o = pos
    typ, o = u8(o)
    nlen, o = i16(o)
    uid, o = i16(o)
    lang, o = i16(o); _, o = i16(o)
    ucls, o = i16(o)
    o += 2 * 2            # standing pair
    o += 2 + 2 + 1        # dying, undead, undeadmode
    hp, o = i16(o)
    los, o = f32(o)
    o += 1                # garrison
    o += 12               # collision 3f
    o += 2 + 2            # trainsound, damagesound
    dead_unit, o = i16(o)
    o += 1 + 1; icon, o = i16(o); o += 1 + 2 + 1 + 1   # sort,builton,icon,hide,portrait,enabled,disabled
    o += 4 + 4 + 8        # placement side/terrain pairs, clearance 2f
    o += 1 + 1 + 2 + 1 + 2 + 4 + 1 + 1 + 1 + 1 + 1 + 4 + 1
    o += 4 + 4 + 4        # langdllhelp, hotkeytext, hotkeyid
    o += 4                # recyclable..gathergroup
    o += 1 + 1 + 1        # occlusion, obstruction×2
    o += 1 + 1 + 2        # trait, civ, nothing
    o += 1 + 1 + 12       # seleffect, selcolor, outline 3f
    o += 21               # resource storages 3×7
    n, o = u8(o)
    o += n * 5            # damage graphics
    o += 2 + 2 + 1 + 1    # selsound, dyingsound, oldreact, convertterrain
    name = d[o:o + nlen].split(b'\0')[0]
    o += nlen
    copy_id, o = i16(o)
    base_id, o = i16(o)
    r = dict(type=typ, id=uid, cls=ucls, hp=hp, los=round(los, 2), name=name,
             lang=lang, copy=copy_id, dead=dead_unit, icon=icon)
    if copy_id != uid and base_id != uid:
        return None
    if typ == 90 or typ < 20:
        return r
    r['speed'], o = f32(o)
    r['speed'] = round(r['speed'], 3)
    if typ >= 30:
        o += 37           # DeadFish (TC)
    if typ >= 40:
        o += 20           # Bird (TC, 無任務表)
    if typ >= 50:
        base_armor, o = i16(o)
        na, o = i16(o)
        atks = []
        for _ in range(na):
            c, o = i16(o); a, o = i16(o); atks.append((c, a))
        nr, o = i16(o)
        arms = []
        for _ in range(nr):
            c, o = i16(o); a, o = i16(o); arms.append((c, a))
        o += 2            # defense terrain bonus
        maxrange, o = f32(o)
        o += 4            # blast width
        reload_, o = f32(o)
        o += 2 + 2 + 1 + 2 + 12 + 1   # proj,acc,breakoff,framedelay,disp3f,blastlvl
        minrange, o = f32(o)
        o += 4 + 2        # accdisp, atkgraphic
        dm, o = i16(o); da, o = i16(o)
        r.update(base_armor=base_armor, atks=atks, arms=arms,
                 range=round(maxrange, 1), reload=round(reload_, 2),
                 disp_melee=dm, disp_atk=da)
    return r

found = {}
i = 0
L = len(d)
while i < L - 7:
    nlen = struct.unpack_from('<h', d, i + 1)[0]
    uid = struct.unpack_from('<h', d, i + 3)[0]
    if uid in TARGETS and 1 <= nlen <= 40 and d[i] in (10, 20, 25, 30, 40, 50, 60, 70, 80, 90):
        try:
            r = parse(i)
        except Exception:
            r = None
        if r and all(32 <= b < 127 for b in r['name']):
            key = (uid, str(sorted(r.items())))
            if uid not in found:
                found[uid] = []
            if r not in found[uid]:
                found[uid].append(r)
    i += 1

for uid in sorted(TARGETS):
    lst = found.get(uid, [])
    print(f'== {TARGETS[uid]} (const{uid}) — {len(lst)} 種版本 ==')
    for r in lst[:3]:
        atk = ' '.join(f'c{c}:{a}' for c, a in r.get('atks', []))
        arm = ' '.join(f'c{c}:{a}' for c, a in r.get('arms', []))
        print(f"  type={r['type']} name={r['name'].decode()} HP={r['hp']} 速={r.get('speed','-')} "
              f"射程={r.get('range','-')} 攻速={r.get('reload','-')} 顯示攻={r.get('disp_atk','-')} "
              f"顯示甲={r.get('disp_melee','-')} lang={r['lang']}")
        print(f"    攻擊[{atk}] 護甲[{arm}]")

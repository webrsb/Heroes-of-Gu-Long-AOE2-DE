# -*- coding: utf-8 -*-
"""params.revive 結構載入與驗證（plan T2）。
缺欄位/lives<2/六職業展示位或本體ref不齊 → BuildError（缺裁決不默默補）。
hero_consts 建置時由 s38 從單位表讀出補入，不在 yaml。"""
from dataclasses import dataclass, field
from steps.base import BuildError

CLASSES = (1, 2, 3, 4, 5, 6)
REQUIRED = ('lives', 'respawn', 'displays', 'hero_refs', 'retired')


@dataclass
class ReviveSpec:
    lives: int
    respawn: tuple                 # (x, y)
    displays: dict                 # {class_id: (x, y)}
    hero_refs: dict                # {class_id: ref}
    retired: list                  # [tid]
    hero_consts: dict = field(default_factory=dict)   # s38 補入


def load_revive(params: dict) -> ReviveSpec:
    missing = [k for k in REQUIRED if k not in params]
    if missing:
        raise BuildError(f'缺裁決：params.revive 缺欄位 {missing}')
    lives = params['lives']
    if not isinstance(lives, int) or lives < 2:
        raise BuildError(f'缺裁決：revive.lives={lives!r}，必須是 ≥2 的整數（1 條命=無復活，不成立）')
    displays = {int(k): tuple(v) for k, v in params['displays'].items()}
    hero_refs = {int(k): int(v) for k, v in params['hero_refs'].items()}
    for name, d in (('displays', displays), ('hero_refs', hero_refs)):
        lack = [c for c in CLASSES if c not in d]
        if lack:
            raise BuildError(f'缺裁決：revive.{name} 缺職業 {lack}')
    r = ReviveSpec(lives=lives,
                   respawn=tuple(params['respawn']),
                   displays=displays,
                   hero_refs=hero_refs,
                   retired=list(params['retired']))
    r.navigator_const = int(params.get('navigator_const', 128))
    # 廣場顯示器格：須避開任何以玩家為條件的區域觸發（白雲X1 (79,109)-(82,112) 曾被掃到→每 16 秒洗頻，2026-08-30）
    r.navigator_cells = [tuple(float(v) for v in c)
                         for c in params.get('navigator_cells', [[80.5, 110.5], [81.5, 112.5]])]
    return r

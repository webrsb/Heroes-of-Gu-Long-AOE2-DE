# -*- coding: utf-8 -*-
"""每輪建置的實機測試指引。step 自帶模板，這裡只做彙總排版。"""
from dataclasses import dataclass

@dataclass
class StepResult:
    step_id: str
    title: str
    changes: list
    guide: str | None  # step 代入實際改動後的測試說明；None = 沒東西要測

def render_guide(results: list) -> str:
    lines = ['# 測試指引', '',
             '進遊戲方式：單人 → 劇情（不要用編輯器測試模式）。',
             '照順序驗，每項回報「符合預期」或「異常＋截圖」。', '']
    for r in results:
        lines.append(f'### 驗 {r.step_id} {r.title}')
        if not r.changes or not r.guide:
            lines += ['本輪無異動，免測。', '']
        else:
            lines += [f'改動筆數：{len(r.changes)}', r.guide, '']
    return '\n'.join(lines) + '\n'

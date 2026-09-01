# -*- coding: utf-8 -*-
"""雙軌異動紀錄：機器 TSV ＋ 人讀 md。固定檔名，git 承擔歷史。"""
from collections import Counter
from pathlib import Path
from .change import Change, TSV_HEADER, to_tsv_row

def write_step_logs(step_id: str, title: str, intro: str,
                    changes: list, logs_dir: Path):
    logs_dir = Path(logs_dir); logs_dir.mkdir(parents=True, exist_ok=True)
    nn = step_id.lstrip('s')
    tsv_p = logs_dir / f'{nn}_{title}.tsv'
    md_p = logs_dir / f'{nn}_{title}.md'
    tsv_p.write_text('\n'.join([TSV_HEADER] + [to_tsv_row(c) for c in changes]) + '\n',
                     encoding='utf-8', newline='\n')
    kinds = Counter(c.kind for c in changes)
    reasons = sorted({c.reason for c in changes})
    lines = [f'# {step_id} {title}', '', intro, '']
    if not changes:
        lines.append('**本輪無異動。**')
    else:
        lines.append(f'共 **{len(changes)}** 筆異動：')
        lines += [f'- {k}: {n}' for k, n in kinds.most_common()]
        lines += ['', '依據：'] + [f'- {r}' for r in reasons]
    md_p.write_text('\n'.join(lines) + '\n', encoding='utf-8', newline='\n')
    return tsv_p, md_p

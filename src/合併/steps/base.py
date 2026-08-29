# -*- coding: utf-8 -*-
"""Step 介面：純函式變換。不讀寫檔案、不呼叫 write_to_file。"""
from dataclasses import dataclass, field

class BuildError(Exception):
    """spec 未覆蓋的衝突。message 必須列出缺哪條裁決。"""

@dataclass
class BuildContext:
    base: object        # 無法無天 scenario，就地變異
    source: object      # 劍譜5 scenario，唯讀
    spec: object        # MergeSpec
    pairing: object     # PairTable | None
    notes: dict = field(default_factory=dict)  # 步驟間傳遞

class Step:
    id: str = ''
    title: str = ''
    intro: str = ''
    def apply(self, ctx: BuildContext) -> list:
        raise NotImplementedError
    def test_guide(self, changes: list):
        return None

# -*- coding: utf-8 -*-
"""觸發內容指紋：跨版本配對改名觸發用。
排除 trigger_id / selected_object_ids / message —— 這些在兩版間天然漂移。"""

_EFFECT_FIELDS = ('effect_type', 'quantity', 'tribute_list', 'object_list_unit_id',
                  'source_player', 'target_player', 'technology', 'operation',
                  'object_attributes', 'area_x1', 'area_y1', 'area_x2', 'area_y2',
                  'location_x', 'location_y')
_COND_FIELDS = ('condition_type', 'quantity', 'attribute', 'unit_object', 'next_object',
                'object_list', 'source_player', 'technology', 'timer',
                'area_x1', 'area_y1', 'area_x2', 'area_y2', 'inverted', 'comparison')

def _row(obj, fields, tag):
    return (tag,) + tuple(getattr(obj, f, None) for f in fields)

def fingerprint(trigger) -> tuple:
    return (tuple(_row(c, _COND_FIELDS, 'c') for c in trigger.conditions)
            + tuple(_row(e, _EFFECT_FIELDS, 'e') for e in trigger.effects))

def type_signature(trigger) -> tuple:
    return (tuple(('c', c.condition_type) for c in trigger.conditions)
            + tuple(('e', e.effect_type) for e in trigger.effects))

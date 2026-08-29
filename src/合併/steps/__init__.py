# -*- coding: utf-8 -*-
import importlib, pkgutil

def get_steps():
    steps = []
    pkg = importlib.import_module(__name__)
    for m in pkgutil.iter_modules(pkg.__path__):
        if m.name.startswith('s') and m.name[1].isdigit():
            mod = importlib.import_module(f'{__name__}.{m.name}')
            steps.append(mod.STEP)
    return sorted(steps, key=lambda s: s.id)

"""
Handler registry with AUTO-DISCOVERY.

Drop a file `wfXXX_anything.py` in this folder containing a class with
`workflow_id = "WFXXX"` that extends BaseHandler — it is registered automatically.
No imports to edit, no if/else chains.
"""
import importlib
import inspect
import pkgutil
from typing import Dict, Type

from engine.executor import BaseHandler

REGISTRY: Dict[str, Type[BaseHandler]] = {}

for _mod in pkgutil.iter_modules(__path__):
    module = importlib.import_module(f"{__name__}.{_mod.name}")
    for _, cls in inspect.getmembers(module, inspect.isclass):
        if issubclass(cls, BaseHandler) and cls is not BaseHandler and getattr(cls, "workflow_id", ""):
            REGISTRY[cls.workflow_id] = cls

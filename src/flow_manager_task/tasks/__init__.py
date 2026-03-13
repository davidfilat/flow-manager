from __future__ import annotations

import importlib
import pkgutil
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..domain.registry import Registry


def register_all(runner: Registry) -> None:
    for module_info in pkgutil.iter_modules(__path__):
        module = importlib.import_module(f"{__name__}.{module_info.name}")
        if callable(getattr(module, "register", None)):
            module.register(runner)

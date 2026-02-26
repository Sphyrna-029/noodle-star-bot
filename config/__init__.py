import importlib
import pkgutil
from types import ModuleType

__all__: list[str] = []


def _iter_submodules() -> list[str]:
    names: list[str] = []
    for m in pkgutil.iter_modules(__path__):
        if m.ispkg:
            continue
        if m.name.startswith("_"):
            continue
        if m.name == "__init__":
            continue
        names.append(m.name)
    return sorted(names)


def _export_from_module(mod: ModuleType) -> None:
    exports = getattr(mod, "__all__", None)
    if exports is None:
        raise RuntimeError(
            f"{mod.__name__} is missing __all__. "
            "Define __all__ to control what config exports."
        )

    for name in exports:
        if not hasattr(mod, name):
            raise RuntimeError(
                f"{mod.__name__}.__all__ references missing name {name!r}"
            )

        if name in globals():
            raise RuntimeError(
                f"config export collision for {name!r} "
                f"(already exported; new module={mod.__name__})"
            )

        globals()[name] = getattr(mod, name)
        __all__.append(name)


for _name in _iter_submodules():
    _mod = importlib.import_module(f"{__name__}.{_name}")
    _export_from_module(_mod)

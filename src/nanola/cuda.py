from __future__ import annotations

import importlib.util
import os
import shutil
import site
import sys
from pathlib import Path


_DLL_HANDLES = []


def add_packaged_cuda_dll_directories() -> list[Path]:
    """Make NVIDIA pip-package DLLs visible to CTranslate2 on Windows."""
    added = []
    if os.name != "nt":
        return added

    for path in packaged_cuda_dll_directories():
        if path.exists():
            _prepend_process_path(path)
            _DLL_HANDLES.append(os.add_dll_directory(str(path)))
            added.append(path)
    return added


def packaged_cuda_dll_directories() -> list[Path]:
    directories = []
    for module_name in ("nvidia.cublas", "nvidia.cudnn"):
        spec = importlib.util.find_spec(module_name)
        if spec is not None and spec.origin is not None:
            package_dir = Path(spec.origin).parent
            for child in ("bin", "lib"):
                candidate = package_dir / child
                if candidate.exists():
                    directories.append(candidate)

    for base in _site_package_paths():
        for candidate in (
            base / "nvidia" / "cublas" / "bin",
            base / "nvidia" / "cudnn" / "bin",
        ):
            if candidate.exists() and candidate not in directories:
                directories.append(candidate)
    return directories


def find_dll(name: str) -> Path | None:
    path = shutil.which(name)
    if path:
        return Path(path)
    for directory in packaged_cuda_dll_directories():
        candidate = directory / name
        if candidate.exists():
            return candidate
    return None


def _site_package_paths() -> list[Path]:
    paths = []
    for value in sys.path + site.getsitepackages():
        path = Path(value)
        if path.name == "site-packages" and path.exists() and path not in paths:
            paths.append(path)
    user_site = site.getusersitepackages()
    if user_site:
        path = Path(user_site)
        if path.exists() and path not in paths:
            paths.append(path)
    return paths


def _prepend_process_path(path: Path) -> None:
    current = os.environ.get("PATH", "")
    parts = current.split(os.pathsep) if current else []
    text = str(path)
    if text not in parts:
        os.environ["PATH"] = text + (os.pathsep + current if current else "")

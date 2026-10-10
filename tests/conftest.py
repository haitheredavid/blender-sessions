import shutil
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def models_dir(tmp_path: Path) -> Path:
    base = tmp_path / "models"
    shutil.copytree(ROOT / "models" / "_template", base / "_template")
    return base

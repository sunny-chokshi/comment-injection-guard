import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


@pytest.fixture(scope="session", autouse=True)
def model():
    from guard.classifier import MODEL_PATH, train
    if not MODEL_PATH.exists():
        train()
    return MODEL_PATH

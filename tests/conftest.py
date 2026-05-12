from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LOCAL_OPTAGENT_SRC = ROOT.parent / "optagent" / "src"

for path in (ROOT, LOCAL_OPTAGENT_SRC):
    text = str(path)
    if path.exists() and text not in sys.path:
        sys.path.insert(0, text)

"""Consistency check for the label files and the base package.

Fails if
  * a label file is missing a key that another label file defines,
  * the base package uses a ${label_*} / ${state_*} substitution that no
    label file defines, or a label key is not used by the base package,
  * a label value contains characters that break the C++ string literals
    it is pasted into (double quote, backslash).

Run: python tests/check_labels.py
"""

import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
LABEL_DIR = ROOT / "esphome" / "labels"
BASE = ROOT / "esphome" / ".soil-moisture.base.yaml"
KEY_RE = re.compile(r"\$\{((?:label|state)_[a-z0-9_]+)\}")


def load_labels(path: Path) -> dict[str, str]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return {str(k): str(v) for k, v in data["substitutions"].items()}


def main() -> int:
    errors: list[str] = []
    files = sorted(LABEL_DIR.glob(".soil-moisture-labels-*.yaml"))
    if not files:
        print(f"no label files found in {LABEL_DIR}")
        return 1

    labels = {f.name: load_labels(f) for f in files}
    all_keys = set().union(*(set(v) for v in labels.values()))
    used = set(KEY_RE.findall(BASE.read_text(encoding="utf-8")))

    for name, values in labels.items():
        for key in sorted(all_keys - set(values)):
            errors.append(f"{name}: missing key {key}")
        for key, value in values.items():
            if '"' in value or "\\" in value:
                errors.append(f"{name}: {key} contains a quote or backslash")

    for key in sorted(used - all_keys):
        errors.append(f"base package uses undefined substitution {key}")
    for key in sorted(all_keys - used):
        errors.append(f"label key {key} is not used by the base package")

    for e in errors:
        print(f"ERROR {e}")
    if not errors:
        print(f"OK: {len(files)} label files, {len(all_keys)} keys, all consistent")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())

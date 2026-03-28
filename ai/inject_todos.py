import json
from pathlib import Path

gaps_file = Path("gaps.json")

# If gaps.json does not exist or is empty → do nothing
if not gaps_file.exists() or gaps_file.stat().st_size == 0:
    print("No gaps.json or file is empty — skipping TODO injection")
    exit(0)

try:
    data = json.loads(gaps_file.read_text())
except json.JSONDecodeError:
    print("Invalid JSON in gaps.json — skipping TODO injection")
    exit(0)

# If no gaps → do nothing
if not data.get("gaps"):
    print("No gaps found — nothing to inject")
    exit(0)

for gap in data["gaps"]:
    file_path = Path(gap.get("file", ""))
    if not file_path.exists():
        continue

    lines = file_path.read_text().splitlines()
    line_no = max(0, min(len(lines), gap.get("line", 1) - 1))

    todo = f"# TODO (AI REVIEW - {gap.get('severity', 'minor')}): {gap.get('message', '')}"
    lines.insert(line_no, todo)

    file_path.write_text("\n".join(lines))

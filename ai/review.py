import os
import json
import subprocess
from pathlib import Path
from groq import Groq

# -------------------------------
# Config
# -------------------------------
MODEL = "llama-3.1-8b-instant"
MAX_CHARS = 12000
OUTPUT_FILE = "gaps.json"

client = Groq(api_key=os.environ["GROQ_API_KEY"])


# -------------------------------
# Utilities
# -------------------------------
def get_changed_files():
    """
    Return a list of files changed in the last commit.
    """
    result = subprocess.run(
        ["git", "diff", "--name-only", "HEAD~1"],
        capture_output=True,
        text=True,
        check=False,
    )

    files = []
    for f in result.stdout.strip().split("\n"):
        if (
            f.endswith(".py")
            and not f.startswith(".github/")
            and not f.startswith("ai/")
            and Path(f).exists()
        ):
            files.append(f)

    return files


def read_files(files):
    """
    Read file contents with headers, capped by MAX_CHARS.
    """
    content = ""
    for path in files:
        try:
            text = Path(path).read_text(encoding="utf-8", errors="ignore")
            block = f"\nFILE: {path}\n{text}\n"
            if len(content) + len(block) > MAX_CHARS:
                break
            content += block
        except Exception:
            continue
    return content.strip()


# -------------------------------
# Main Review Logic
# -------------------------------
def run_review():
    changed_files = get_changed_files()

    if not changed_files:
        with open(OUTPUT_FILE, "w") as f:
            json.dump({"gaps": []}, f)
        return

    code_context = read_files(changed_files)

    prompt = f"""
You are a senior backend engineer performing a STRICT code review.

ABSOLUTE RULES:
- DO NOT explain anything
- DO NOT rewrite code
- DO NOT add markdown
- DO NOT include commentary
- OUTPUT VALID JSON ONLY
- If no issues exist, output: {{ "gaps": [] }}

TASK:
Identify logical gaps, missing validations, security issues,
authorization issues, error-handling flaws, or design problems.

Each gap MUST include:
- file
- line (approximate if needed)
- issue (short, precise)

CODE:
{code_context}
"""

    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
    )

    raw = response.choices[0].message.content.strip()

    try:
        data = json.loads(raw)
        if "gaps" not in data:
            raise ValueError("Missing gaps key")
    except Exception:
        data = {"gaps": []}

    with open(OUTPUT_FILE, "w") as f:
        json.dump(data, f, indent=2)


if __name__ == "__main__":
    run_review()

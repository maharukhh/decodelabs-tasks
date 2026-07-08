"""
test_runner.py
---------------
Runs the Project 1 extraction prompt against every file in test_cases/,
calls the Claude API at temperature 0, and checks the output against
expected_outputs.json.

Setup:
    pip install anthropic --break-system-packages
    export ANTHROPIC_API_KEY="your-key-here"

Run:
    python3 test_runner.py
"""

import json
import os
import sys
from pathlib import Path

try:
    import anthropic
except ImportError:
    sys.exit("Please run: pip install anthropic --break-system-packages")

BASE_DIR = Path(__file__).parent
PROMPT_TEMPLATE = (BASE_DIR / "prompt.txt").read_text()
EXPECTED = json.loads((BASE_DIR / "expected_outputs.json").read_text())
TEST_DIR = BASE_DIR / "test_cases"

client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from env

MODEL = "claude-sonnet-4-6"


def run_test(test_name: str, raw_text: str) -> dict:
    prompt = PROMPT_TEMPLATE.replace("{RAW_USER_DATA}", raw_text)

    response = client.messages.create(
        model=MODEL,
        max_tokens=500,
        temperature=0,  # Pillar 1: deterministic output
        messages=[{"role": "user", "content": prompt}],
    )

    raw_output = response.content[0].text.strip()

    # Strip accidental markdown fences just in case
    if raw_output.startswith("```"):
        raw_output = raw_output.strip("`")
        if raw_output.lower().startswith("json"):
            raw_output = raw_output[4:].strip()

    try:
        parsed = json.loads(raw_output)
    except json.JSONDecodeError:
        return {"raw_output": raw_output, "parsed": None, "error": "Invalid JSON"}

    return {"raw_output": raw_output, "parsed": parsed, "error": None}


def grade(test_name: str, result: dict) -> bool:
    expected = EXPECTED[test_name]
    parsed = result["parsed"]

    if parsed is None:
        print(f"  ❌ FAILED TO PARSE JSON: {result['raw_output'][:200]}")
        return False

    passed = True
    for key in ["customer_name", "order_number", "complaint_type", "contact_phone"]:
        exp_val = expected.get(key)
        got_val = parsed.get(key)
        if str(exp_val).lower() != str(got_val).lower():
            print(f"  ⚠️  {key}: expected {exp_val!r}, got {got_val!r}")
            passed = False

    # severity is fuzzy-graded: allow +/-1 from expected
    exp_sev = expected.get("severity_level")
    got_sev = parsed.get("severity_level")
    if exp_sev is not None and got_sev is not None:
        if abs(int(exp_sev) - int(got_sev)) > 1:
            print(f"  ⚠️  severity_level: expected ~{exp_sev}, got {got_sev}")
            passed = False

    return passed


def main():
    test_files = sorted(TEST_DIR.glob("*.txt"))
    if not test_files:
        sys.exit("No test files found in test_cases/")

    results_summary = []
    for f in test_files:
        test_name = f.stem
        raw_text = f.read_text()
        print(f"\n▶ Running {test_name} ...")
        result = run_test(test_name, raw_text)
        ok = grade(test_name, result)
        status = "✅ PASS" if ok else "❌ FAIL"
        print(f"  Output: {result['raw_output']}")
        print(f"  Result: {status}")
        results_summary.append((test_name, ok))

    print("\n" + "=" * 40)
    print("SUMMARY")
    print("=" * 40)
    for name, ok in results_summary:
        print(f"  {'✅' if ok else '❌'}  {name}")

    passed_count = sum(1 for _, ok in results_summary if ok)
    print(f"\n{passed_count}/{len(results_summary)} tests passed.")


if __name__ == "__main__":
    main()

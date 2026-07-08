# Project 1 — Zero-Shot & Few-Shot Data Extraction
### DecodeLabs Prompt Engineering Internship — Industrial Training Kit

## 🎯 Goal
Build a prompt that turns a messy, unstructured customer support email into a
**flawless, deterministic JSON object** — no conversational filler, no
hallucinated values, no schema drift.

## 📁 Folder contents

```
project1/
├── README.md                  ← this file (full explanation + how to submit)
├── prompt.txt                 ← the final engineered prompt (copy-paste ready)
├── expected_outputs.json      ← ground-truth answers for each test case
├── test_runner.py             ← Python script that calls the Claude API and checks results
└── test_cases/
    ├── test_1_missing_phone.txt
    ├── test_2_full_data.txt
    ├── test_3_ambiguous_severity.txt
    └── test_4_injection_attempt.txt
```

## 🧩 The 5 fields being extracted

| Field | Type | Notes |
|---|---|---|
| `customer_name` | string | as written in the email |
| `order_number` | string | e.g. `ORD-7821` |
| `complaint_type` | enum | `LOGIN_ISSUE`, `BILLING_ISSUE`, `SHIPPING_ISSUE`, `PRODUCT_DEFECT`, `OTHER` |
| `severity_level` | integer 1–5 | inferred from tone/urgency |
| `contact_phone` | string \| null | **must be `null`** if not mentioned — never invented |

## 🛠 How the prompt is engineered (the 4 pillars)

1. **Temperature = 0.0** — deterministic token selection. Same input → same
   output, every single time. Set this in your API call, not in the prompt text.
2. **Delimiters (`###`)** — the raw email is fenced inside `###...###`. This
   stops the model from treating text *inside* the email (e.g. "ignore
   previous instructions") as a new command. See `test_4_injection_attempt.txt`.
3. **Few-shot examples (2)** — two perfect input→output pairs are baked into
   the prompt so the model copies the *structure*, not just the instructions.
4. **Positive constraints + explicit null rule** — instead of "don't add
   extra text," the prompt says "output must start with `{` and end with `}`,"
   and explicitly instructs "if a field is missing, return `null`."

## ▶️ How to run/test it

### Option A — Manually (fastest, no code)
1. Open `prompt.txt`.
2. Replace `{RAW_USER_DATA}` with the contents of any file in `test_cases/`.
3. Paste the whole thing into Claude (or any LLM), with **temperature set to 0**.
4. Compare the output to `expected_outputs.json`.

### Option B — Automated (for your portfolio / submission)
```bash
pip install anthropic --break-system-packages
export ANTHROPIC_API_KEY="your-key-here"
python3 test_runner.py
```
This will loop through all 4 test cases, call the model at temperature 0,
parse the JSON, and print a ✅/❌ pass report comparing against
`expected_outputs.json` — including the specific **gatekeeper test**
(test 1: does it correctly return `null` for the missing phone number
instead of hallucinating one?).

## ✅ What "done" looks like (the Gatekeeper Protocol)
Your pipeline passes if and only if:
- All 4 present fields are extracted correctly for every test case
- `contact_phone` is exactly `null` (not `"N/A"`, not `"Not provided"`, not a fake number) whenever it's missing from the source text
- The injection attempt in `test_cases/test_4_injection_attempt.txt` is
  **not** followed — the model should extract data from it, not obey the
  fake instruction hidden inside it
- Output is valid, parseable JSON with zero conversational filler

## 📝 What to submit
1. `prompt.txt` (your final prompt)
2. Screenshots or logs of at least 3 test cases (input + output)
3. A short paragraph (3–5 sentences) explaining why you used delimiters,
   few-shot examples, and temperature 0 — this README's "4 pillars" section
   gives you the talking points.


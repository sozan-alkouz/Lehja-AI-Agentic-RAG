# LehjaAI — Token-level Precision, Recall, and F1
# Reproducible implementation used for the competition evaluation.
#
# Definition:
#   Precision = overlapping tokens / response tokens
#   Recall    = overlapping tokens / reference tokens
#   F1        = harmonic mean of precision and recall
#
# Important:
# - Comparison is against the Reference Answer.
# - Text is lowercased.
# - Unicode punctuation is replaced with spaces.
# - Whitespace is normalized.
# - Repeated tokens are counted (multiset overlap).
# - No Arabic letter normalization is applied (e.g., أ is NOT changed to ا).
# - Per-item scores are calculated first, then macro-averaged.
# - Truly blank/unrecorded rows are excluded from the aggregate.
# - An explicit "NO OUTPUT" response is retained and scored as 0.

import re
import unicodedata
from collections import Counter

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------
# 1. Configuration
# ---------------------------------------------------------------------
INPUT_FILE = "LehjaAI_RAG_NoRAG_Evaluation_Competition_Final.xlsx"

# The cleaned workbook may use "Results"; older versions used "Results_Template".
PREFERRED_SHEETS = ["Results", "Results_Template"]

REFERENCE_COL = "Reference_Answer"
NO_RAG_COL = "Without_RAG_Response"
RAG_COL = "With_RAG_Response"

EXPLICIT_NO_OUTPUT = {
    "no output",
    "no_output",
    "no response",
}


# ---------------------------------------------------------------------
# 2. Token normalization
# ---------------------------------------------------------------------
def normalize_tokens(text):
    """
    Normalize text exactly for the token-overlap metric.

    Steps:
      1) lowercase
      2) replace every Unicode punctuation character with a space
      3) collapse repeated whitespace
      4) split on whitespace

    Arabic letters are intentionally NOT normalized.
    """

    if pd.isna(text):
        return None  # truly missing/unrecorded value

    text = str(text).strip()

    if text == "":
        return None  # truly missing/unrecorded value

    # Explicit experimental no-output is not treated as missing.
    if text.lower() in EXPLICIT_NO_OUTPUT:
        return []

    text = text.lower()

    # Unicode-aware punctuation removal.
    # Categories beginning with "P" include Arabic and English punctuation.
    text = "".join(
        " " if unicodedata.category(ch).startswith("P") else ch
        for ch in text
    )

    text = re.sub(r"\s+", " ", text).strip()

    return text.split() if text else []


# ---------------------------------------------------------------------
# 3. Per-item token Precision / Recall / F1
# ---------------------------------------------------------------------
def token_prf1(reference, response):
    """
    Return (precision, recall, f1).

    Repeated tokens are counted using multiset intersection.
    Example:
        reference = ["a", "a", "b"]
        response  = ["a", "b", "b"]
        overlap   = 2
    """

    ref_tokens = normalize_tokens(reference)
    pred_tokens = normalize_tokens(response)

    # Truly missing/unrecorded values are marked None so they can be
    # transparently excluded from the historical aggregate.
    if ref_tokens is None or pred_tokens is None:
        return None

    # Explicit NO OUTPUT (or an empty token sequence) receives zero.
    if len(ref_tokens) == 0 or len(pred_tokens) == 0:
        return 0.0, 0.0, 0.0

    ref_counts = Counter(ref_tokens)
    pred_counts = Counter(pred_tokens)

    overlap = sum((ref_counts & pred_counts).values())

    precision = overlap / len(pred_tokens)
    recall = overlap / len(ref_tokens)

    if precision + recall == 0:
        f1 = 0.0
    else:
        f1 = 2 * precision * recall / (precision + recall)

    return precision, recall, f1


# ---------------------------------------------------------------------
# 4. Load evaluation workbook
# ---------------------------------------------------------------------
xls = pd.ExcelFile(INPUT_FILE, engine="openpyxl")

sheet_name = next(
    (s for s in PREFERRED_SHEETS if s in xls.sheet_names),
    None
)

if sheet_name is None:
    raise ValueError(
        f"Could not find a results sheet. Expected one of: {PREFERRED_SHEETS}"
    )

df = pd.read_excel(
    INPUT_FILE,
    sheet_name=sheet_name,
    engine="openpyxl"
)

df.columns = [str(c).strip() for c in df.columns]

required_cols = {REFERENCE_COL, NO_RAG_COL, RAG_COL}
missing_cols = required_cols - set(df.columns)

if missing_cols:
    raise KeyError(f"Missing required columns: {sorted(missing_cols)}")


# ---------------------------------------------------------------------
# 5. Evaluate one system
# ---------------------------------------------------------------------
def evaluate_system(data, response_col):
    per_item = []

    for row_index, row in data.iterrows():
        result = token_prf1(
            row[REFERENCE_COL],
            row[response_col]
        )

        # Historical aggregate: skip only truly blank/unrecorded rows.
        if result is None:
            continue

        precision, recall, f1 = result

        per_item.append({
            "Row": row_index + 2,
            "Evaluation_ID": row.get("Evaluation_ID", ""),
            "Token_Precision": precision,
            "Token_Recall": recall,
            "Token_F1": f1,
        })

    details = pd.DataFrame(per_item)

    if details.empty:
        raise ValueError(f"No evaluable rows found for {response_col}")

    summary = {
        "N_Token_Evaluated": len(details),
        # Macro-average: average the per-item values.
        "Token_Precision": details["Token_Precision"].mean(),
        "Token_Recall": details["Token_Recall"].mean(),
        "Token_F1": details["Token_F1"].mean(),
    }

    return summary, details


no_rag_summary, no_rag_details = evaluate_system(df, NO_RAG_COL)
rag_summary, rag_details = evaluate_system(df, RAG_COL)


# ---------------------------------------------------------------------
# 6. Print results
# ---------------------------------------------------------------------
summary = pd.DataFrame([
    {"System": "Without RAG", **no_rag_summary},
    {"System": "With RAG", **rag_summary},
])

print("\nTOKEN-LEVEL OVERLAP RESULTS")
print(summary.to_string(index=False))

print("\nRounded percentages:")
for _, row in summary.iterrows():
    print(
        f"{row['System']}: "
        f"Precision={row['Token_Precision']*100:.2f}% | "
        f"Recall={row['Token_Recall']*100:.2f}% | "
        f"Token F1={row['Token_F1']*100:.2f}% | "
        f"N={int(row['N_Token_Evaluated'])}"
    )


# ---------------------------------------------------------------------
# 7. Optional reproducibility check for the historical RAG-vs-No-RAG file
# ---------------------------------------------------------------------
# These values are NOT used to calculate the metric.
# They are only assertions that confirm the implementation reproduces
# the already-reported workbook results when the same input file is used.

EXPECTED = {
    "Without RAG": {
        "Token_Precision": 0.6140228099026978,
        "Token_Recall": 0.6200606965970091,
        "Token_F1": 0.6138371584411875,
    },
    "With RAG": {
        "Token_Precision": 0.962756052141527,
        "Token_Recall": 0.962756052141527,
        "Token_F1": 0.962756052141527,
    },
}

for _, row in summary.iterrows():
    system = row["System"]

    if system in EXPECTED:
        for metric, expected_value in EXPECTED[system].items():
            if not np.isclose(
                row[metric],
                expected_value,
                rtol=0,
                atol=1e-12,
            ):
                print(
                    f"WARNING: {system} {metric} differs from the "
                    f"historical workbook: calculated={row[metric]:.12f}, "
                    f"expected={expected_value:.12f}"
                )


# ---------------------------------------------------------------------
# 8. Save item-level audit trail
# ---------------------------------------------------------------------
no_rag_details = no_rag_details.rename(columns={
    "Token_Precision": "NoRAG_Token_Precision",
    "Token_Recall": "NoRAG_Token_Recall",
    "Token_F1": "NoRAG_Token_F1",
})

rag_details = rag_details.rename(columns={
    "Token_Precision": "RAG_Token_Precision",
    "Token_Recall": "RAG_Token_Recall",
    "Token_F1": "RAG_Token_F1",
})

audit = no_rag_details.drop(columns=["Row"]).merge(
    rag_details.drop(columns=["Row"]),
    on="Evaluation_ID",
    how="outer",
    validate="one_to_one",
)

OUTPUT_FILE = "LehjaAI_Token_F1_Results.xlsx"

with pd.ExcelWriter(OUTPUT_FILE, engine="openpyxl") as writer:
    summary.to_excel(writer, sheet_name="Summary", index=False)
    audit.to_excel(writer, sheet_name="Per_Item_Token_F1", index=False)

print(f"\nSaved audit file: {OUTPUT_FILE}")

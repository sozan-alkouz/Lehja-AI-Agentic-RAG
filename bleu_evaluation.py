# LehjaAI — Reproducible BLEU Evaluation
# Compares No-RAG vs RAG using the same preprocessing and BLEU-4 settings.
# Missing/no-output responses remain in the 180-item evaluation and receive sentence BLEU = 0.

import re
import unicodedata
import numpy as np
import pandas as pd

from nltk.translate.bleu_score import sentence_bleu, corpus_bleu, SmoothingFunction


# ---------------------------------------------------------------------
# 1. Input
# ---------------------------------------------------------------------
# Place the evaluation workbook in the same folder as this notebook/script
# and change the filename below if needed.
INPUT_FILE = "LehjaAI_Evaluation.xlsx"

EVALUATION_SHEET = "Evaluation_Set"
DETAIL_SHEET = "BLEU_Detailed"


# ---------------------------------------------------------------------
# 2. Load the fixed 180-item evaluation set and recorded model responses
# ---------------------------------------------------------------------
evaluation = pd.read_excel(
    INPUT_FILE,
    sheet_name=EVALUATION_SHEET,
    engine="openpyxl"
)

responses = pd.read_excel(
    INPUT_FILE,
    sheet_name=DETAIL_SHEET,
    engine="openpyxl"
)

evaluation.columns = [str(c).strip() for c in evaluation.columns]
responses.columns = [str(c).strip() for c in responses.columns]

required_eval = {"Evaluation_ID", "Reference_Answer"}
required_resp = {
    "Evaluation_ID",
    "Without_RAG_Response",
    "With_RAG_Response",
}

missing_eval = required_eval - set(evaluation.columns)
missing_resp = required_resp - set(responses.columns)

if missing_eval:
    raise KeyError(f"Missing Evaluation_Set columns: {sorted(missing_eval)}")
if missing_resp:
    raise KeyError(f"Missing BLEU_Detailed columns: {sorted(missing_resp)}")


# ---------------------------------------------------------------------
# 3. Build the complete evaluation table
# ---------------------------------------------------------------------
evaluation["Evaluation_ID"] = evaluation["Evaluation_ID"].astype(str).str.strip()
responses["Evaluation_ID"] = responses["Evaluation_ID"].astype(str).str.strip()

evaluation = evaluation[
    evaluation["Evaluation_ID"].str.match(r"^EV-\d{3}$", na=False)
].copy()

responses = responses[
    responses["Evaluation_ID"].str.match(r"^EV-\d{3}$", na=False)
].copy()

if evaluation["Evaluation_ID"].duplicated().any():
    raise ValueError("Duplicate Evaluation_ID values found in Evaluation_Set.")

if responses["Evaluation_ID"].duplicated().any():
    raise ValueError("Duplicate Evaluation_ID values found in BLEU_Detailed.")

# Evaluation_Set is the source of truth for all 180 cases.
df = evaluation[
    ["Evaluation_ID", "Reference_Answer"]
].merge(
    responses[
        ["Evaluation_ID", "Without_RAG_Response", "With_RAG_Response"]
    ],
    on="Evaluation_ID",
    how="left",
    validate="one_to_one",
)

expected_ids = {f"EV-{i:03d}" for i in range(1, 181)}
actual_ids = set(df["Evaluation_ID"])

missing_ids = sorted(expected_ids - actual_ids)
extra_ids = sorted(actual_ids - expected_ids)

if len(df) != 180 or missing_ids or extra_ids:
    raise ValueError(
        f"Expected exactly 180 evaluation items. "
        f"Rows={len(df)}, missing={missing_ids}, extra={extra_ids}"
    )

df["_order"] = df["Evaluation_ID"].str.extract(r"(\d+)")[0].astype(int)
df = df.sort_values("_order").drop(columns="_order").reset_index(drop=True)


# ---------------------------------------------------------------------
# 4. Text normalization
# ---------------------------------------------------------------------
ARABIC_DIACRITICS = re.compile(
    r"[\u0617-\u061A\u064B-\u0652\u0670\u06D6-\u06ED]"
)

NO_OUTPUT_VALUES = {
    "",
    "no output",
    "no_output",
    "no response",
    "none",
    "null",
    "nan",
}


def normalize_text(text):
    """Apply the same light normalization to references and hypotheses."""
    if pd.isna(text):
        return ""

    text = str(text).strip()

    if text.lower() in NO_OUTPUT_VALUES:
        return ""

    text = unicodedata.normalize("NFKC", text)

    # Arabic normalization
    text = re.sub(ARABIC_DIACRITICS, "", text)
    text = text.replace("ـ", "")
    text = re.sub(r"[أإآٱ]", "ا", text)
    text = text.replace("ى", "ي")

    # English normalization
    text = text.lower()

    # Whitespace
    text = re.sub(r"\s+", " ", text).strip()

    return text


def tokenize(text):
    """Tokenize words/numbers and keep punctuation as separate tokens."""
    text = normalize_text(text)
    if not text:
        return []
    return re.findall(r"\w+|[^\w\s]", text, flags=re.UNICODE)


# ---------------------------------------------------------------------
# 5. BLEU configuration
# ---------------------------------------------------------------------
# BLEU-4 with equal n-gram weights.
BLEU_WEIGHTS = (0.25, 0.25, 0.25, 0.25)

# Same smoothing method for both systems.
SMOOTHING = SmoothingFunction().method3


# ---------------------------------------------------------------------
# 6. Calculate BLEU
# ---------------------------------------------------------------------
def evaluate_system(response_column):
    sentence_scores = []
    corpus_references = []
    corpus_hypotheses = []
    detailed_rows = []
    no_output_count = 0

    for _, row in df.iterrows():
        ev_id = row["Evaluation_ID"]
        reference_tokens = tokenize(row["Reference_Answer"])
        hypothesis_tokens = tokenize(row[response_column])

        if not reference_tokens:
            raise ValueError(f"Empty reference answer for {ev_id}")

        if not hypothesis_tokens:
            # A missing/no-output response remains in the evaluation.
            sentence_score = 0.0
            no_output_count += 1
        else:
            sentence_score = sentence_bleu(
                [reference_tokens],
                hypothesis_tokens,
                weights=BLEU_WEIGHTS,
                smoothing_function=SMOOTHING,
            ) * 100

        sentence_scores.append(sentence_score)
        corpus_references.append([reference_tokens])
        corpus_hypotheses.append(hypothesis_tokens)

        detailed_rows.append({
            "Evaluation_ID": ev_id,
            "Sentence_BLEU": sentence_score,
            "No_Output": int(len(hypothesis_tokens) == 0),
        })

    corpus_score = corpus_bleu(
        corpus_references,
        corpus_hypotheses,
        weights=BLEU_WEIGHTS,
        smoothing_function=SMOOTHING,
    ) * 100

    return {
        "N": len(df),
        "No_Output": no_output_count,
        "Generated_Responses": len(df) - no_output_count,
        "Corpus_BLEU": float(corpus_score),
        "Mean_Sentence_BLEU": float(np.mean(sentence_scores)),
    }, pd.DataFrame(detailed_rows)


without_rag, without_detail = evaluate_system("Without_RAG_Response")
with_rag, with_detail = evaluate_system("With_RAG_Response")


# ---------------------------------------------------------------------
# 7. Results
# ---------------------------------------------------------------------
summary = pd.DataFrame([
    {"System": "Without RAG", **without_rag},
    {"System": "With RAG", **with_rag},
])

print("\nBLEU RESULTS")
print(summary.round({
    "Corpus_BLEU": 2,
    "Mean_Sentence_BLEU": 2,
}).to_string(index=False))

print(
    "\nCorpus BLEU improvement:",
    round(with_rag["Corpus_BLEU"] - without_rag["Corpus_BLEU"], 2),
    "points"
)

print(
    "Mean Sentence BLEU improvement:",
    round(
        with_rag["Mean_Sentence_BLEU"]
        - without_rag["Mean_Sentence_BLEU"],
        2
    ),
    "points"
)


# ---------------------------------------------------------------------
# 8. Save reproducible outputs
# ---------------------------------------------------------------------
without_detail = without_detail.rename(columns={
    "Sentence_BLEU": "Without_RAG_Sentence_BLEU",
    "No_Output": "Without_RAG_No_Output",
})

with_detail = with_detail.rename(columns={
    "Sentence_BLEU": "With_RAG_Sentence_BLEU",
    "No_Output": "With_RAG_No_Output",
})

per_item = without_detail.merge(
    with_detail,
    on="Evaluation_ID",
    how="inner",
    validate="one_to_one",
)

OUTPUT_FILE = "LehjaAI_BLEU_Evaluation_Results.xlsx"

with pd.ExcelWriter(OUTPUT_FILE, engine="openpyxl") as writer:
    summary.to_excel(writer, sheet_name="BLEU_Summary", index=False)
    per_item.to_excel(writer, sheet_name="Per_Item_BLEU", index=False)

print(f"\nSaved: {OUTPUT_FILE}")

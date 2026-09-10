# Lehja-AI-Agentic-RAG

An agentic Retrieval-Augmented Generation (RAG) platform for teaching Levantine Arabic to non-native speakers.

## Project Overview

This project presents a web-based learning platform for teaching Levantine Arabic using Retrieval-Augmented Generation (RAG).

The system uses:
- n8n for workflow orchestration
- BGE-M3 for embeddings
- ChromaDB as the vector database
- GPT-5 mini as the main language model
- A decision agent for selecting the next learning action

The platform includes:
- Placement Test
- Learning Mode
- Interactive Question Mode
- Pre-test and Post-test assessment
- Micro-level quizzes

Both Learning Mode and Interactive Question Mode use the shared RAG pipeline to retrieve relevant Levantine Arabic content from the knowledge base.

## Live Platform

The learning platform is available at:

https://lehja.169.58.245.203.sslip.io/

## Research

This repository accompanies the research paper:

**Designing an Agentic AI System for Teaching the Levantine Arabic Dialect to Non-Native Speakers**

University of Jordan.

The research evaluates:
- GPT-5 mini with and without RAG
- Different prompting strategies
- Multiple language models under the same RAG framework
- Retrieval performance and response quality
- User learning progress and satisfaction

## n8n Workflows

The repository includes sanitized public versions of the main n8n workflows used in the project.

### `platform_workflow_public.json`

Contains the workflow used to support the learning platform, including the placement process, learning sessions, quizzes, pre-test/post-test assessment, RAG retrieval, and the learning decision agent.

### `model_comparison_rag_workflow_public.json`

Contains the RAG-based experimental workflow used for model comparison and RAG testing.

The same general RAG workflow structure was reused and adjusted during the experiments to evaluate GPT-5 mini, Gemini, and Qwen under comparable settings.

The workflow includes:
- BGE-M3 embeddings
- ChromaDB retrieval
- Top-5 retrieval
- CRC prompting
- Language-model generation
- Experimental output storage

Because the experimental workflow was iteratively modified during the study, a separate archived n8n file was not saved for every individual experimental run. The paper reports the configuration used for each experiment.

### `without_rag_workflow_public.json`

Contains the evaluation workflow used for the Without-RAG condition.

In this workflow, GPT-5 mini answers the evaluation questions using its internal knowledge without retrieved records or external RAG context.

### Public Workflow Note

The uploaded workflow files are sanitized versions prepared for public reproducibility.

Credential references, private instance identifiers, and private Google Drive or Google Sheets identifiers were removed or replaced with placeholders.

Users importing the workflows must configure their own:
- OpenAI credentials
- Google Drive / Google Sheets credentials
- ChromaDB connection
- Ollama connection
- Required file, sheet, and webhook identifiers

## Python Translation Script

The repository includes `translate_missing_english.py`, which was used during dataset preparation to fill missing English translations.

The script:
- Reads the Excel dataset
- Checks the `English` column
- Translates only rows with missing English values
- Uses `deep-translator` with Google Translate
- Saves progress automatically to `done_translated.xlsx`

## Evaluation Scripts

The repository also includes Python scripts used for automatic evaluation.

### `bleu_evaluation.py`

Calculates BLEU scores for the fixed RAG vs. Without-RAG evaluation set using the same text preprocessing and BLEU-4 configuration for both systems.

The script:
- Uses the same reference answers for both systems
- Evaluates the full 180-item test set
- Keeps no-output responses in the evaluation with a score of zero
- Calculates corpus BLEU and mean sentence-level BLEU
- Saves detailed per-item results

### `token_f1_evaluation.py`

Calculates token-level Precision, Recall, and F1 between generated responses and reference answers.

The script:
- Performs token-level overlap comparison
- Calculates Precision, Recall, and F1 for each response
- Uses multiset token overlap
- Retains explicit no-output responses with a score of zero
- Reports macro-averaged Token Precision, Recall, and F1
- Saves item-level evaluation results

## Installation

Install the required Python packages using:

```bash
pip install -r requirements.txt
```

The required packages include:
- pandas
- numpy
- openpyxl
- deep-translator
- nltk

## Running the Translation Script

Place the dataset file in the same folder as the script and name it:

```text
done.xlsx
```

Then run:

```bash
python translate_missing_english.py
```

## Repository Files

```text
Lehja-AI-Agentic-RAG/
├── README.md
├── requirements.txt
├── translate_missing_english.py
├── bleu_evaluation.py
├── token_f1_evaluation.py
├── platform_workflow_public.json
├── model_comparison_rag_workflow_public.json
└── without_rag_workflow_public.json
```

## Reproducibility

The public files are provided to document the main implementation and experimental workflows described in the research paper.

Private credentials and service-specific identifiers are not included in the public repository.

External datasets and experimental result files are provided separately through the supplementary materials link.

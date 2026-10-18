# SANAD VLM research

Status: see LOCAL_VLM.md for the integrated CPU PaddleOCR-VL and Gemma pipeline. There is no trained SANAD checkpoint or measured ministry-document benchmark. The Gemma 4 E2B candidate below remains a separate research experiment.

The target is faithful Arabic judicial-document transcription with source-linked regions, reading order,
tables, handwriting, stamps and human approval. A fluent answer is not evidence of faithful transcription.

## Candidate models

- PaddleOCR-VL 1.6 full layout-and-recognition pipeline: existing SANAD adapter.
- Small Google model: `google/gemma-4-E2B-it`, initial research candidate following the user's request.
  Its E2B name describes effective size; do not infer weight memory from that name.
  This is a general multimodal model, not a validated Arabic judicial OCR model.

These are separate model families. Compare them independently first. Train SANAD adapters against each
base separately; do not average their weights. Potential later distillation uses reviewed teacher
transcriptions as data, subject to the applicable model and dataset licenses.

## Run local baselines

Provision models on approved hardware first. Record the exact weight commit/checksum, package versions,
license and download source. The Gemma loader only reads local files. Paddle's upstream pipeline can
download missing assets, so pre-provision its caches and enforce network isolation for an offline run.
The supplied revision label is operator metadata, not an automated checksum verification.

Install the base package and the optional backend in a compatible Python environment:

```powershell
python -m pip install -e ".[dev,gemma]"
# For Paddle, separately install the appropriate PaddlePaddle runtime and .[paddle].
```

Create a UTF-8 JSONL manifest. Paths are relative to the manifest. Each row is a page or an explicitly
prepared crop, with reviewed text in logical reading order. Crops from the same document share its ID.
Blank ground truth is allowed for blank-image evaluation. Keep document IDs stable across scans.

```json
{"id":"doc001-p1","document_id":"doc001","split":"dev","image":"images/doc001-p1.png","text":"نص مراجع","reviewed":true}
```

The validator checks all splits before inference and rejects duplicate IDs, unreviewed text,
documents spanning splits and byte-identical images spanning splits. Near-duplicate scan detection
and grouping related document versions still require dataset curation.

```powershell
python -m sanad.research data/research/manifest.jsonl --engine gemma --model-dir C:/models/gemma-4-E2B-it --revision EXACT_WEIGHT_COMMIT --output data/research/gemma-dev.jsonl
python -m sanad.research data/research/manifest.jsonl --engine paddleocr_vl --revision EXACT_WEIGHT_COMMIT --output data/research/paddle-dev.jsonl
```

Outputs contain run metadata, image hashes, separate raw predictions and micro-averaged CER/WER,
both literal and NFC-only, plus exact transcript match. Arabic letters, diacritics and digit forms
are never folded. Rates with no reference units are null; insertion counts are still reported.
CER may exceed 1. Gemma token-limit hits are flagged. Existing output files are never overwritten.
An interrupted run retains partial evidence and has no final metrics record.

This runner evaluates transcription only. It does not claim layout, table or critical-field accuracy.
Gemma text is not assigned fabricated bounding boxes or recognition confidence and is not registered
as a production engine. The existing SANAD review workflow remains the path to approved content.

## Building the specialized model

Public-source intake and the first pinned sample are documented in [PUBLIC_DATA.md](PUBLIC_DATA.md).

1. Curate authorized public/synthetic and institutional examples with licenses/provenance. Group by
   document before splitting; freeze test data. Independently review the evaluation transcription.
2. Run both baselines on dev data, stratified by printed/handwritten/mixed, quality and document type.
   Inspect omissions, hallucinations, names, case numbers, dates and RTL ordering. Measure latency
   and GPU memory on the actual target hardware; these measurements are not implemented here.
3. Fine-tune separate candidate adapters on reviewed train data, initially parameter-efficient tuning
   where the selected runtime supports it. Choose crop resolution, target modules, batch size and
   precision after a hardware smoke test. Do not train on unreviewed model-generated labels.
4. Use dev results to select the model and any routing policy. Test the selected configuration once
   on frozen held-out data; add source-location, table and critical-field evaluation before deployment.
5. Publish a versioned SANAD checkpoint/adapter with its base revision, dataset lineage, license,
   evaluation evidence and limitations. A two-model experimental pipeline alone is not a new VLM.

Training is pending an authorized reviewed corpus and a verified GPU/runtime. Refer to LOCAL_VLM.md for operational inference verification; the Gemma 4 E2B research candidate has not been executed. No accuracy improvement, hardware fit or production readiness is claimed.

## Official references

- https://huggingface.co/PaddlePaddle/PaddleOCR-VL-1.6
- https://huggingface.co/google/gemma-4-E2B-it
- https://ai.google.dev/gemma/docs/get_started

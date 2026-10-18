# SANAD local document VLM

This is an application pipeline around existing models, not a newly trained SANAD
checkpoint. Transcriptions and extracted fields still require human review.

## Components

1. **PP-DocLayoutV3** detects page blocks and reading order.
2. **PaddleOCR-VL-1.6-0.9B** reads the detected image blocks using llama.cpp on CPU.
   Text, table markup and seal text remain in the private raw result. Positions
   use original image pixels; rotation and unwarping are disabled.
3. Canonical source-linked regions enter the existing versioned review workflow.
   VLM regions require review; no recognition-confidence percentage is fabricated.
   When a prior Arabic OCR version exists for the same source, overlapping text is
   attached as an explicitly attributed alternative. It never replaces VLM text.
4. **Gemma 3 4B**, served locally by Ollama, proposes document fields from saved
   text. A validator accepts only exact literal spans with an existing source
   region. Invalid proposals are retained as rejected diagnostics. Grounding
   proves where text occurs, not whether its interpretation or OCR is correct.
5. Proposals are separate from approved content and tied to the exact page
   version. Editing/reprocessing the page hides the old proposals. Each run
   records the Gemma model digest, prompt version and source version.

Gemma 1B was tested during setup and produced a poor Arabic field interpretation;
it is not the default. Small Gemma 4 E2B remains a separate research candidate.
Neither model's weights are averaged or automatically trained from predictions.

## Windows CPU setup

The supplied `PaddleOCR-main/.venv` remains isolated from the API environment.

```powershell
py -3.11 -m venv .venv
py -3.11 -m venv PaddleOCR-main/.venv
.venv/Scripts/python.exe -m pip install -e ".[dev]"
PaddleOCR-main/.venv/Scripts/python.exe -m pip install paddlepaddle==3.3.0 -e PaddleOCR-main "paddlex[ocr,genai-client]==3.7.2"
.venv/Scripts/python.exe scripts/provision_vlm.py
ollama pull gemma3:4b
.venv/Scripts/python.exe -m uvicorn sanad.api:create_app --factory --host 127.0.0.1 --port 8000
```

Provisioning pins the Paddle GGUF revision `511b09642bb324401f15f97cc23bc67e8f0a291d`,
layout revision `241f8bdfc77a7c7bee915a5057aaee58c235a8d3`, and llama.cpp build `b11717`.
Large model downloads support resuming and are checked against official LFS SHA256
values. `data/models/manifest.json` records artifact URLs, hashes and sizes.
Downloads fetch weights only; document processing uses loopback services.

In **System → SANAD model controls**, start VLM and wait for Ready. Select
PaddleOCR-VL beside Extract page. The old Arabic recognizer remains an explicit
comparison option; VLM failures never silently select it. On-demand workers
serialize OCR, VLM and Gemma tasks. CPU VLM has a 30-minute per-page bound.

Open **Document understanding → Extract fields** after saving text changes.
Gemma is unloaded after each extraction to release RAM. Page-layout SVG previews
use block coordinates; line positions inside multiline VLM blocks are approximate.
The original typeface, graphics and handwriting are not reconstructed.

Services bind to 127.0.0.1. The managed VLM service uses a private per-process API key. The API starts/stops only its owned llama.cpp process;
it refuses an occupied port. Shutdown terminates that owned process. State is
checked from service health, not assumed from installed files. Model lifecycle
requires admin_ops; extraction and page data retain role/organization checks.

`SANAD_PADDLE_PYTHON` overrides the Paddle interpreter. `SANAD_GEMMA_MODEL`
selects another locally installed Ollama model. To run CLI evaluation against the managed service, set the same `SANAD_VLM_INTERNAL_KEY` in the API and evaluation environments before starting them; otherwise the API generates a private key for its own worker. `SANAD_ENGINE` controls the
default queue engine (`paddleocr_vl`); requests can explicitly select a real engine.

## Reviewed data and specialization

```powershell
.venv/Scripts/python.exe scripts/export_approved_dataset.py data/research/approved-v1
```

Only latest approved, non-demo pages with resolved textual regions are exported.
Image hashes group duplicate sources into the same deterministic split. The
manifest includes source hashes, region coordinates and approval version IDs.
This export does not start training. Use `sanad.research` for baseline evaluation
after reviewing split balance and document-family leakage. Adapter training and
release of a SANAD checkpoint still need a reviewed corpus and verified training
compute; no training success or accuracy gain is inferred from integration tests.

Official references:

- https://github.com/PaddlePaddle/PaddleOCR/blob/main/docs/version3.x/pipeline_usage/PaddleOCR-VL.en.md
- https://huggingface.co/PaddlePaddle/PaddleOCR-VL-1.6-GGUF
- https://huggingface.co/PaddlePaddle/PP-DocLayoutV3
- https://ai.google.dev/gemma/docs/core/model_card_3
- https://ollama.com/library/gemma3


The repository also includes a Git LFS model bundle. See weights/README.md to restore
weights locally instead of downloading them again. This does not publish document data.

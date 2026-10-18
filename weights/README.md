# Bundled model weights

These are upstream model weights, not a trained SANAD checkpoint. Large artifacts
are stored in Git LFS. The Gemma 4B language-model blob is split into parts smaller
than GitHub Free's per-object limit. `index.json` records every part and complete
blob hash; `upstream-manifest.json` records the pinned Paddle download sources.

```powershell
git lfs install
git lfs pull
python scripts/restore_weights.py --verify-only
python scripts/restore_weights.py
```

Restoration places PaddleOCR-VL/layout assets in `data/models`, Arabic OCR models
in `~/.paddlex/official_models`, and Gemma blobs/manifest in `~/.ollama/models`.
Existing files with different hashes are refused. Read `docs/LOCAL_VLM.md` to
install runtimes and obtain the pinned llama.cpp binary. Runtime executables,
uploaded documents, databases, generated transcriptions and credentials are not
part of this weight bundle.

- PaddleOCR-VL 1.6 GGUF + projector: PaddlePaddle, pinned revision in manifest.
- PP-DocLayoutV3: PaddlePaddle, pinned revision in manifest.
- Arabic PP-OCRv5 mobile recognizer and PP-OCRv5 server detector: PaddlePaddle.
- Gemma 3 4B Q4_K_M and vision projector: Google model, distributed through the
  Ollama `gemma3:4b` registry tag. Its exact content-addressed layers are retained.

Paddle artifacts are subject to the accompanying Apache-2.0 license. Gemma is
subject to **GEMMA-LICENSE.txt**, including its Section 3.2 use restrictions and
the Gemma Prohibited Use Policy at https://ai.google.dev/gemma/prohibited_use_policy.
Use or redistribution of the Gemma artifacts is permitted only subject to those
terms and restrictions; this repository grants no exemption from them. Subsequent
redistributions must retain the terms and NOTICE. No blanket project license
overrides these third-party model licenses.

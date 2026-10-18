# Public-data intake — 18 October 2026

This is development data for SANAD, not evidence of performance on ministry records.

## First intake

[Egyptian official documents](https://huggingface.co/datasets/mohamedwasef/egyptian-official-documents-ocr)
is the closest printed-domain candidate found. Its annotation license is CC BY 4.0. Labels are
LLM-generated and spot-checked, not fully verified. Formatting includes normalized spacing and HTML
tables, so review target conventions before comparing against SANAD's literal transcription prompt.

The upstream test shard and README are saved under
`data/research/sources/egyptian-official-documents-ocr/`, pinned to revision
`ad2c38f5809d58d4ab475df26fd2bf750ab063a3`. `provenance.json` records URLs and SHA-256 hashes.
Keep these examples reserved for evaluation; independently correct labels before running evaluation.

```powershell
python -m pip install pyarrow
python scripts/prepare_egyptian_sample.py data/research/sources/egyptian-official-documents-ocr/test-00000-of-00001.parquet data/research/egyptian-eval
```

The importer verifies the exact source hash, preserves publisher metadata and marks every example
`reviewed=false`. The research runner will reject these until independently reviewed. Do not bulk
flip that field. Preserve originals and put corrected text in a separate reviewed manifest.
Dataset bytes live under ignored `data/`; keep attribution with any reused annotations.

## Additional sources to acquire

- [Synthetic Arabic scans](https://huggingface.co/datasets/loay/arabic-ocr-synthetic-scans-faker-300k):
  publisher lists CC BY 4.0, roughly 300k generated pages. Useful for printed OCR diversity; text
  uses structural tags and Faker-generated content. Strip/convert tags explicitly before literal-text
  scoring. Not a source of realistic legal reasoning or real handwriting. Not downloaded.
- [Muharaf — official repository](https://github.com/MehreenMehreen/muharaf) and
  [public release](https://zenodo.org/records/11492215): 1,216 public handwritten pages with annotations;
  CC BY-NC-SA 4.0. Keep separate from unrestricted training until intended-use compatibility is
  established. Restricted pages are excluded. Not downloaded.
- [Humans in the Loop Arabic documents](https://humansintheloop.org/resources/datasets/arabic-documents-ocr-dataset/):
  publisher lists 10k images and CC0; includes official documents and administrative forms. Access
  requires a form. Annotation description promises transcribed titles and line boxes, so inspect
  body-text coverage before treating it as transcription training data. No form submitted.
- [KHATT — official distributor](https://catalog.ldc.upenn.edu/LDC2015T23): modern handwriting;
  requires its distribution agreement. Do not infer dataset rights from an MIT-licensed model or mirror.
  Not downloaded.

## Next preparation

Review a small document-disjoint selection, including numbers, stamps and tables. Use the printed
sample to exercise the data pipeline while training hardware is unavailable. Acquire handwriting
only under compatible terms, then add separate printed/handwritten/mixed strata. Public legal text
does not substitute for court case files, marginal notes, signatures or ministry-specific layouts.

# SANAD control workspace

الواجهة عربية افتراضياً، مع مفتاح تبديل إلى الإنجليزية يحفظ اختيار اللغة محلياً. يتبدل اتجاه التخطيط بين RTL وLTR تلقائياً. تشمل الترجمة القوائم والنماذج وحالات
المعالجة ورسائل التحقق وسجل الإصدارات وشاشة النظام. تظل أسماء الملفات ومعرّفات النماذج
ونصوص المستندات وملاحظات الناشر بلغتها الأصلية. لا تُطبّع حروف النص أو أرقامه عند العرض أو الحفظ.
إحداثيات مربعات المناطق تُحسب بالنسبة إلى الصورة الأصلية ولا تُعكس مع اتجاه الواجهة.

Start with the existing editable package and development database:

```powershell
.\.venv\Scripts\python.exe -m uvicorn sanad.api:create_app --factory --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000/. Local development opens automatically as **Super admin** with all
workflow controls and access to all organizations. There is no token entry or role switching in this flow.
Uploads use the `sanad-workspace` organization automatically.

The development session uses an HTTP-only, same-site cookie provisioned through a loopback-only endpoint.
It is unavailable in secure mode or when a custom users file is configured. Those configurations retain
explicit authentication. Existing role-specific tokens remain available for API authorization tests.

The default pipeline is real Arabic PP-OCRv5 on CPU, using the supplied Paddle environment.
New image uploads start recognition automatically. **تشغيل OCR العربي** starts/repeats recognition
on the selected document, and status refreshes automatically. PaddleOCR-VL remains a separate real
adapter requiring its dependencies and a worker. The mock engine and demo-step endpoint were removed.
A missing runtime/weights blocks processing; no synthetic fallback exists.

The bridge uses `PaddleOCR-main/.venv/Scripts/python.exe` and local model caches by default. Override
with `SANAD_PADDLE_PYTHON` / `SANAD_PADDLE_MODELS`. Each page uses an isolated native subprocess
with a ten-minute timeout, four CPU threads and oneDNN disabled, as in the provided working app.
Orientation and unwarping are disabled so polygons stay in original-image coordinates. Full table
structure and handwriting performance are not established by line OCR. Processing is serialized in this
single-process local pilot. A process restart interrupts in-flight work; retry it after the lease expires.

The source viewer supports zoom and linked region selection. Unsaved transcription changes trigger
a discard prompt when navigating. Saving creates a draft, approval creates a separate immutable version,
and reopening preserves the approved version. Export is supervisor-only and reports schema rejection.
The owner schema remains provisional. Legacy synthetic versions remain traceable, but cannot be approved or exported in any environment.
Real reprocessing creates a new version and preserves the old history.

**Dataset review** reads the prepared 30-page public sample from `SANAD_DATA_DIR/research/egyptian-eval`.
It is a dev-only workbench. Compare the complete source image with the publisher transcription, correct
it, add a note, and confirm visual review. Saving writes a separate `reviewed.jsonl` with reviewer identity,
revision and previous-text history. The source `pending_review.jsonl` is preserved. Stale saves return a
conflict. No public sample was automatically marked reviewed during UI development.

Public dataset routes use an in-process writer lock and atomic file replacement: run this development
workbench with one API process. Move this store to transactional persistence before multi-process use.

## Design and validation

The concept is in `docs/design/workspace-concept.png`; it was generated with the built-in ImageGen tool.
Brief: full SANAD document operations screen, forest-green navigation rail, white workspace, five workflow
stages, document list, source/transcription split, mock warning, version history and queue controls.

Design tokens: white background, #103b2e navigation/action, #edf5f1 selected rows, #dfe5e1 dividers,
Georgia title/brand, Segoe UI/Tahoma controls, 5–6 px panels and 12–26 px spacing. Responsive layouts
stack source and transcription; narrow screens use a horizontal navigation strip.

The implementation retains the concept's palette, serif title, navigation, workflow ribbon and three-column
document/source/transcription structure. Intentional functional differences: real raster documents replace
fictional PDF rows; actual region counts replace the illustrated six regions; role-gated actions replace
fictional model-configuration controls; no unimplemented pan/reset, metadata tabs or fabricated queue errors.
The queue is for the selected document. This preserves the design structure while accurately representing
backend capabilities.


## Current processing feedback

The processing panel shows the current real job first, with a concise state and actionable failure text.
Earlier attempts, including removed-engine records, are collapsed under processing history. No old audit
records are deleted. Arabic and English can be switched from the header; the choice survives reloads.
Document text and publisher notes remain unchanged when changing language.

The Windows Arabic-output failure was caused by the implicit cp1252 encoding of raw JSON writes.
Raw output is now explicitly UTF-8. The regression test simulates a cp1252 default and verifies an Arabic
round trip. Inference commits its initial run record before native execution, releasing the database write
lock; SQLite uses WAL. An independent write during inference is covered by the same regression test.


## OCR quality profile

Arabic PaddleOCR defaults to `SANAD_OCR_QUALITY=balanced`: cubic enlargement of small
images to a 1200-pixel longest side (maximum 4x), then two independent reads with
illumination correction and local contrast enhancement. Original images remain unchanged;
all detection coordinates are mapped back using actual X/Y resize factors.
Geometry-matched disagreements retain both readings. A candidate replaces the primary
only with a score margin greater than 0.08 and a length check against fragments.
Disagreements, scores below 0.8, and numeric content require human review before approval.
Scores are engine signals, not measured accuracy. Unmatched alternate detections remain
available in raw output; they are not automatically inserted into the transcription.
`SANAD_OCR_QUALITY=baseline` selects an unenhanced single read for comparison.

Compared three preparation profiles on the actual uploaded 390x512 Iraqi summons and
480x640 Yemeni memo. Illumination helped headings while contrast recovered long body
lines, motivating the combined profile. Small source pixels, stamps and handwriting still
cause errors, including high-scoring wrong words. No CER/WER or accuracy percentage is
claimed without reviewed full-page transcriptions. Enlargement cannot recover lost detail.
The UI shows source-resolution warnings, engine scores and alternate readings in both
languages. These are OCR candidates, never automatic legal-name/date corrections.


## Full-page text layout

The Full-page text button opens a side-by-side source and selectable SVG transcription.
Every nonempty OCR region is placed in its original pixel bbox; each line has independent
RTL/LTR direction. SVG fits the line to its detected width; original typography, stamps,
logos and handwriting shapes are not reconstructed. Current textarea edits are included
in the preview/download, even before saving, and the download is explicitly a preview,
not an approved delivery. Existing approval and JSON export rules remain in force.
Verified at localhost using bundled Playwright/Chrome (Browser plugin not available):
32 text elements matched the selected page, SVG download succeeded, English controls
worked, no page errors, and the dialog had no horizontal overflow at 390px.

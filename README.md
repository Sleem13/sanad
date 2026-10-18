# SANAD · سند

Current release: Arabic/English document workbench with local **PaddleOCR-VL 1.6 +
PP-DocLayoutV3**, an explicit Arabic PP-OCRv5 comparison pipeline, and **Gemma 3 4B**
for source-grounded field proposals. The app includes full-page SVG previews,
versioned review, approval and export, model controls, and approved-dataset export.

Read **[docs/LOCAL_VLM.md](docs/LOCAL_VLM.md)** for current Windows CPU setup.
Start VLM in the System panel, choose an engine beside Extract page, and process
the document. Gemma proposals reference saved text and do not approve or rewrite it.

These are upstream models integrated into SANAD, not a newly trained checkpoint.
Actual uploaded-page VLM inference and Gemma field extraction have been exercised;
small Arabic text, handwriting and stamps still produce errors and hallucinations.
All VLM text requires review. No ministry-document accuracy benchmark is claimed.

Model manifests and licenses are in **[weights/README.md](weights/README.md)**.
Large weights use Git LFS when available; they can also be downloaded with the
pinned provision script and `ollama pull gemma3:4b`. Uploaded documents, databases,
transcripts, runtime logs, credentials and virtual environments are excluded.

Run tests with `.venv/Scripts/python.exe -m pytest -q`.

<details><summary>Historical pilot setup (superseded by the local VLM guide)</summary>

واجهة عربية محلية لحفظ المستندات، والتعرف على النص، والمراجعة والاعتماد والتصدير.
**محركات حقيقية فقط:** أُزيل المحرك التجريبي ومسار تشغيله، ولا يوجد رجوع تلقائي إلى نصوص اصطناعية.

## التشغيل المحلي

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m uvicorn sanad.api:create_app --factory --host 127.0.0.1 --port 8000
```

افتح http://127.0.0.1:8000/؛ تدخل النسخة المحلية تلقائياً بصلاحيات المدير العام.
رفع صورة جديدة يبدأ التعرف الحقيقي. لإعادة التعرف اضغط **تشغيل OCR العربي**؛ تظهر حالة المهمة
وتتحدث النتائج تلقائياً. المعتمد يحتاج إلى إعادة فتحه قبل إعادة المعالجة.

المحرك الافتراضي `paddleocr_arabic` يستخدم نسخة PaddleOCR المقدمة في
`PaddleOCR-main/.venv/Scripts/python.exe` ونموذجي `PP-OCRv5_server_det` و
`arabic_PP-OCRv5_mobile_rec` من `~/.paddlex/official_models` على CPU.
يمكن تحديد مواقع أخرى باستخدام `SANAD_PADDLE_PYTHON` و`SANAD_PADDLE_MODELS`.
لا تُنزّل الأوزان تلقائياً؛ غياب البيئة أو الأوزان يوقف المهمة بوضوح.

جرى اختبار استخراج عربي فعلي عبر الواجهة على صورة اصطناعية ذات سطرين، باستخدام
PaddleOCR 3.7.0 وPaddlePaddle 3.3.0. هذا اختبار تشغيل وليس قياس دقة على أرشيف الوزارة.
الثقة المعادة من المحرك ليست نسبة دقة معتمدة. الجداول والخط اليدوي تحتاج إلى تقييم مستقل.

**PaddleOCR-VL:** محوّل حقيقي منفصل وغير مجهّز محلياً بعد. لتشغيله يلزم
`SANAD_ENGINE=paddleocr_vl` واعتمادياته وأوزانه، ثم العامل المنفصل:

```powershell
.\.venv\Scripts\python.exe -m sanad.worker
```

Gemma ما زال مشغّلاً بحثياً منفصلاً. لا توجد نسخة VLM خاصة بسند مدرّبة بعد.
الإصدارات الاصطناعية القديمة محفوظة للتتبع فقط، ولا يمكن اعتمادها أو تصديرها؛ إعادة التعرف
تنشئ إصداراً حقيقياً جديداً دون محو السجل القديم.

## المستندات

- [دليل الواجهة](docs/WORKSPACE.md)
- [التجارب والنماذج](docs/VLM_RESEARCH.md)
- [البيانات العامة](docs/PUBLIC_DATA.md)
- المعمارية والخطة وقرارات التصميم في `docs/`؛ الأقسام القديمة التي تصف المحرك التجريبي
  سجلات تاريخية، وتحل محلها سياسة المحركات الحقيقية الموصوفة هنا.

المخطط النهائي للمالك والتقييم على بيانات الوزارة ما زالا معلقين. ملفات Docker تحتاج إلى
تجهيز بيئة Paddle وأوزان متوافقة داخل الحاوية؛ لا تستخدم بيئة Windows تلقائياً.


Local PaddleOCR-VL + Gemma setup and model controls: [docs/LOCAL_VLM.md](docs/LOCAL_VLM.md).
</details>

import {language,t,registerTranslations} from '/static/i18n.js';
// UI translations only. Source text, identifiers and API enum values stay unchanged.
const labels = {
 generation_repetition:'تكرار في توليد VLM — لا تعتمد هذا النص دون مراجعة',long_vlm_block:'كتلة طويلة — تحقق من الاكتمال',
 cross_engine_disagreement:'اختلف OCR وVLM — قارن القراءتين بالأصل',
 starting:'جارٍ تحميل النموذج',stopped:'متوقف',not_provisioned:'الأوزان غير جاهزة',vlm_needs_review:'قراءة VLM تحتاج مراجعة',issuer:'الجهة المصدرة',recipient:'المرسل إليه',date:'التاريخ',reference_number:'الرقم المرجعي',person:'اسم شخص',
 ingested:'تم الاستلام',processing:'قيد المعالجة',processed:'تمت المعالجة',failed:'فشلت المعالجة',
 in_review:'قيد المراجعة',approved:'معتمد',blocked:'متوقف',partial_failure:'فشل جزئي',
 queued:'في الانتظار',running:'جارٍ التنفيذ',succeeded:'اكتمل',cancelled:'ملغى',delivered:'تم التسليم',rejected:'مرفوض',
 recognized:'تم التعرف',uncertain:'غير مؤكد',illegible:'غير مقروء',not_present:'غير موجود',
 not_processed:'لم تتم المعالجة',requires_review:'يحتاج إلى مراجعة',pending:'قيد الانتظار',
 reviewed:'تمت المراجعة',raw:'ناتج المحرك',draft:'مسودة',title:'عنوان',text:'نص',seal:'ختم',
 signature:'توقيع',stamp:'ختم',image:'صورة',figure:'شكل',chart:'رسم بياني',table:'جدول',
 header:'ترويسة',footer:'تذييل',margin_note:'ملاحظة هامشية',human_edited:'عدّله المراجع',non_text_region:'منطقة غير نصية',
 paragraph:'فقرة',body:'متن',doc_title:'عنوان المستند',paragraph_title:'عنوان فقرة',
 ocr_disagreement:'اختلفت القراءتان — راجع الأصل',numbers_need_review:'راجع الأرقام مقابل الأصل',
 low_ocr_score:'درجة المحرك منخفضة — راجع النص',low_resolution_source:'الأصل منخفض الدقة',
 table_title:'عنوان جدول',table_caption:'وصف جدول',table_footnote:'هامش جدول',
 figure_title:'عنوان شكل',figure_caption:'وصف شكل',image_caption:'وصف صورة',
 footnote:'حاشية',reference:'مرجع',formula:'معادلة',formula_number:'رقم المعادلة',
 abstract:'ملخص',content:'محتوى',number:'رقم الصفحة',header_image:'صورة الترويسة',footer_image:'صورة التذييل',
 environment:'بيئة التشغيل',engine:'محرك المعالجة',external_processing:'المعالجة الخارجية',
 database:'قاعدة البيانات',storage:'التخزين',max_upload_mb:'حد الرفع (ميغابايت)',worker:'عامل المعالجة',training:'التدريب',
 dev:'تطوير محلي',secure:'تشغيل محمي',ready:'جاهز',unavailable:'غير متاح',mock:'محرك قديم محذوف',
 paddleocr_vl_full_page:'PaddleOCR-VL · صفحة كاملة',whole_page_only:'نص الصفحة كاملة — دون مواضع أسطر مكتشفة',generation_truncated:'وصل النص إلى الحد الأقصى — تحقق من الأجزاء الناقصة',paddleocr_vl:'PaddleOCR-VL',gemma:'Gemma',
 paddleocr_arabic:'PaddleOCR العربي',
 'On-demand local OCR worker':'عامل OCR محلي يعمل عند بدء المعالجة',
 'legacy synthetic content cannot be approved; run a real OCR pipeline':'هذا ناتج قديم غير حقيقي. شغّل OCR العربي قبل الاعتماد.',
 'local Arabic PP-OCRv5 CPU runtime':'نسخة PP-OCRv5 العربية المحلية على المعالج المركزي',
 'Separate worker required; heartbeat not implemented':'يتطلب عامل معالجة منفصلاً؛ مراقبة اتصاله غير متاحة بعد',
 'adapter available; inference unverified':'المحوّل متاح؛ لم يُتحقق من الاستدلال بعد',
 'research runner only; inference unverified':'مشغّل بحثي فقط؛ لم يُتحقق من الاستدلال بعد',
 'No trained SANAD checkpoint or verified training GPU':'لا توجد نسخة مدرّبة من سند أو بطاقة رسومية متحقق منها للتدريب'
};
const enLabels={paddleocr_vl_full_page:'PaddleOCR-VL · full page',whole_page_only:'Whole-page text — no detected line positions',generation_truncated:'Output reached token limit — check for missing text',generation_repetition:'VLM repetition — review before approval',long_vlm_block:'Long block — check completeness',cross_engine_disagreement:'OCR and VLM disagree — compare with source',starting:'Loading model',stopped:'Stopped',not_provisioned:'Weights not installed',vlm_needs_review:'VLM reading needs review',issuer:'Issuer',recipient:'Recipient',date:'Date',reference_number:'Reference number',person:'Person',ocr_disagreement:'OCR readings disagree — check source',numbers_need_review:'Check numbers against source',low_ocr_score:'Low engine score — review text',low_resolution_source:'Low-resolution source',paddleocr_vl:'PaddleOCR-VL',gemma:'Gemma',succeeded:'Completed',running:'Running',in_review:'In review',not_processed:'Not processed',requires_review:'Needs review',partial_failure:'Partial failure',ready:'Ready',false:'Disabled',true:'Enabled',paddleocr_arabic:'Arabic PaddleOCR',mock:'Removed legacy engine',max_upload_mb:'Upload limit (MB)',dev:'Local development',secure:'Secure',raw:'OCR output',human_edited:'Human edited',non_text_region:'Non-text region'};
registerTranslations(Object.fromEntries(Object.entries(labels).map(([key,value])=>[value,enLabels[key]??(key.includes(' ')?key:key.replaceAll('_',' ').replace(/^./,c=>c.toUpperCase()))])));
export function label(value){return language==='ar'?(labels[value]??String(value)):(enLabels[value]??(labels[value]?t(labels[value]):String(value)));}
export function num(value){return new Intl.NumberFormat(language==='ar'?'ar-EG':'en-US').format(value);}
const errors = {
 'Start the local VLM in Model controls and wait until ready':'شغّل VLM من قسم النظام وانتظر حتى تصبح حالته جاهزاً.',
 'model worker is busy':'عامل النماذج مشغول. انتظر اكتمال المعالجة الحالية.',
 'VLM assets missing; run scripts/provision_vlm.py':'أوزان VLM غير جاهزة. أكمل تثبيتها على الخادم.',
 'Gemma is not installed; run ollama pull gemma3:4b':'نموذج Gemma غير جاهز. أكمل تثبيت gemma3:4b على الخادم.',
 'a real transcription is required':'شغّل محركاً حقيقياً لاستخراج النص أولاً.',

 'invalid or missing token':'انتهت الجلسة أو بيانات الدخول غير صحيحة. أعد تحميل الصفحة.',
 'not found':'العنصر غير موجود أو غير متاح لحسابك.',
 'not processed yet':'لم تكتمل معالجة الصفحة بعد.',
 'storage unavailable':'التخزين غير متاح حالياً.',
 'page has no content yet':'لم يتوفر محتوى الصفحة بعد.',
 'page is approved; reopen it (supervisor) before editing':'الصفحة معتمدة. أعد فتحها قبل تعديلها.',
 'concurrent edit detected':'عدّل مراجع آخر هذه الصفحة. أعد تحميلها قبل الحفظ.',
 'concurrent change detected':'تغيرت الصفحة أثناء العمل. أعد تحميلها قبل المتابعة.',
 'reason required to reopen':'أدخل سبب إعادة فتح الصفحة.',
 'page is not approved':'الصفحة غير معتمدة بعد.',
 'no review task':'لا توجد مهمة مراجعة لهذه الصفحة.',
 'page has no review task':'لا توجد مهمة مراجعة لهذه الصفحة.',
 'real Arabic OCR is not the configured engine':'محرك التعرف العربي الحقيقي غير مفعّل في إعدادات الخادم.',
 'approved page must be reopened before reprocessing':'أعد فتح الصفحة المعتمدة قبل إعادة التعرف على نصها.',
 'OCR job is already running':'تجري معالجة هذا المستند بالفعل.',
 'OCR worker is busy; try again when current processing completes':'محرك التعرف مشغول. أعد المحاولة بعد اكتمال المعالجة الحالية.',
 'only queued, running or blocked jobs can be cancelled':'يمكن إلغاء المهام المنتظرة أو الجارية أو المتوقفة فقط.',
 'job is not retryable':'هذه المهمة غير قابلة لإعادة المحاولة في حالتها الحالية.',
 'approved documents cannot be retried':'لا يمكن إعادة معالجة مستند معتمد.',
 'job must be queued':'يجب أن تكون المهمة في الانتظار.',
 'job was already claimed':'بدأ عامل آخر تنفيذ هذه المهمة.',
 'assignee must be a reviewer in the document organization':'اختر مراجعاً مسجلاً لدى جهة المستند.',
 'escalation note required':'أدخل سبب التصعيد.',
 'public dataset workbench is dev-only':'مراجعة البيانات العامة متاحة في بيئة التطوير فقط.',
 'example not found':'العينة غير موجودة.',
 'invalid image path':'مسار صورة العينة غير صالح.',
 'confirm visual review and provide a review note':'أكد مراجعة الصورة بالكامل وأضف ملاحظة المراجعة.',
 'review changed; reload before saving':'تغيرت المراجعة. أعد تحميل العينة قبل الحفظ.',
 'local development session requires a loopback connection':'افتح مساحة العمل عبر عنوان الخادم المحلي.',
 'cross-origin session request refused':'تعذّر فتح الجلسة من عنوان مختلف.',
 'content derived from the MOCK engine cannot be approved (demo approval is dev-only)':'لا يمكن اعتماد المحتوى التجريبي خارج بيئة التطوير.'
};
function arabicError(detail,status=0){
 if(typeof detail==='string'&&detail.startsWith('VLM output rejected: repetitive generation'))return 'رُفض ناتج VLM لأنه يكرر النص نفسه. لم يُحفظ كاستخراج ناجح. استخدم صورة أوضح أو أدخل النص يدوياً.';
 if(typeof detail!=='string')return 'البيانات المدخلة غير صالحة. تحقق من الحقول المطلوبة.';
 if(errors[detail])return errors[detail];
 if(/database is locked|OperationalError/.test(detail))return 'قاعدة البيانات مشغولة. انتظر اكتمال العملية الحالية ثم أعد المحاولة.';
 if(/UnicodeEncodeError/.test(detail))return 'تعذر حفظ العربية في محاولة سابقة بسبب ترميز Windows. تم إصلاح الحفظ إلى UTF-8؛ أعد المحاولة.';
 if(detail==='Paddle OCR worker failed')return 'تعذّر حفظ النتيجة سابقاً. أعد المحاولة بعد إصلاح الحفظ؛ لا حاجة لإعادة رفع الملف.';
 if(/stale (base )?version/.test(detail))return 'الإصدار المعروض قديم. أعد تحميل الصفحة قبل المتابعة.';
 if(detail.startsWith('unresolved regions:'))return 'توجد مناطق غير مؤكدة. راجع حالاتها قبل الاعتماد.';
 if(/missing permission|outside organizational scope|missing system access|job control requires/.test(detail))return 'ليس لديك صلاحية تنفيذ هذا الإجراء.';
 if(/recognized requires text/.test(detail))return 'أدخل النص أو اختر حالة «غير مقروء» أو «غير موجود» للمنطقة الفارغة.';
 if(/paddleocr|weights|hardware|CUDA|GPU|VLM endpoint/i.test(detail))return 'محرك التعرف غير جاهز. تحقق من الاعتماديات وأوزان النموذج وعتاد التشغيل.';
 if(/no approved version/.test(detail))return 'يجب اعتماد جميع صفحات المستند قبل التصدير.';
 if(/mock-engine content is not exportable/.test(detail))return 'لا يمكن تصدير محتوى المحرك التجريبي في وضع التشغيل الحالي.';
 if(/page\(s\) failed/.test(detail))return 'فشلت معالجة بعض الصفحات. راجع حالة المحرك ثم أعد المحاولة.';
 if(/empty_file/.test(detail))return 'الملف فارغ.';
 if(/file_too_large/.test(detail))return 'حجم الملف أكبر من الحد المسموح.';
 if(/too_many_pixels/.test(detail))return 'أبعاد الصورة تتجاوز الحد المسموح.';
 if(/unsupported_format/.test(detail))return 'صيغة الملف غير مدعومة. ارفع صورة PNG أو JPEG أو TIFF.';
 if(/corrupt_or_unreadable/.test(detail))return 'الملف تالف أو لا يمكن قراءة صورته.';
 return ({401:'تعذّر التحقق من الجلسة. أعد تحميل الصفحة.',403:'ليس لديك صلاحية تنفيذ هذا الإجراء.',404:'العنصر المطلوب غير موجود.',409:'تغيرت حالة العنصر. أعد تحميله قبل المتابعة.',422:'تعذّر قبول البيانات. تحقق من الحقول وحالة المستند.',503:'الخدمة غير متاحة حالياً.'})[status]??'تعذّر إتمام العملية. تحقق من اتصال الخادم وحاول مجدداً.';
}

registerTranslations(Object.fromEntries(Object.entries(errors).map(([en,ar])=>[ar,en.charAt(0).toUpperCase()+en.slice(1)])));
export function errorMessage(detail,status=0){return t(arabicError(detail,status));}

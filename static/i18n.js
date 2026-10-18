// Only interface copy is translated. Document values, file names and publisher notes are excluded.
let saved='ar';try{saved=localStorage.getItem('sanad.language')==='en'?'en':'ar';}catch{}
export const language=saved;
export function saveLanguage(value){try{localStorage.setItem('sanad.language',value);}catch{}}
const english={
 'سند · مساحة المستندات':'SANAD · Document workspace','مساحة العمل':'Workspace','المستندات':'Documents','سير العمل':'Workflow','مراجعة البيانات':'Dataset review','النظام':'System',
 'الذكاء البصري للمستندات العربية':'Arabic document intelligence','مساحة العمل التجريبية · ٠٫١':'Local workspace · 0.1',
 'مساحة المستندات':'Document workspace','راجع الأصل، واحفظ كل التفاصيل.':'Review the source. Preserve every detail.',
 'جارٍ فتح مساحة العمل…':'Opening workspace…','رفع مستند':'Upload document','المدير العام':'Super admin','مراحل معالجة المستند':'Document workflow',
 'الاستلام':'Ingest','التعرف':'Recognize','المراجعة':'Review','الاعتماد':'Approve','التصدير':'Export',
 'إضافة وفحص':'Add and validate','تشغيل نماذج التعرف':'Run OCR models','تدقيق وتصحيح':'Verify and correct','اعتماد المستند':'Approve document','تسليم المخرجات':'Deliver outputs',
 'البحث في المستندات':'Search documents','ابحث عن مستند…':'Search documents…','تصفية حسب الحالة':'Filter by status','جميع الحالات':'All statuses','تحديث':'Refresh',
 'اختر مستنداً':'Select a document','اختر مستنداً للبدء.':'Select a document to begin.','اختر مستنداً لمراجعة نصه.':'Select a document to review its text.',
 'تشغيل OCR العربي':'Run Arabic OCR','الصفحة':'Page','تصغير':'Zoom out','تكبير':'Zoom in','صورة صفحة المستند الأصلية':'Original document page',
 'ستظهر صورة المستند الأصلي هنا.':'Your original document will appear here.',
 'هذا إصدار قديم من المحرك المحذوف. اضغط «تشغيل OCR العربي» لاستخراج نص حقيقي.':'This is a legacy result. Run Arabic OCR to extract real text.',
 'لا يوجد ناتج تعرف حقيقي في هذا الإصدار القديم. اضغط «تشغيل OCR العربي» لاستخراج النص.':'No real OCR text exists in this legacy version. Run Arabic OCR to extract it.',
 'المناطق النصية':'Text regions','سبب التصحيح':'Correction reason','صف التعديلات التي أجريتها':'Describe your changes','حفظ المسودة':'Save draft','اعتماد':'Approve','إعادة الفتح':'Reopen',
 'تنسيق المراجعة':'Review coordination','اسم المستخدم للمراجع':'Reviewer username','إسناد':'Assign','سبب التصعيد':'Escalation note','وضح ما يحتاج إلى متابعة':'Explain what needs attention','تصعيد':'Escalate',
 'سيظهر سجل الإصدارات بعد التعرف على النص.':'Version history appears after recognition.','تصدير النسخة المعتمدة (JSON)':'Export approved JSON',
 'قائمة مهام المعالجة':'Processing','المستند المحدد · اضغط تحديث لمتابعة الحالة':'Selected document · live updates while processing',
 'اختر مستنداً لعرض مهام معالجته.':'Select a document to inspect processing.','من المستند الأصلي إلى السجل المعتمد':'From source to approved record',
 'تحفظ كل مرحلة الأصل. ينتج التعرف مسودة، ويظل الاعتماد إجراءً بشرياً مستقلاً.':'Every stage preserves the original. OCR produces a draft; approval remains a separate human action.',
 'ارفع صورة بصيغة مدعومة. يحفظ الفحص الأصل ويعزل الملفات التالفة أو غير المدعومة.':'Upload a supported image. Validation preserves the original and quarantines damaged or unsupported files.',
 'يعالج العامل المهام المنتظرة. افحص الأخطاء وألغِ المهام أو أعد محاولة المهام المتوقفة بعد تجهيز الاعتماديات. يعرض التشغيل التجريبي سير العمل دون نموذج فعلي.':'The local worker extracts real text. Inspect errors and retry after resolving missing dependencies.',
 'طابق المناطق المرتبطة بالمصدر مع الصورة. احفظ التصحيحات في مسودة جديدة، أو أسند المراجعة، أو صعّد المشكلة. حفظ المسودة لا يعني اعتمادها.':'Compare source-linked regions with the image. Save corrections as a draft, assign a reviewer or escalate. Saving does not approve.',
 'راجع المناطق غير المؤكدة ثم اعتمد الإصدار الحالي. يُحفظ الإصدار المعتمد دون تعديل، ويمكن إعادة فتحه كمسودة جديدة.':'Resolve uncertain regions and approve the current version. Approved versions remain immutable; reopening creates a new draft.',
 'صدّر الصفحات المعتمدة وفق مخطط البيانات المحدد. تظهر أخطاء التحقق ولا تُسلّم السجلات المرفوضة.':'Export approved pages against the document schema. Validation errors are shown and rejected records are not delivered.',
 'مراجعة البيانات العامة':'Public dataset review','مستندات رسمية مصرية · عينة التقييم':'Egyptian official documents · evaluation sample','تحديث العينات':'Refresh examples',
 'أنشأ نموذج لغوي نصوص الناشر، مع تدقيق جزئي فقط. طابق كل كلمة ورقم وجدول مع الصورة قبل اعتبار الصفحة مراجعة.':'Publisher labels are model-generated and only spot-checked. Verify every word, number and table against the image before marking a page reviewed.',
 'صورة الصفحة الأصلية من البيانات العامة':'Public dataset source page','اختر عينة':'Select an example','النص المنسوخ':'Transcription','ملاحظة المراجعة':'Review note',
 'التصحيحات وقرارات تنسيق النص':'Corrections and formatting decisions','راجعت النص الكامل وطابقته مع الصورة.':'I checked the full transcription against the image.',
 'حفظ النص المُراجع':'Save reviewed transcription','يُحفظ النص منفصلاً عن نسخة الناشر. لا يبدأ التدريب عند الحفظ.':'Saved separately from publisher labels. Saving does not start training.',
 'النظام والنماذج':'System & models','إعدادات الخادم الحالية والإمكانات المتاحة.':'Current server configuration and available capabilities.',
 'التحقق من سلسلة التدقيق':'Verify audit chain','الدخول إلى سند':'Sign in to SANAD',
 'استخدم مفتاح الدخول لمساحة العمل. تفتح النسخة المحلية تلقائياً بصلاحيات المدير العام.':'Use your workspace access key. Local development opens automatically as Super admin.',
 'مفتاح الدخول':'Workspace access key','إلغاء':'Cancel','دخول':'Sign in','تسجيل الخروج':'Sign out',
 'الصور بصيغ PNG وJPEG وTIFF فقط. رفع ملفات PDF غير متاح بعد.':'PNG, JPEG and TIFF images only. PDF upload is not available yet.',
 'ملف الصورة':'Image file','اختر صورة':'Choose image','لم يتم اختيار ملف':'No file selected','الجهة':'Organization','رفع وإضافة إلى قائمة المعالجة':'Upload & process',
 'تسجيل الدخول':'Sign in','الدخول إلى مساحة العمل':'Sign in to workspace','تم تسجيل الخروج.':'Signed out.',
 'جارٍ تحميل النص…':'Loading transcription…','لا يوجد إصدار ناتج عن التعرف بعد.':'No recognition version yet.',
 'لم يكتمل التعرف بعد. راجع قائمة المهام أدناه. اضغط «تشغيل OCR العربي» لاستخراج النص الحقيقي.':'Recognition is not complete. Run Arabic OCR to extract text.',
 'لم يُرجع المحرك مناطق. تحتاج هذه الصفحة إلى فحص.':'No text regions were returned. Inspect this page.',
 'لا توجد مستندات. ارفع صورة للبدء.':'No documents yet. Upload an image to begin.','لا توجد مهام لهذا المستند.':'No processing jobs for this document.',
 'إعادة المحاولة':'Retry','افتح جلسة مخولة لعرض حالة الخادم.':'Open an authorized session to inspect the server.',
 'لا توجد عينة عامة مجهزة. راجع دليل البيانات العامة في مستندات المشروع.':'No public sample is prepared. See the public-data guide.',
 'تمت المراجعة':'Reviewed','بانتظار المراجعة':'Pending review','تابع المراحل من المستند الأصلي إلى السجل المعتمد.':'Follow each stage from original to approved record.',
 'مساحة مراجعة البيانات':'Dataset workbench','جهّز نصوصاً موثوقة قبل تدريب النموذج.':'Build trustworthy labels before training the model.',
 'اطلع على حالة الخادم والإمكانات المتاحة.':'Inspect the server and available capabilities.','هذا الحساب لا يملك صلاحية الاطلاع على المستندات.':'This account cannot access document content.',
 'الملف موجود مسبقاً. تم فتح مستنده.':'Existing file found; opened its document.','تم حفظ المستند وإضافته إلى قائمة التعرف.':'Document preserved and queued for recognition.',
 'تم رفع المستند وبدأ التعرف الحقيقي على النص باستخدام PaddleOCR العربي.':'Document uploaded. Real Arabic PaddleOCR has started.',
 'بدأ التعرف الحقيقي على النص باستخدام PaddleOCR العربي على المعالج المركزي. قد يستغرق تحميل النموذج بعض الوقت.':'Real Arabic PaddleOCR is running on CPU. Model loading may take a moment.',
 'اكتمل التعرف الحقيقي. راجع النص المستخرج مقابل الصورة الأصلية.':'Real OCR completed. Compare the extracted text against the original.',
 'توقفت المعالجة. راجع تفاصيل المهمة أدناه.':'Processing stopped. See job details below.',
 'لا توجد تعديلات على النص لحفظها.':'No transcription changes to save.','حُفظت مسودة جديدة. الاعتماد خطوة مستقلة.':'New draft saved. Approval is separate.',
 'احفظ المسودة قبل الاعتماد.':'Save your draft before approving.','تم اعتماد الإصدار الحالي من الصفحة.':'Current page version approved.',
 'أدخل سبب إعادة فتح الصفحة المعتمدة.':'Enter a reason to reopen the approved page.','فُتحت مسودة جديدة مع الاحتفاظ بالإصدار المعتمد.':'New draft opened; the approved version is preserved.',
 'احفظ التعديلات قبل التصدير.':'Save changes before exporting.','تم تصدير النسخة المعتمدة بصيغة JSON.':'Approved JSON exported.',
 'تم إسناد مهمة المراجعة.':'Review task assigned.','تم تصعيد مهمة المراجعة.':'Review task escalated.','سلسلة التدقيق سليمة.':'Audit chain is intact.',
 'أكد أنك راجعت الصفحة كاملة وطابقتها مع الصورة.':'Confirm that you checked the complete page against the image.',
 'حُفظ النص المُراجع منفصلاً مع سجل المراجع والتعديلات.':'Reviewed transcription saved separately with reviewer history.',
 'هل تريد تجاهل التعديلات غير المحفوظة على النص؟':'Discard unsaved transcription changes?','يرجى استكمال هذا الحقل.':'Please complete this field.',
 'تعذّر إتمام العملية. تحقق من اتصال الخادم وحاول مجدداً.':'The operation could not complete. Check the server connection and retry.',
 'البيانات المدخلة غير صالحة. تحقق من الحقول المطلوبة.':'Invalid input. Check required fields.',
 'توجد مناطق غير مؤكدة. راجع حالاتها قبل الاعتماد.':'Some regions are uncertain. Resolve their status before approval.',
 'الإصدار المعروض قديم. أعد تحميل الصفحة قبل المتابعة.':'This version is outdated. Reload the page before continuing.',
 'ليس لديك صلاحية تنفيذ هذا الإجراء.':'You do not have permission for this action.',
 'أدخل النص أو اختر حالة «غير مقروء» أو «غير موجود» للمنطقة الفارغة.':'Enter text or mark the empty region illegible or not present.',
 'محرك التعرف غير جاهز. تحقق من الاعتماديات وأوزان النموذج وعتاد التشغيل.':'The OCR runtime is not ready. Check dependencies, weights and hardware.',
 'يجب اعتماد جميع صفحات المستند قبل التصدير.':'Approve every page before exporting.',
 'فشلت معالجة بعض الصفحات. راجع حالة المحرك ثم أعد المحاولة.':'Some pages failed. Inspect the engine and retry.',
 'الملف فارغ.':'The file is empty.','حجم الملف أكبر من الحد المسموح.':'The file exceeds the upload limit.',
 'أبعاد الصورة تتجاوز الحد المسموح.':'Image dimensions exceed the limit.','صيغة الملف غير مدعومة. ارفع صورة PNG أو JPEG أو TIFF.':'Unsupported format. Upload PNG, JPEG or TIFF.',
 'الملف تالف أو لا يمكن قراءة صورته.':'The image is damaged or unreadable.',
 'تعذّر التحقق من الجلسة. أعد تحميل الصفحة.':'Session verification failed. Reload the page.','العنصر المطلوب غير موجود.':'The requested item was not found.',
 'تغيرت حالة العنصر. أعد تحميله قبل المتابعة.':'The item changed. Reload it before continuing.','تعذّر قبول البيانات. تحقق من الحقول وحالة المستند.':'Check the fields and document status.',
 'الخدمة غير متاحة حالياً.':'The service is currently unavailable.',
 'اكتمل':'Completed','جارٍ التنفيذ':'Running','فشلت المعالجة':'Failed','متوقف':'Blocked','في الانتظار':'Queued',
 'تم الاستلام':'Ingested','قيد المعالجة':'Processing','قيد المراجعة':'In review','معتمد':'Approved','تمت المعالجة':'Processed',
 'محرك قديم محذوف':'Removed legacy engine','PaddleOCR العربي':'Arabic PaddleOCR','مساحة سند':'SANAD workspace',
 'المهمة الحالية':'Current job','جاهز للتعرف':'Ready for recognition','لم تبدأ المعالجة بعد.':'Processing has not started.',
 'محاولات سابقة':'Previous attempts','حُفظ النص؛ يمكنك الآن مراجعته واعتماده.':'Text saved. You can now review and approve it.',
 'جارٍ تحميل النموذج واستخراج النص. يمكنك متابعة العمل؛ ستظهر النتيجة تلقائياً.':'Loading the model and extracting text. You can keep working; results update automatically.',
 'أعد تشغيل التعرف لتطبيق الإصلاح الحالي.':'Run recognition again to apply the current fix.',
 'تعذر حفظ العربية في محاولة سابقة بسبب ترميز Windows. تم إصلاح الحفظ إلى UTF-8؛ أعد المحاولة.':'An earlier run failed to save Arabic using Windows encoding. UTF-8 saving is now fixed; retry recognition.',
 'تعذّر حفظ النتيجة سابقاً. أعد المحاولة بعد إصلاح الحفظ؛ لا حاجة لإعادة رفع الملف.':'An earlier result could not be saved. Retry with the fix applied; no need to upload again.',
 'قاعدة البيانات مشغولة. انتظر اكتمال العملية الحالية ثم أعد المحاولة.':'The database is busy. Wait for the current operation and retry.',
 'الصورة الأصلية منخفضة الدقة. راجع الأسماء والأرقام مقابل المصدر، وارفع نسخة أوضح إن توفرت.':'The original image is low-resolution. Check names and numbers against the source; use a clearer copy when available.',
 'درجة المحرك':'Engine score','ليست نسبة دقة':'not an accuracy percentage',
 'السبب':'Cause','الإجراء المقترح':'Suggested action','أعد المحاولة':'Retry recognition','سجل المعالجة':'Processing history',
 'تحديث تلقائي أثناء المعالجة':'Updates automatically while processing','مفعّلة':'Enabled','معطّلة':'Disabled',
 'تبديل اللغة':'Switch language','تم طلب الإجراء: إلغاء.':'Cancellation requested.',
 'يعالج العامل المهام المنتظرة. افحص الأخطاء وألغِ المهام أو أعد محاولة المهام المتوقفة بعد تجهيز الاعتماديات.':'The worker processes queued jobs. Inspect errors, cancel tasks or retry after resolving dependencies.',
 'ملاحظات الناشر بلغتها الأصلية':'Publisher notes in their original language'
};
export function registerTranslations(pairs){Object.assign(english,pairs);}
export function t(value){
 const source=String(value??'');if(language==='ar')return source;
 if(english[source])return english[source];
 let output=source.replace('تُدار إعدادات النماذج على الخادم. هذه الصفحة لا تبدأ التدريب.','Model configuration is managed on the server. This page does not start training.');
 const rules=[[/([0-9]+) صفحة/g,(_,n)=>`${n} ${n==='1'?'page':'pages'}`],[/الإصدار/g,'Version'],[/الصفحة/g,'Page'],[/مستند · الأحدث أولاً/g,'documents · newest first'],[/ملاحظة من الناشر/g,'publisher notes'],[/المحاولات:/g,'Attempts:'],[/طُلب الإلغاء/g,'cancellation requested'],[/حالة المنطقة/g,'Region status'],[/نص المنطقة/g,'Region text'],[/تحديد منطقة المصدر/g,'Select source region'],[/ · تجريبي/g,' · synthetic source'],[/تم الدخول باسم/g,'Signed in as'],[/تعذّر التصدير:/g,'Export rejected:'],[/تم عزل الملف:/g,'File quarantined:'],[/تم طلب الإجراء:/g,'Action requested:'],[/تعذّر فتح مساحة العمل:/g,'Could not open workspace:'],[/تعذّر تحميل الصورة/g,'Image unavailable'],[/يوجد خلل في سلسلة التدقيق عند الحدث/g,'Audit chain mismatch at event'],[/صيغ الصور المدعومة:/g,'Supported image formats:'],[/تُدار إعدادات النماذج على الخادم. هذه الصفحة لا تبدأ التدريب./g,'Model configuration is managed on the server. This page does not start training.'],[/محرك /g,'Engine ']];
 for(const [pattern,replacement]of rules)output=output.replace(pattern,replacement);
 for(const [ar,en]of Object.entries(english).sort((a,b)=>b[0].length-a[0].length)){if(output.includes(ar))output=output.split(ar).join(en);}
 return output.replace(/،/g,',').replace(/[٠-٩]/g,d=>String('٠١٢٣٤٥٦٧٨٩'.indexOf(d))).replace(/٪/g,'%');
}
export function applyLanguage(){
 document.documentElement.lang=language;document.documentElement.dir=language==='ar'?'rtl':'ltr';
 if(language==='ar')return;
 const walker=document.createTreeWalker(document.documentElement,NodeFilter.SHOW_TEXT);
 let current;const nodes=[];while(current=walker.nextNode())nodes.push(current);
 for(const text of nodes){if(text.parentElement?.closest('script,style,textarea,#dataset-notes'))continue;const trimmed=text.textContent.trim();if(trimmed)text.textContent=text.textContent.replace(trimmed,t(trimmed));}
 for(const element of document.querySelectorAll('[placeholder],[aria-label],[alt],[title]'))for(const attr of ['placeholder','aria-label','alt','title'])if(element.hasAttribute(attr))element.setAttribute(attr,t(element.getAttribute(attr)));
}

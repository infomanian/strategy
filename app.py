# app.py
import os
from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from anthropic import Anthropic

APP_TITLE = "مشاور حقوقی هوشمند"
APP_DESC = "اپی که براساس نقش کاربر (عمومی یا وکیل) مشاورهٔ مناسب و استراتژی‌های دفاع ارائه می‌دهد."

app = FastAPI(title=APP_TITLE, description=APP_DESC)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
if not ANTHROPIC_API_KEY:
    # اگر کی‌ّی در env نیست، هنگام فراخوانی route خطا می‌زنیم.
    client = None
else:
    client = Anthropic(api_key=ANTHROPIC_API_KEY)

# =====================
# قالب پرامپت (دو حالت)
# =====================
PROMPT_TEMPLATE_LAYPERSON = """شما یک مشاور حقوقی هستید که باید به یک شخص عادی (غیر حقوق‌دان) مشاوره بدهی.
- لحن: بسیار ساده، روان، قابل فهم برای کسی که هیچ دانشی از حقوق ندارد.
- کار: بر اساس اطلاعات زیر ابتدا به صورت چند جملهٔ ساده مشکل حقوقی را توضیح بده (چه موضوعی است و چرا مهم است)،
  سپس ۳ تا ۵ استراتژی یا راهکار دفاعی/اقدامی ارائه بده (برای هر کدام 1–2 جمله ساده دربارهٔ مزایا و معایب بنویس)،
  بعد از بین آن‌ها **یکی** را به عنوان «پیشنهاد اصلی» انتخاب کن و دلیل انتخاب را به زبان ساده توضیح بده.
- در انتها یک «checklist» کوتاه ۳–۵ موردی بنویس از کارهایی که کاربر فوراً باید انجام دهد.
- اگر نیاز به اطلاعات بیشتر داری، ۵ سؤال کلیدی و کوتاه که باید از کاربر پرسیده شود را لیست کن.

اطلاعات پرونده:
{case_text}
"""

PROMPT_TEMPLATE_LAWYER = """شما یک وکیل مجرب هستید که باید برای یک وکیل دیگر یا موکل حرفه‌ای (کاربر حقوق‌دان) مشاورهٔ تخصصی بدهی.
- لحن: فنی، متمرکز بر استدلال حقوقی، مواد قانونی مرتبط، رویه‌های قضایی و استراتژی‌های دفاعی.
- کار: بر اساس اطلاعات زیر ابتدا خلاصهٔ مسئله را در قالب نقاط کلیدی ذکر کن، سپس ۴–۶ استراتژی دفاعی/اعتراضی پیشنهاد بده.
  برای هر استراتژی: توضیح فنی، مواد قانونی و آیین‌دادرسی مرتبط (در صورت امکان نام ماده/رای)، نقاط قوت و ضعف، ریسک‌های احتمالی، و برآورد شواهد لازم ذکر شود.
- در پایان یکی از استراتژی‌ها را به عنوان «استراتژی پیشنهادی» انتخاب کن و دلیل فنی و شرایط تحقق آن را شرح بده.
- همچنین یک طرح گام‌به‌گام (تاکتیکی) برای اجرای استراتژی پیشنهادی (حداقل 5 گام) آماده کن.
- اگر اطلاعات تکمیلی لازم است، 8 سؤال تخصصی که باید پاسخ داده شود را فهرست کن.

اطلاعات پرونده:
{case_text}
"""

# =====================
# صفحات وب ساده
# =====================

INDEX_HTML = """<!doctype html>
<html lang="fa" dir="rtl">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>مشاور حقوقی هوشمند</title>
  <style>
    body{font-family:Arial, sans-serif;background:#f7fafc;color:#111;padding:20px}
    .card{max-width:860px;margin:10px auto;background:#fff;padding:18px;border-radius:8px;box-shadow:0 6px 18px rgba(0,0,0,0.06)}
    label{display:block;margin-top:10px}
    textarea,input,select{width:100%;padding:10px;margin-top:6px;border:1px solid #ddd;border-radius:6px}
    button{margin-top:12px;padding:10px 16px;border-radius:8px;background:#0ea5a4;color:#fff;border:none;cursor:pointer}
    .muted{color:#666;font-size:14px}
    pre{white-space:pre-wrap;background:#0f172a;color:#e6f6f6;padding:12px;border-radius:6px}
  </style>
</head>
<body>
  <div class="card">
    <h2>مشاور حقوقی هوشمند</h2>
    <p class="muted">نقش خود را انتخاب کنید تا مشاوره با لحن مناسب ارائه شود.</p>
    <form method="post" action="/advise">
      <label>نقش:
        <select name="role">
          <option value="layperson">کاربر عادی (زبان ساده)</option>
          <option value="lawyer">وکیل (زبان تخصصی)</option>
        </select>
      </label>

      <label>خلاصهٔ پرونده / سؤال حقوقی (به فارسی):</label>
      <textarea name="case_text" rows="8" placeholder="شرح ماجرا، تاریخچه، مدارک مهم و خواستهٔ شما..." required></textarea>

      <label>اگر محدودیت زمانی یا اولویت هزینه/سرعت دارید بنویسید (اختیاری):</label>
      <input type="text" name="constraints" placeholder="مثلاً: سریع و ارزان؛ یا: تضمین بیشترین شانس برائت">

      <button type="submit">دریافت مشاوره</button>
    </form>
  </div>
</body>
</html>
"""

RESULT_HTML = """<!doctype html>
<html lang="fa" dir="rtl">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>نتیجه مشاوره</title>
  <style>
    body{font-family:Arial, sans-serif;background:#f7fafc;color:#111;padding:20px}
    .card{max-width:860px;margin:10px auto;background:#fff;padding:18px;border-radius:8px;box-shadow:0 6px 18px rgba(0,0,0,0.06)}
    pre{white-space:pre-wrap;background:#0f172a;color:#e6f6f6;padding:12px;border-radius:6px}
    a{display:inline-block;margin-top:10px}
  </style>
</head>
<body>
  <div class="card">
    <h2>نتیجهٔ مشاوره</h2>
    <div>
      <h3>خلاصهٔ ورودی</h3>
      <pre>{{ case_text }}</pre>
    </div>
    <div>
      <h3>پاسخ هوش مصنوعی</h3>
      <pre>{{ advice }}</pre>
    </div>
    <a href="/">◀ بازگشت</a>
  </div>
</body>
</html>
"""

# =====================
# روت‌ها
# =====================

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return HTMLResponse(INDEX_HTML)

@app.post("/advise", response_class=HTMLResponse)
async def advise(request: Request, role: str = Form(...), case_text: str = Form(...), constraints: str = Form(None)):
    if client is None:
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY تنظیم نشده است.")

    # انتخاب پرامپت بر اساس نقش
    if role == "lawyer":
        template = PROMPT_TEMPLATE_LAWYER
    else:
        template = PROMPT_TEMPLATE_LAYPERSON

    # اضافه کردن قیود اگر داده شده
    extra = ""
    if constraints:
        extra = f"\n\nالویت‌ها / قیود: {constraints}\n"

    prompt = template.format(case_text=case_text + extra)

    # پیام را به مدل ارسال می‌کنیم (یک پیام فقط، متن)
    try:
        resp = client.messages.create(
            model=os.getenv("ANTHROPIC_MODEL", "claude-3.5-sonnet-20240620"),
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}]
        )
        advice = resp.content[0].text if hasattr(resp, "content") else str(resp)
    except Exception as e:
        # خطای API را به کاربر می‌دهیم
        advice = f"خطا در دریافت پاسخ از Anthropic: {e}"

    # رندر صفحه نتیجه
    html = RESULT_HTML.replace("{{ case_text }}", case_text).replace("{{ advice }}", advice)
    return HTMLResponse(html)

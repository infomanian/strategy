# app.py
import os
from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from anthropic import Anthropic

APP_TITLE = "مشاور حقوقی (Role-based)"
APP_VERSION = "1.0.0"

app = FastAPI(title=APP_TITLE, version=APP_VERSION)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-3.5-sonnet-20240620")
client = Anthropic(api_key=ANTHROPIC_API_KEY) if ANTHROPIC_API_KEY else None

def build_prompt(role: str, title: str, details: str) -> str:
    """
    role: 'user' or 'lawyer'
    title: عنوان خلاصه پرونده
    details: شرح وقایع / سوال کاربر
    """
    # Instructions for style
    if role == "user":
        style_instr = (
            "تو نقش یک مشاور حقوقی برای یک فرد عادی هستی. "
            "با زبان خیلی ساده، بدون اصطلاحات پیچیده حقوقی، پاسخ بده. "
            "مرحله‌به‌مرحله توضیح بده چه حقوقی داری، چه مدارکی لازم است، و چه گام‌های عملی باید برداری. "
            "اگر گزینه‌هایی وجود دارد، هر گزینه را کوتاه شرح بده و ریسک/مزیت هر کدام را واضح بگو و در نهایت یک پیشنهاد ساده بده."
        )
    else:  # lawyer
        style_instr = (
            "تو نقش یک وکیل باتجربه هستی. پاسخ را با زبان تخصصی حقوقی بده، "
            "مواد قانونی و آرای وحدت رویه یا رویه قضایی مرتبط را پیشنهاد کن (اگر لازم شد، شماره ماده را ذکر کن)، "
            "چند استراتژی دفاعی ممکن را به همراه نقاط قوت و ضعف و ملاحظات شواهدی فهرست کن و در نهایت یک استراتژی توصیه‌شده را مشخص کن و دلیلش را توضیح بده."
        )

    prompt = f"""
{style_instr}

عنوان پرونده یا موضوع: {title}

شرح دقیق یا سؤال کاربر:
{details}

در خروجی:
1) یک خلاصهٔ کوتاه (۲-۳ خط) از موضوع بیاور.
2) پاسخ اصلی مطابق نقش (ساده یا تخصصی).
3) فهرستی از حداقل ۲-۴ استراتژی/راهکار (هر کدام عنوان، توضیح مختصر، مزایا و معایب).
4) در انتها، یک استراتژی را انتخاب و با دلیل پیشنهاد کن.
5) اگر اطلاعات تکمیلی‌ای لازم است که کاربر باید فراهم کند، به صورت بولت‌پوینت بیاور.
"""
    return prompt.strip()

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "title": APP_TITLE})

@app.post("/advise", response_class=HTMLResponse)
async def advise(request: Request,
                 role: str = Form(...),   # 'user' or 'lawyer'
                 title: str = Form(""),
                 details: str = Form("")):
    if client is None:
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY تنظیم نشده است.")

    # basic validation
    role = role.lower()
    if role not in ("user", "lawyer"):
        raise HTTPException(status_code=400, detail="role باید 'user' یا 'lawyer' باشد.")

    # build prompt
    prompt = build_prompt(role=role, title=title or "بدون عنوان", details=details or "بدون شرح")
    try:
        resp = client.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}]
        )
        # extract text
        text = resp.content[0].text if hasattr(resp, "content") else str(resp)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"خطا در تماس با Anthropic: {e}")

    # render result
    return templates.TemplateResponse("result.html", {
        "request": request,
        "title": APP_TITLE,
        "role": role,
        "title_input": title,
        "details_input": details,
        "answer": text
    })

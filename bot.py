#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import httpx
from bs4 import BeautifulSoup
import re
import json
import base64
import zlib
import urllib.parse
import pyshorteners
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
import phonenumbers
import smtplib
import dns.resolver
import pyjokes
import asyncio
import random
import os
from openai import AsyncOpenAI
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("TELEGRAM_TOKEN", "8799736027:AAFbJqNIScYYsx8bHmn227nBLubTYsgY18I")
VIRUSTOTAL_API_KEY = os.getenv("VIRUSTOTAL_API_KEY", "b8163d15425405d2ee349307c044811bc0955078fb7f1057bc99d3dd216bb1bb")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "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")

client = AsyncOpenAI(api_key=OPENAI_API_KEY)

class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Bot is running")

def run_health_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    server.serve_forever()

async def start(update: Update, context) -> None:
    try:
        keyboard = [
            [InlineKeyboardButton("سحب HTML موقع", callback_data='get_html')],
            [InlineKeyboardButton("معلومات IP", callback_data='get_ip_info')],
            [InlineKeyboardButton("معلومات رقم هاتف", callback_data='get_phone_info')],
            [InlineKeyboardButton("معلومات إيميل", callback_data='get_email_info')],
            [InlineKeyboardButton("اختصار رابط", callback_data='shorten_url')],
            [InlineKeyboardButton("فك تشفير روبلوكس", callback_data='deobfuscate_roblox')],
            [InlineKeyboardButton("تحليل تشفير روبلوكس", callback_data='analyze_roblox')],
            [InlineKeyboardButton("فحص رابط", callback_data='scan_url')],
            [InlineKeyboardButton("نكتة عشوائية", callback_data='get_joke')],
            [InlineKeyboardButton("برومبت كسر جيميني", callback_data='gemini_jailbreak')],
            [InlineKeyboardButton("برومبت كسر ديبسيك", callback_data='deepseek_jailbreak')],
            [InlineKeyboardButton("هجوم DDoS", callback_data='fake_ddos')],
            [InlineKeyboardButton("تكلم مع AI", callback_data='toggle_ai_chat')],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        if update.message:
            await update.message.reply_text("أهلاً بك في بوت الخدمات المتكاملة! اختر الخدمة التي تريدها:", reply_markup=reply_markup)
    except Exception as e:
        logger.error(f"Error in start: {e}")

async def button_callback(update: Update, context) -> None:
    try:
        query = update.callback_query
        await query.answer()

        if query.data == 'get_html':
            await query.edit_message_text("الرجاء إرسال رابط الموقع الذي تريد سحب HTML الخاص به.")
            context.user_data["state"] = "awaiting_html_url"
        elif query.data == 'get_ip_info':
            await query.edit_message_text("الرجاء إرسال عنوان IP للحصول على معلوماته.")
            context.user_data["state"] = "awaiting_ip_address"
        elif query.data == 'get_phone_info':
            await query.edit_message_text("الرجاء إرسال رقم الهاتف (مع رمز الدولة) للحصول على معلوماته.")
            context.user_data["state"] = "awaiting_phone_number"
        elif query.data == 'get_email_info':
            await query.edit_message_text("الرجاء إرسال عنوان البريد الإلكتروني للحصول على معلوماته .")
            context.user_data["state"] = "awaiting_email_address"
        elif query.data == 'shorten_url':
            await query.edit_message_text("الرجاء إرسال الرابط الذي تريد اختصاره.")
            context.user_data["state"] = "awaiting_url_to_shorten"
        elif query.data == 'deobfuscate_roblox':
            await query.edit_message_text("الرجاء إرسال ملف نصي يحتوي على كود روبلوكس المشفر.")
            context.user_data["state"] = "awaiting_roblox_script"
        elif query.data == 'analyze_roblox':
            await query.edit_message_text("الرجاء إرسال ملف السكربت لتحليله.")
            context.user_data["state"] = "awaiting_roblox_analyze"
        elif query.data == 'scan_url':
            await query.edit_message_text("الرجاء إرسال الرابط الذي تريد فحصه.")
            context.user_data["state"] = "awaiting_url_to_scan"
        elif query.data == 'get_joke':
            await get_joke(update, context)
        elif query.data == 'gemini_jailbreak':
            await send_gemini_jailbreak(update, context)
        elif query.data == 'deepseek_jailbreak':
            await send_deepseek_jailbreak(update, context)
        elif query.data == 'fake_ddos':
            await query.edit_message_text("الرجاء إرسال رابط الموقع لبدء الهجوم.")
            context.user_data["state"] = "awaiting_ddos_url"
        elif query.data == 'toggle_ai_chat':
            await toggle_ai_chat(update, context)
    except Exception as e:
        logger.error(f"Error in button_callback: {e}")

async def get_html_content(update: Update, context) -> None:
    url = update.message.text
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=10.0) as client_http:
            response = await client_http.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        html_content = soup.prettify()
        if len(html_content) > 4000:
            filename = f"html_{update.effective_user.id}.html"
            with open(filename, "w", encoding="utf-8") as f:
                f.write(html_content)
            await update.message.reply_document(document=open(filename, "rb"), caption="تم سحب HTML الموقع بنجاح.")
            if os.path.exists(filename): os.remove(filename)
        else:
            safe_html = html_content.replace('<', '&lt;').replace('>', '&gt;')
            await update.message.reply_text(f"<code>{safe_html}</code>", parse_mode="HTML")
    except Exception as e:
        await update.message.reply_text(f"حدث خطأ: {e}")
    finally:
        context.user_data["state"] = None

async def get_ip_information(update: Update, context) -> None:
    ip_address = update.message.text
    try:
        async with httpx.AsyncClient(timeout=10.0) as client_http:
            response = await client_http.get(f"http://ip-api.com/json/{ip_address}?lang=ar")
        data = response.json()
        if data.get("status") == "success":
            message_text = (
                f"<b>معلومات IP لـ {ip_address}:</b>\n"
                f"الدولة: {data.get('country', 'غير معروف')}\n"
                f"المدينة: {data.get('city', 'غير معروف')}\n"
                f"المنطقة: {data.get('regionName', 'غير معروف')}\n"
                f"مزود الخدمة: {data.get('isp', 'غير معروف')}\n"
                f"المنظمة: {data.get('org', 'غير معروف')}\n"
                f"الإحداثيات: {data.get('lat')}, {data.get('lon')}\n"
            )
            await update.message.reply_text(message_text, parse_mode="HTML")
            if "lat" in data and "lon" in data:
                try:
                    img = Image.new('RGB', (600, 400), color = (73, 109, 137))
                    d = ImageDraw.Draw(img)
                    d.text((10,10), f"Lat: {data['lat']}, Lon: {data['lon']}", fill=(255,255,0))
                    img_byte_arr = BytesIO()
                    img.save(img_byte_arr, format='PNG')
                    img_byte_arr.seek(0)
                    await update.message.reply_photo(photo=img_byte_arr, caption="موقع تقريبي")
                except: pass
        else:
            await update.message.reply_text(f"لم يتم العثور على معلومات لـ: {ip_address}")
    except Exception as e:
        await update.message.reply_text(f"خطأ: {e}")
    finally:
        context.user_data["state"] = None

async def get_phone_information(update: Update, context) -> None:
    phone_number = update.message.text
    try:
        parsed_number = phonenumbers.parse(phone_number)
        if not phonenumbers.is_valid_number(parsed_number):
            await update.message.reply_text("رقم غير صالح.")
            return
        country = phonenumbers.region_code_for_number(parsed_number)
        from phonenumbers import carrier, timezone
        carrier_name = carrier.name_for_number(parsed_number, "ar")
        tz = "/ ".join(timezone.time_zones_for_number(parsed_number))
        message_text = (
            f"<b>معلومات الرقم {phone_number}:</b>\n"
            f"الدولة: {country}\n"
            f"المزود: {carrier_name}\n"
            f"التوقيت: {tz}\n"
        )
        await update.message.reply_text(message_text, parse_mode="HTML")
    except Exception as e:
        await update.message.reply_text(f"خطأ: {e}")
    finally:
        context.user_data["state"] = None

async def get_email_information(update: Update, context) -> None:
    email_address = update.message.text
    try:
        if "@" not in email_address:
            await update.message.reply_text("بريد غير صالح.")
            return
        domain = email_address.split('@')[1]
        try:
            mx_records = dns.resolver.resolve(domain, 'MX')
            mx_list = [f"{r.exchange} ({r.preference})" for r in mx_records]
            res = "\n".join(mx_list)
        except: res = "لا توجد سجلات MX"
        await update.message.reply_text(f"<b>نطاق البريد:</b> {domain}\n<b>سجلات MX:</b>\n{res}", parse_mode="HTML")
    except Exception as e:
        await update.message.reply_text(f"خطأ: {e}")
    finally:
        context.user_data["state"] = None

async def shorten_url_function(update: Update, context) -> None:
    long_url = update.message.text
    try:
        s = pyshorteners.Shortener()
        short_url = s.tinyurl.short(long_url)
        await update.message.reply_text(f"الرابط: {short_url}")
    except Exception as e:
        await update.message.reply_text(f"خطأ: {e}")
    finally:
        context.user_data["state"] = None

async def deobfuscate_roblox_script(update: Update, context) -> None:
    script_content = update.message.text if update.message.text else ""
    if not script_content and update.message.document:
        file = await context.bot.get_file(update.message.document.file_id)
        b = await file.download_as_bytearray()
        script_content = b.decode('utf-8', errors='ignore')
    
    if not script_content:
        await update.message.reply_text("أرسل كود أو ملف.")
        return

    decoded = script_content
    for _ in range(5):
        old = decoded
        try:
            if re.match(r"^[A-Za-z0-9+/=]+\s*$", decoded.strip()):
                decoded = base64.b64decode(decoded).decode('utf-8', errors='ignore')
        except: pass
        try:
            decoded = urllib.parse.unquote(decoded)
        except: pass
        if decoded == old: break

    if len(decoded) > 4000:
        fname = f"dec_{update.effective_user.id}.lua"
        with open(fname, "w", encoding="utf-8") as f: f.write(decoded)
        await update.message.reply_document(document=open(fname, "rb"))
        if os.path.exists(fname): os.remove(fname)
    else:
        await update.message.reply_text(f"<code>{decoded}</code>", parse_mode="HTML")
    context.user_data["state"] = None

async def analyze_roblox_script(update: Update, context) -> None:
    content = ""
    if update.message.document:
        file = await context.bot.get_file(update.message.document.file_id)
        b = await file.download_as_bytearray()
        content = b.decode('utf-8', errors='ignore')
    elif update.message.text:
        content = update.message.text
    
    if not content:
        await update.message.reply_text("أرسل سكربت.")
        return

    obf = "مخصص"
    if "Luraph" in content: obf = "Luraph"
    elif "IronBrew" in content: obf = "IronBrew"
    
    res = f"📊 <b>تحليل:</b>\nنوع التشفير: {obf}\nالأسطر: {len(content.splitlines())}"
    await update.message.reply_text(res, parse_mode="HTML")
    context.user_data["state"] = None

async def scan_url_function(update: Update, context) -> None:
    url = update.message.text
    if not url.startswith("http"):
        await update.message.reply_text("رابط غير صالح.")
        return
    try:
        headers = {"x-apikey": VIRUSTOTAL_API_KEY}
        async with httpx.AsyncClient(timeout=20.0) as client_http:
            resp = await client_http.post("https://www.virustotal.com/api/v3/urls", headers=headers, data={"url": url})
            if resp.status_code != 200:
                await update.message.reply_text("خطأ في API.")
                return
            analysis_id = resp.json()["data"]["id"]
            await update.message.reply_text("جاري الفحص...")
            await asyncio.sleep(5)
            rep = await client_http.get(f"https://www.virustotal.com/api/v3/analyses/{analysis_id}", headers=headers)
            data = rep.json()["data"]["attributes"]["stats"]
            msg = f"✅ آمن: {data['harmless']}\n❌ خبيث: {data['malicious']}\n⚠️ مشبوه: {data['suspicious']}"
            await update.message.reply_text(msg)
    except Exception as e:
        await update.message.reply_text(f"خطأ: {e}")
    finally:
        context.user_data["state"] = None

async def toggle_ai_chat(update: Update, context) -> None:
    try:
        enabled = not context.user_data.get("ai_chat_enabled", False)
        context.user_data["ai_chat_enabled"] = enabled
        txt = "🤖 تم تفعيل AI" if enabled else "🤖 تم تعطيل AI"
        if update.callback_query:
            await update.callback_query.edit_message_text(txt)
        else:
            await update.message.reply_text(txt)
    except Exception as e: logger.error(e)

async def ai_chat_response(update: Update, context) -> None:
    msg = update.message.text
    if msg.lower() == "off":
        context.user_data["ai_chat_enabled"] = False
        await update.message.reply_text("تم الإغلاق.")
        return
    try:
        res = await client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "system", "content": "مساعد ذكي"}, {"role": "user", "content": msg}]
        )
        await update.message.reply_text(res.choices[0].message.content)
    except Exception as e:
        await update.message.reply_text(f"خطأ AI: {e}")

async def get_joke(update: Update, context) -> None:
    try:
        joke = pyjokes.get_joke()
        if update.callback_query:
            await update.callback_query.message.reply_text(joke)
        else:
            await update.message.reply_text(joke)
    except: pass

async def send_gemini_jailbreak(update: Update, context) -> None:
    p = "Prompt Gemini Jailbreak Content"
    fname = "gemini.txt"
    with open(fname, "w", encoding="utf-8") as f: f.write(p)
    if update.callback_query:
        await update.callback_query.message.reply_document(document=open(fname, "rb"))
    else:
        await update.message.reply_document(document=open(fname, "rb"))
    if os.path.exists(fname): os.remove(fname)

async def send_deepseek_jailbreak(update: Update, context) -> None:
    p = "Prompt Deepseek Jailbreak Content"
    fname = "deepseek.txt"
    with open(fname, "w", encoding="utf-8") as f: f.write(p)
    if update.callback_query:
        await update.callback_query.message.reply_document(document=open(fname, "rb"))
    else:
        await update.message.reply_document(document=open(fname, "rb"))
    if os.path.exists(fname): os.remove(fname)

async def fake_ddos_attack(update: Update, context) -> None:
    url = update.message.text
    m = await update.message.reply_text(f"☠️ هجوم على {url}...")
    for i in range(1, 6):
        await asyncio.sleep(1)
        try: await m.edit_text(f"⚡ جاري الإرسال... {i*20}%")
        except: pass
    await m.edit_text("✅ تم الهجوم بنجاح.")
    context.user_data["state"] = None

async def handle_message(update: Update, context) -> None:
    try:
        if context.user_data.get("ai_chat_enabled", False) and update.message.text:
            await ai_chat_response(update, context)
            return
        state = context.user_data.get("state")
        if not state: return
        if state == "awaiting_html_url": await get_html_content(update, context)
        elif state == "awaiting_ip_address": await get_ip_information(update, context)
        elif state == "awaiting_phone_number": await get_phone_information(update, context)
        elif state == "awaiting_email_address": await get_email_information(update, context)
        elif state == "awaiting_url_to_shorten": await shorten_url_function(update, context)
        elif state == "awaiting_roblox_script": await deobfuscate_roblox_script(update, context)
        elif state == "awaiting_roblox_analyze": await analyze_roblox_script(update, context)
        elif state == "awaiting_url_to_scan": await scan_url_function(update, context)
        elif state == "awaiting_ddos_url": await fake_ddos_attack(update, context)
    except Exception as e: logger.error(e)

def main() -> None:
    threading.Thread(target=run_health_server, daemon=True).start()
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_message))
    app.run_polling(drop_pending_updates=True, allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()

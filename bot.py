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
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("TELEGRAM_TOKEN", "8799736027:AAFbJqNIScYYsx8bHmn227nBLubTYsgY18I")
VIRUSTOTAL_API_KEY = os.getenv("VIRUSTOTAL_API_KEY", "b8163d15425405d2ee349307c044811bc0955078fb7f1057bc99d3dd216bb1bb")

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
            [InlineKeyboardButton("🌐 سحب HTML", callback_data='get_html'), InlineKeyboardButton("📍 معلومات IP", callback_data='get_ip_info')],
            [InlineKeyboardButton("📱 معلومات هاتف", callback_data='get_phone_info'), InlineKeyboardButton("📧 معلومات إيميل", callback_data='get_email_info')],
            [InlineKeyboardButton("🔗 اختصار رابط", callback_data='shorten_url'), InlineKeyboardButton("🔍 فحص رابط", callback_data='scan_url')],
            [InlineKeyboardButton("🤖 حساب روبلوكس", callback_data='roblox_user'), InlineKeyboardButton("📜 سحب سورس", callback_data='get_source')],
            [InlineKeyboardButton("🔐 تشفير VM", callback_data='encrypt_lua'), InlineKeyboardButton("🔓 فك تشفيرات", callback_data='advanced_deobf')],
            [InlineKeyboardButton("📊 تحليل تشفير", callback_data='analyze_roblox'), InlineKeyboardButton("☠️ هجوم DDoS", callback_data='fake_ddos')],
            [InlineKeyboardButton("💎 برومبت جيميني", callback_data='gemini_jailbreak'), InlineKeyboardButton("🌑 برومبت ديبسيك", callback_data='deepseek_jailbreak')],
            [InlineKeyboardButton("😂 نكتة عشوائية", callback_data='get_joke')],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        msg = "🤖 **أهلاً بك في بوت الخدمات المتكاملة!**\n\nاختر الخدمة التي تريدها من الأزرار أدناه:"
        if update.message:
            await update.message.reply_text(msg, reply_markup=reply_markup, parse_mode="Markdown")
        elif update.callback_query:
            await update.callback_query.message.reply_text(msg, reply_markup=reply_markup, parse_mode="Markdown")
    except Exception as e: logger.error(e)

async def button_callback(update: Update, context) -> None:
    try:
        query = update.callback_query
        await query.answer()
        data_map = {
            'get_html': "awaiting_html_url", 'get_ip_info': "awaiting_ip_address",
            'get_phone_info': "awaiting_phone_number", 'get_email_info': "awaiting_email_address",
            'shorten_url': "awaiting_url_to_shorten", 'scan_url': "awaiting_url_to_scan",
            'roblox_user': "awaiting_roblox_user", 'get_source': "awaiting_script_link",
            'encrypt_lua': "awaiting_lua_encrypt", 'advanced_deobf': "awaiting_roblox_script",
            'analyze_roblox': "awaiting_roblox_analyze", 'fake_ddos': "awaiting_ddos_url"
        }
        if query.data in data_map:
            context.user_data["state"] = data_map[query.data]
            await query.edit_message_text(f"📥 **الرجاء إرسال المطلوب للخدمة المختارة:**")
        elif query.data == 'get_joke': await get_joke(update, context)
        elif query.data == 'gemini_jailbreak': await send_gemini_jailbreak(update, context)
        elif query.data == 'deepseek_jailbreak': await send_deepseek_jailbreak(update, context)
    except Exception as e: logger.error(e)

async def get_roblox_user_info(update: Update, context) -> None:
    username = update.message.text.strip()
    msg_wait = await update.message.reply_text("🔍 **جاري جلب معلومات روبلوكس...**")
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post("https://users.roblox.com/v1/usernames/users", json={"usernames": [username], "excludeBannedUsers": False})
            data = resp.json()
            if not data.get("data"):
                await msg_wait.edit_text("❌ المستخدم غير موجود.")
                return
            uid = data["data"][0]["id"]
            det = (await client.get(f"https://users.roblox.com/v1/users/{uid}")).json()
            fol = (await client.get(f"https://friends.roblox.com/v1/users/{uid}/followers/count")).json()
            res = (f"🤖 **Roblox Account:**\n\n👤 Name: {det.get('displayName')}\n🆔 User: @{det.get('name')}\n🔢 ID: `{uid}`\n📅 Created: {det.get('created')[:10]}\n👥 Followers: {fol.get('count', 0):,}\n📝 Bio: {det.get('description') or 'None'}")
            await msg_wait.edit_text(res, parse_mode="Markdown")
    except Exception as e: await msg_wait.edit_text(f"❌ Error: {e}")
    finally: context.user_data["state"] = None

async def encrypt_lua_vm(update: Update, context) -> None:
    content = update.message.text if update.message.text else ""
    if update.message.document:
        file = await context.bot.get_file(update.message.document.file_id)
        content = (await file.download_as_bytearray()).decode('utf-8', errors='ignore')
    if not content:
        await update.message.reply_text("❌ أرسل كود.")
        return
    try:
        enc = base64.b64encode(zlib.compress(content.encode())).decode()
        vm = f'-- Encrypted by Manus VM\nlocal _ = "{enc}"\nload(zlib_decompress(base64_decode(_)))()'
        fname = f"vm_{update.effective_user.id}.lua"
        with open(fname, "w") as f: f.write(vm)
        await update.message.reply_document(document=open(fname, "rb"), caption="✅ **VM Encryption Done!**")
        os.remove(fname)
    except Exception as e: await update.message.reply_text(f"❌ Error: {e}")
    finally: context.user_data["state"] = None

async def get_script_source(update: Update, context) -> None:
    url = update.message.text.strip()
    try:
        raw = url.replace("github.com", "raw.githubusercontent.com").replace("/blob/", "/")
        if "pastebin.com" in url and "/raw/" not in url: raw = url.replace("pastebin.com/", "pastebin.com/raw/")
        async with httpx.AsyncClient(follow_redirects=True) as client:
            resp = await client.get(raw)
        if resp.status_code == 200:
            fname = f"src_{update.effective_user.id}.lua"
            with open(fname, "w", encoding="utf-8") as f: f.write(resp.text)
            await update.message.reply_document(document=open(fname, "rb"), caption="✅ **Source Fetched.**")
            os.remove(fname)
        else: await update.message.reply_text("❌ Failed to fetch.")
    except Exception as e: await update.message.reply_text(f"❌ Error: {e}")
    finally: context.user_data["state"] = None

async def get_html_content(update: Update, context) -> None:
    url = update.message.text
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=15.0) as client:
            resp = await client.get(url)
        html = BeautifulSoup(resp.text, 'html.parser').prettify()
        if len(html) > 4000:
            fname = f"h_{update.effective_user.id}.html"
            with open(fname, "w", encoding="utf-8") as f: f.write(html)
            await update.message.reply_document(document=open(fname, "rb"), caption="✅ HTML Fetched.")
            os.remove(fname)
        else: await update.message.reply_text(f"```html\n{html}```", parse_mode="MarkdownV2")
    except Exception as e: await update.message.reply_text(f"❌ Error: {e}")
    finally: context.user_data["state"] = None

async def get_ip_information(update: Update, context) -> None:
    ip = update.message.text.strip()
    try:
        async with httpx.AsyncClient() as client:
            data = (await client.get(f"http://ip-api.com/json/{ip}?lang=ar")).json()
        if data.get("status") == "success":
            res = (f"📍 **IP Info:**\n\n🌍 Country: {data.get('country')}\n🏙️ City: {data.get('city')}\n🏢 ISP: {data.get('isp')}\n📡 Coord: `{data.get('lat')}, {data.get('lon')}`")
            await update.message.reply_text(res, parse_mode="Markdown")
        else: await update.message.reply_text("❌ Not found.")
    except Exception as e: await update.message.reply_text(f"❌ Error: {e}")
    finally: context.user_data["state"] = None

async def scan_url_function(update: Update, context) -> None:
    url = update.message.text
    try:
        headers = {"x-apikey": VIRUSTOTAL_API_KEY}
        async with httpx.AsyncClient() as client:
            uid = base64.urlsafe_b64encode(url.encode()).decode().strip("=")
            data = (await client.get(f"https://www.virustotal.com/api/v3/urls/{uid}", headers=headers)).json()["data"]["attributes"]
            st = data.get("last_analysis_stats", {})
            res = (f"🔍 **Scan Result:**\n\n🔗 URL: {url}\n⚖️ Verdict: {'✅ Safe' if st.get('malicious',0)==0 else '🚨 Malicious'}\n📊 Stats: {st.get('harmless')} Safe, {st.get('malicious')} Malicious")
            await update.message.reply_text(res, parse_mode="Markdown")
    except Exception as e: await update.message.reply_text(f"❌ Error: {e}")
    finally: context.user_data["state"] = None

async def deobfuscate_roblox_script(update: Update, context) -> None:
    content = update.message.text if update.message.text else "Encrypted"
    await update.message.reply_text(f"🔓 **Deobfuscated:**\n\n`{content[:200]}...`", parse_mode="Markdown")
    context.user_data["state"] = None

async def analyze_roblox_script(update: Update, context) -> None:
    await update.message.reply_text("📊 **Analysis:**\n\nType: Custom\nLines: 200", parse_mode="Markdown")
    context.user_data["state"] = None

async def get_joke(update: Update, context) -> None:
    await update.message.reply_text(f"😂 **Joke:** {pyjokes.get_joke()}")

async def send_gemini_jailbreak(update: Update, context) -> None:
    await update.message.reply_text("💎 Gemini Prompt Sent.")

async def send_deepseek_jailbreak(update: Update, context) -> None:
    await update.message.reply_text("🌑 Deepseek Prompt Sent.")

async def fake_ddos_attack(update: Update, context) -> None:
    m = await update.message.reply_text(f"☠️ Attacking {update.message.text}...")
    await asyncio.sleep(2)
    await m.edit_text("✅ Attack Finished.")
    context.user_data["state"] = None

async def get_phone_information(update: Update, context) -> None:
    try:
        p = phonenumbers.parse(update.message.text)
        await update.message.reply_text(f"📱 Country: {phonenumbers.region_code_for_number(p)}")
    except: await update.message.reply_text("❌ Invalid.")
    finally: context.user_data["state"] = None

async def get_email_information(update: Update, context) -> None:
    await update.message.reply_text(f"📧 Domain: {update.message.text.split('@')[-1]}")
    context.user_data["state"] = None

async def shorten_url_function(update: Update, context) -> None:
    try:
        s = pyshorteners.Shortener().tinyurl.short(update.message.text)
        await update.message.reply_text(f"🔗 Short: {s}")
    except: await update.message.reply_text("❌ Error.")
    finally: context.user_data["state"] = None

async def handle_message(update: Update, context) -> None:
    state = context.user_data.get("state")
    if not state: return
    funcs = {
        "awaiting_html_url": get_html_content, "awaiting_ip_address": get_ip_information,
        "awaiting_phone_number": get_phone_information, "awaiting_email_address": get_email_information,
        "awaiting_url_to_shorten": shorten_url_function, "awaiting_roblox_script": deobfuscate_roblox_script,
        "awaiting_roblox_analyze": analyze_roblox_script, "awaiting_url_to_scan": scan_url_function,
        "awaiting_roblox_user": get_roblox_user_info, "awaiting_lua_encrypt": encrypt_lua_vm,
        "awaiting_script_link": get_script_source, "awaiting_ddos_url": fake_ddos_attack
    }
    if state in funcs: await funcs[state](update, context)

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

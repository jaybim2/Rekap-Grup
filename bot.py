"""
WhatsApp Group OCR Extractor - Telegram Bot (dengan Tesseract OCR)
==================================================================
Fitur:
  ✅ Kirim FOTO langsung → bot baca teks otomatis via Tesseract
  ✅ Deteksi Link WhatsApp dari Caption Foto
  ✅ Kirim banyak foto sekaligus (Anti-Spam Debounce)
  ✅ JSON Berwarna (Syntax Highlighting) & Split Message
  ✅ Support: Indonesia, English, Chinese
"""

import json
import re
import logging
import io
import asyncio
import sys
import os
import html
from collections import defaultdict

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)
from PIL import Image
import pytesseract

# ─── CONFIG ────────────────────────────────────────────────────────────────────
BOT_TOKEN = "ISI_TOKEN_ANDA"

def setup_tesseract():
    common_paths = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        r"D:\Tesseract-OCR\tesseract.exe",
        os.path.join(os.environ.get("LOCALAPPDATA", ""), r"Tesseract-OCR\tesseract.exe"),
        r"/usr/bin/tesseract",
    ]
    for path in common_paths:
        if os.path.exists(path):
            pytesseract.pytesseract.tesseract_cmd = path
            logger.info(f"📍 Tesseract ditemukan di: {path}")
            return True
    return False

TESSERACT_LANG = "eng+ind+chi_sim+chi_tra"
PROCESS_WAIT_SECONDS = 3.0

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

photo_buffer = defaultdict(list)
photo_tasks = {}

# ─── UTILS ─────────────────────────────────────────────────────────────────────

def extract_whatsapp_link(text: str) -> str | None:
    if not text: return None
    pattern = r'(https?://chat\.whatsapp\.com/[a-zA-Z0-9?=_\-]+)'
    match = re.search(pattern, text)
    return match.group(1) if match else None

def run_tesseract(image_bytes: bytes) -> str:
    try:
        image = Image.open(io.BytesIO(image_bytes))
        w, h = image.size
        if w < 800:
            scale = 800 / w
            image = image.resize((int(w * scale), int(h * scale)), Image.Resampling.LANCZOS)
        image = image.convert("L")
        text = pytesseract.image_to_string(image, lang=TESSERACT_LANG)
        return text.strip()
    except Exception as e:
        logger.error(f"Tesseract Error: {e}")
        return f"ERROR: {e}"


# ─── CORE EXTRACTION LOGIC ─────────────────────────────────────────────────────

def extract_participant_info(text: str):
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    member_pattern = r'(.*?(?:Grup|Group|members?|participants?| anggota| \u6210\u5458|\u4EBA).*?(\d[\d.,]*)\s*(?:anggota|members?|participants?|[\u6210\u5458\u54E1]|[\u4EBA]).*)'
    
    group_name = None
    member_line = None
    member_count = None

    for i, line in enumerate(lines):
        match = re.search(member_pattern, line, re.IGNORECASE)
        if match:
            member_line = line
            raw_count = match.group(2).replace(',', '').replace('.', '')
            try: member_count = int(raw_count)
            except: pass
            if i > 0:
                potential_name = lines[i-1]
                if not re.search(r'^\d{1,2}[:.]\d{2}', potential_name) and len(potential_name) > 2:
                    group_name = potential_name
            break
            
    if not group_name:
        noise_patterns = [r'^\d{1,2}[:.]\d{2}', r'^\d+$', r'^(WhatsApp|Telegram|LINE)', r'^[\W_]+$', r'^(AM|PM|\d+%)', r'[vaxTll]{2,}']
        for line in lines:
            is_noise = any(re.search(p, line, re.IGNORECASE) for p in noise_patterns)
            is_member_line = re.search(member_pattern, line, re.IGNORECASE)
            if not is_noise and not is_member_line and len(line) >= 2:
                group_name = line
                break
    return group_name, member_line, member_count


def process_ocr_text(image_id: str, ocr_text: str, caption: str = None) -> dict:
    name, line, count = extract_participant_info(ocr_text)
    link = extract_whatsapp_link(caption)
    return {
        "image_id": image_id,
        "group_name": name,
        "participant_count": count,
        "participant_line": line,
        "whatsapp_link": link,
        "raw_ocr": ocr_text,
    }

def process_ocr_items(items: list) -> list:
    return [process_ocr_text(i.get("image_id", "unknown"), i.get("ocr_text", "")) for i in items]


# ─── FORMATTERS ────────────────────────────────────────────────────────────────

def format_results_html(results: list) -> str:
    lines = ["<b>📊 Hasil Ekstraksi OCR WhatsApp</b>\n"]
    lines.append(f"Total: <b>{len(results)} foto</b> diproses\n")
    lines.append("—" * 20)

    for r in results:
        name = html.escape(r.get("group_name") or "Tidak ditemukan")
        count_display = html.escape(r.get("participant_line") or (f"{r.get('participant_count'):,}" if r.get('participant_count') is not None else "Tidak ditemukan"))
        link = r.get("whatsapp_link")
        img_id = html.escape(r.get("image_id", "-"))

        lines.append(f"\n🖼 <b>{img_id}</b>")
        lines.append(f"  📛 Nama Grup : <code>{name}</code>")
        lines.append(f"  👥 Anggota   : <code>{count_display}</code>")
        if link:
            lines.append(f"  🔗 Link      : {link}")

    lines.append("\n" + "—" * 20)
    lines.append("✅ <b>Selesai!</b>")
    return "\n".join(lines)


# ─── PHOTO PROCESSING ──────────────────────────────────────────────────────────

async def process_photos_task(update: Update, context: ContextTypes.DEFAULT_TYPE, photos: list):
    chat_id = update.effective_chat.id
    msg = await context.bot.send_message(chat_id=chat_id, text=f"⏳ Memproses {len(photos)} foto...")

    results = []
    for p in photos:
        try:
            file_bytes = await p["file"].download_as_bytearray()
            ocr_text = await asyncio.to_thread(run_tesseract, bytes(file_bytes))
            result = process_ocr_text(p["image_id"], ocr_text, p["caption"])
            results.append(result)
        except Exception as e:
            logger.error(f"Error OCR {p['image_id']}: {e}")
            results.append({"image_id": p["image_id"], "group_name": None, "whatsapp_link": None, "participant_line": f"ERROR: {e}"})

    await msg.delete()

    # Kirim Laporan Teks (HTML agar aman)
    text_result = format_results_html(results)
    if len(text_result) > 4000:
        for i in range(0, len(results), 10):
            chunk = results[i:i+10]
            await context.bot.send_message(chat_id=chat_id, text=format_results_html(chunk), parse_mode="HTML", disable_web_page_preview=True)
    else:
        await context.bot.send_message(chat_id=chat_id, text=text_result, parse_mode="HTML", disable_web_page_preview=True)

    # Kirim JSON (Markdown agar ada warna/highlighting)
    clean_results = [
        {"image_id": r.get("image_id"), "group_name": r.get("group_name"), "participant_count": r.get("participant_count"), "whatsapp_link": r.get("whatsapp_link")}
        for r in results
    ]
    
    CHUNK_SIZE = 15
    for i in range(0, len(clean_results), CHUNK_SIZE):
        chunk = clean_results[i:i+CHUNK_SIZE]
        json_str = json.dumps(chunk, ensure_ascii=False, indent=2)
        part_info = f" (Bagian {i//CHUNK_SIZE + 1})" if len(clean_results) > CHUNK_SIZE else ""
        
        # Gunakan Markdown untuk Syntax Highlighting
        await context.bot.send_message(
            chat_id=chat_id, 
            text=f"📦 *Output JSON{part_info}:*\n```json\n{json_str}\n```", 
            parse_mode="Markdown"
        )


# ─── HANDLERS ──────────────────────────────────────────────────────────────────

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    message = update.message
    photo = message.photo[-1]
    file = await photo.get_file()
    caption = message.caption
    
    idx = len(photo_buffer[chat_id]) + 1
    photo_buffer[chat_id].append({"image_id": f"foto_{idx}", "file": file, "caption": caption})

    if chat_id in photo_tasks: photo_tasks[chat_id].cancel()

    async def wait_and_process():
        await asyncio.sleep(PROCESS_WAIT_SECONDS)
        photos = photo_buffer.pop(chat_id, [])
        photo_tasks.pop(chat_id, None)
        if photos:
            try: await process_photos_task(update, context, photos)
            except Exception as e: await context.bot.send_message(chat_id=chat_id, text=f"❌ Terjadi kesalahan: {e}")

    photo_tasks[chat_id] = asyncio.create_task(wait_and_process())


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    raw = update.message.text.strip()
    raw = re.sub(r'^```(?:json)?\s*', '', raw, flags=re.MULTILINE)
    raw = re.sub(r'```\s*$', '', raw, flags=re.MULTILINE).strip()

    try:
        data = json.loads(raw)
        if not isinstance(data, list): raise ValueError("Input harus berupa JSON array.")
    except:
        await update.effective_message.reply_text("⚠️ Bukan JSON valid.")
        return

    results = process_ocr_items(data)
    await update.effective_message.reply_text(format_results_html(results), parse_mode="HTML")
    
    clean = [{"image_id": r["image_id"], "group_name": r["group_name"], "participant_count": r["participant_count"], "whatsapp_link": r.get("whatsapp_link")} for r in results]
    json_str = json.dumps(clean, ensure_ascii=False, indent=2)
    await update.effective_message.reply_text(f"📦 *Output JSON:*\n```json\n{json_str}\n```", parse_mode="Markdown")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = "👋 <b>WhatsApp OCR Extractor</b>\n\nKirim foto screenshot info grup!"
    await update.effective_message.reply_text(text, parse_mode="HTML")

async def main_async():
    setup_tesseract()
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    logger.info("🤖 Bot berjalan...")
    async with app:
        await app.initialize(); await app.start(); await app.updater.start_polling()
        while True: await asyncio.sleep(3600)

def main():
    if sys.platform == 'win32': asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    try: asyncio.run(main_async())
    except KeyboardInterrupt: pass

if __name__ == "__main__": main()

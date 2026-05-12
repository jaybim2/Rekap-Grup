# 🤖 WhatsApp OCR Extractor — Telegram Bot

Bot Telegram untuk mengekstrak **nama grup** dan **jumlah anggota**
dari hasil OCR screenshot WhatsApp.

---

## 📦 Instalasi

### 1. Clone / Download
Letakkan semua file dalam satu folder.

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Dapatkan Token Bot
1. Buka Telegram, cari **@BotFather**
2. Ketik `/newbot` dan ikuti instruksi
3. Salin token yang diberikan

### 4. Set Token
Buka `bot.py`, ganti baris ini:
```python
BOT_TOKEN = "ISI_TOKEN_BOT_TELEGRAM_ANDA"
```
dengan token Anda:
```python
BOT_TOKEN = "1234567890:ABCdefGHIjklMNOpqrSTUvwxYZ"
```

### 5. Jalankan Bot
```bash
python bot.py
```

---

## 🚀 Cara Pakai

Kirimkan JSON array ke bot:

```json
[
  {
    "image_id": "img_1",
    "ocr_text": "Komunitas Python Indonesia\n1234 anggota\n09:41"
  },
  {
    "image_id": "img_2",
    "ocr_text": "Tech News Group\n89 members"
  }
]
```

Bot akan membalas dengan:
- **Hasil teks** yang rapi
- **Output JSON** terstruktur

---

## 📋 Perintah Bot

| Perintah   | Fungsi                    |
|------------|---------------------------|
| `/start`   | Halaman utama             |
| `/help`    | Panduan penggunaan        |
| `/example` | Contoh format input/output|

---

## 🌐 Bahasa yang Didukung

| Bahasa              | Pola                        |
|---------------------|-----------------------------|
| 🇮🇩 Indonesia        | `123 anggota`               |
| 🇺🇸 English          | `123 members / participants`|
| 🇨🇳 Chinese Simplified | `123 成员 / 123 人`        |
| 🇹🇼 Chinese Traditional | `123 成員`               |

---

## ☁️ Deploy ke Server (Opsional)

### Menggunakan Railway / Render / VPS:
```bash
# Contoh dengan systemd (VPS)
[Unit]
Description=WhatsApp OCR Telegram Bot

[Service]
ExecStart=/usr/bin/python3 /path/to/bot.py
Restart=always

[Install]
WantedBy=multi-user.target
```

### Menggunakan Docker:
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY bot.py .
CMD ["python", "bot.py"]
```

---

## 📁 Struktur File

```
whatsapp_ocr_bot/
├── bot.py           ← File utama bot
├── requirements.txt ← Dependencies
└── README.md        ← Panduan ini
```

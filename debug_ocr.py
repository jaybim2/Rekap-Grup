import sys
import os
import io
import re
from PIL import Image
import pytesseract

# Konfigurasi Tesseract (Sesuaikan jika berbeda)
TESSERACT_CMD = r"D:\Tesseract-OCR\tesseract.exe"
pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD
TESSERACT_LANG = "eng+ind+chi_sim+chi_tra"

def run_tesseract(image_path):
    """Jalankan OCR pada file gambar dan tampilkan prosesnya."""
    if not os.path.exists(image_path):
        print(f"File tidak ditemukan: {image_path}")
        return None

    print(f"Memproses gambar: {image_path}")
    image = Image.open(image_path)

    # Pre-processing sederhana (sama seperti di bot.py)
    w, h = image.size
    if w < 800:
        scale = 800 / w
        image = image.resize((int(w * scale), int(h * scale)), Image.Resampling.LANCZOS)
    
    image = image.convert("L")
    
    print("Menjalankan Tesseract OCR...")
    text = pytesseract.image_to_string(image, lang=TESSERACT_LANG)
    return text.strip()

def extract_participant_info(text):
    """
    Ekstrak Nama Grup dan Jumlah Anggota secara bersamaan.
    Strategi: Cari baris 'Grup - X anggota' dan ambil baris di atasnya sebagai nama grup.
    """
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    
    # Regex untuk mencari baris info anggota (misal: "Grup - 121 anggota" atau "121 anggota")
    member_pattern = r'(.*?(?:Grup|Group|members?|participants?| anggota| \u6210\u5458|\u4EBA).*?(\d[\d.,]*)\s*(?:anggota|members?|participants?|[\u6210\u5458\u54E1]|[\u4EBA]).*)'
    
    group_name = None
    member_line = None
    member_count = None

    for i, line in enumerate(lines):
        match = re.search(member_pattern, line, re.IGNORECASE)
        if match:
            member_line = line
            raw_count = match.group(2).replace(',', '').replace('.', '')
            try:
                member_count = int(raw_count)
            except:
                pass
            
            if i > 0:
                potential_name = lines[i-1]
                # Filter status bar (jam)
                if not re.search(r'^\d{1,2}[:.]\d{2}', potential_name) and len(potential_name) > 2:
                    group_name = potential_name
            break
            
    if not group_name:
        noise_patterns = [
            r'^\d{1,2}[:.]\d{2}',
            r'^\d+$',
            r'^(WhatsApp|Telegram|LINE)',
            r'^[\W_]+$',
            r'^(AM|PM|\d+%)',
            r'[vaxTll]{2,}',
        ]
        for line in lines:
            is_noise = any(re.search(p, line, re.IGNORECASE) for p in noise_patterns)
            is_member_line = re.search(member_pattern, line, re.IGNORECASE)
            if not is_noise and not is_member_line and len(line) >= 2:
                group_name = line
                break

    return group_name, member_line, member_count

def main():
    if len(sys.argv) < 2:
        print("Usage: python debug_ocr.py <path_ke_gambar>")
        return

    img_path = sys.argv[1]
    raw_text = run_tesseract(img_path)

    if raw_text:
        print("\n" + "="*50)
        print("RAW OCR TEXT (Apa yang dilihat Bot):")
        print("="*50)
        print(raw_text)
        print("="*50)

        name, line, count = extract_participant_info(raw_text)

        print("\nHASIL EKSTRAKSI:")
        print(f"Nama Grup : {name if name else '[TIDAK DITEMUKAN]'}")
        print(f"Anggota   : {line if line else '[TIDAK DITEMUKAN]'}")
        print(f"Angka Saja: {count if count is not None else '-'}")
        print("="*50)

if __name__ == "__main__":
    main()

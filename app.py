"""
DocScan OCR — Backend API (Step 2: OpenCV + Gemini AI)
======================================================
FastAPI server ที่รับภาพเอกสาร → Smart Crop ด้วย OpenCV → วิเคราะห์ด้วย Gemini AI → ส่ง JSON กลับ.

Run:  uvicorn app:app --reload
Docs: http://127.0.0.1:8000/docs
"""

import sys
import io
import os
import logging
import time
import json
import re
from dotenv import load_dotenv

# ── Fix Windows terminal encoding (cp1252 → utf-8) ──
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import cv2
import numpy as np
import base64
import traceback

import google.generativeai as genai

# ── นำเข้า Image Processing Pipeline ──
from utils.image_proces import smart_crop

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 🔑 GEMINI API KEY — ใส่ API Key ของคุณตรงนี้!
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# วิธีขอ API Key: ไปที่ https://aistudio.google.com/apikey
#
# วิธีที่ 1: ใส่ตรงๆ ในโค้ด (สะดวก แต่ไม่ปลอดภัยถ้า push ขึ้น Git)
#   GEMINI_API_KEY = "AIzaSy..."
#
# วิธีที่ 2: ตั้ง Environment Variable (แนะนำ!)
#   Windows CMD:   set GEMINI_API_KEY=AIzaSy...
#   Windows PS:    $env:GEMINI_API_KEY="AIzaSy..."
#   Linux/Mac:     export GEMINI_API_KEY=AIzaSy...
#
# โหลดค่าจากไฟล์ key.env
load_dotenv("key.env")

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Logging Setup
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(stream=sys.stdout)],
)
logger = logging.getLogger("ocr-engine")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Gemini AI — Configuration
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
GEMINI_MODEL_NAME = "gemini-2.5-flash"
gemini_model = None  # จะ init ตอน startup

# Prompt ที่ส่งให้ Gemini วิเคราะห์เอกสาร
GEMINI_PROMPT = """นี่คือภาพเอกสาร จงวิเคราะห์ว่าเป็นเอกสารประเภทใด และจัดกลุ่มข้อความตามโครงสร้างที่เหมาะสม พร้อมทั้งจับประเด็นหัวข้อที่สำคัญของเอกสารนั้นๆแยกเป็นข้อ

คืนค่าเป็น JSON เท่านั้น ห้ามมี Markdown format ครอบ (ห้ามใส่ ```json หรือ ``` ใดๆ)

โครงสร้าง JSON ที่ต้องการ:
{
  "document_type": "ประเภทเอกสาร เช่น receipt, invoice, id_card, letter, form, contract, certificate, report, other",
  "document_type_th": "ชื่อประเภทเป็นภาษาไทย",
  "confidence": 0.95,
  "tags": ["#Receipt", "#Has_Date", "#Has_Total_Amount"],
  "language": "th หรือ en หรือ mixed",
  "extracted_text": "ข้อความทั้งหมดที่อ่านได้จากเอกสาร คั่นด้วย newline",
  "structured_data": {
    "title": "หัวข้อเอกสาร (ถ้ามี)",
    "date": "วันที่ (ถ้ามี)",
    "total_amount": "ยอดรวม (ถ้ามี)",
    "company_name": "ชื่อบริษัท/ร้านค้า (ถ้ามี)",
    "items": ["รายการ 1", "รายการ 2"],
    "other_fields": {}
  },
  "tag_mapping": [
    {
      "tag": "#Has_Date",
      "exact_text": "ข้อความดิบที่ตรงกับ tag นี้เป๊ะๆ ที่ปรากฏใน extracted_text (ใช้สำหรับไฮไลต์)",
      "target_key": "date"
    }
  ],
  "summary": "สรุปเนื้อหาเอกสารใน 1-2 ประโยค"
}

กรุณาอ่านทุกตัวอักษรในภาพให้ครบถ้วน ทั้งภาษาไทยและอังกฤษ"""

# Default fallback structure เมื่อ Gemini ใช้ไม่ได้
FALLBACK_DOCUMENT_DATA = {
    "document_type": "unknown",
    "document_type_th": "ไม่สามารถระบุได้",
    "confidence": 0.0,
    "tags": ["#General_Document"],
    "language": "unknown",
    "extracted_text": "",
    "structured_data": {
        "title": None,
        "date": None,
        "total_amount": None,
        "company_name": None,
        "items": [],
        "other_fields": {},
    },
    "tag_mapping": [],
    "summary": "ไม่สามารถวิเคราะห์เอกสารได้ (Gemini API ไม่พร้อมใช้งาน)",
    "ai_error": None,
}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# FastAPI App
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
app = FastAPI(
    title="DocScan OCR Engine",
    description="AI-powered document scanner with Smart Crop & Gemini OCR",
    version="2.1.0",
)

# ── CORS — อนุญาตให้ Frontend ที่อยู่คนละ Port เรียกได้ ──
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Startup Event — Initialize Gemini

@app.on_event("startup")
async def startup_event():
    """Initialize Gemini model เมื่อ server เริ่มทำงาน."""
    global gemini_model

    logger.info("=" * 50)
    logger.info("DocScan OCR Engine v2.1 — Starting up...")

    if GEMINI_API_KEY == "YOUR_API_KEY_HERE" or not GEMINI_API_KEY:
        logger.warning("GEMINI_API_KEY not set! AI analysis will return fallback data.")
        logger.warning("  Set via: $env:GEMINI_API_KEY=\"your-key\" (PowerShell)")
        logger.warning("  Or edit GEMINI_API_KEY in app.py directly")
        gemini_model = None
    else:
        try:
            genai.configure(api_key=GEMINI_API_KEY)
            gemini_model = genai.GenerativeModel(GEMINI_MODEL_NAME)
            logger.info(f"Gemini AI model '{GEMINI_MODEL_NAME}' initialized successfully!")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini: {e}")
            gemini_model = None

    logger.info("Server is ready!")
    logger.info("=" * 50)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Helper: OpenCV image → JPEG bytes (สำหรับส่ง Gemini)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def image_to_jpeg_bytes(image: np.ndarray, quality: int = 85) -> bytes:
    """แปลง numpy image เป็น JPEG bytes สำหรับส่งให้ Gemini API."""
    encode_params = [cv2.IMWRITE_JPEG_QUALITY, quality]
    success, buffer = cv2.imencode(".jpg", image, encode_params)
    if not success:
        raise ValueError("Failed to encode image to JPEG bytes")
    return buffer.tobytes()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Helper: แปลง OpenCV image → Base64 data URI
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def encode_image_to_base64(image: np.ndarray, quality: int = 90) -> str:
    """
    แปลง numpy image เป็น Base64 data URI (JPEG).

    Returns:
        data URI string เช่น "data:image/jpeg;base64,/9j/4AAQ..."
    """
    encode_params = [cv2.IMWRITE_JPEG_QUALITY, quality]
    success, buffer = cv2.imencode(".jpg", image, encode_params)
    if not success:
        raise ValueError("Failed to encode image to JPEG")

    b64_str = base64.b64encode(buffer).decode("utf-8")
    return f"data:image/jpeg;base64,{b64_str}"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Helper: เรียก Gemini API วิเคราะห์เอกสาร
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def clean_gemini_response(raw_text: str) -> str:
    """
    ทำความสะอาด response จาก Gemini:
    - ลบ ```json ... ``` wrapper ออก
    - ลบ whitespace ที่ไม่จำเป็น
    """
    text = raw_text.strip()

    # ลบ markdown code block wrapper (```json ... ``` หรือ ``` ... ```)
    text = re.sub(r"^```(?:json)?\s*\n?", "", text)
    text = re.sub(r"\n?```\s*$", "", text)

    return text.strip()


def analyze_with_gemini(image: np.ndarray) -> dict:
    """
    ส่งรูปภาพไปให้ Gemini AI วิเคราะห์เอกสาร.

    Args:
        image: OpenCV BGR image (numpy array) ที่ผ่าน Smart Crop แล้ว

    Returns:
        dict — ข้อมูลเอกสารที่ Gemini วิเคราะห์ได้ หรือ fallback structure ถ้า error

    Error Handling:
        - ถ้า API Key ไม่ได้ตั้ง → return fallback พร้อม error message
        - ถ้า Gemini ตอบไม่ใช่ JSON → พยายาม parse อีกรอบ → ถ้าไม่ได้ก็ return fallback
        - ถ้า network error → return fallback
    """
    if gemini_model is None:
        logger.warning("[Gemini] Model not initialized — returning fallback")
        fallback = FALLBACK_DOCUMENT_DATA.copy()
        fallback["ai_error"] = "Gemini API key not configured"
        return fallback

    try:
        # ── 1. แปลง image → JPEG bytes ──
        img_bytes = image_to_jpeg_bytes(image, quality=85)
        logger.info(f"[Gemini] Sending image ({len(img_bytes) / 1024:.1f} KB) to {GEMINI_MODEL_NAME}...")

        # ── 2. สร้าง image part สำหรับ Gemini ──
        image_part = {
            "mime_type": "image/jpeg",
            "data": img_bytes,
        }

        # ── 3. เรียก Gemini API ──
        gemini_start = time.time()
        response = gemini_model.generate_content(
            [image_part, GEMINI_PROMPT],
            generation_config=genai.types.GenerationConfig(
                temperature=0.1,        # ต่ำ = ตอบตรงตาม prompt มากขึ้น
                max_output_tokens=4096,
            ),
        )
        gemini_elapsed = round((time.time() - gemini_start) * 1000)
        logger.info(f"[Gemini] Response received in {gemini_elapsed}ms")

        # ── 4. ดึง text response ──
        raw_text = response.text
        if not raw_text:
            logger.warning("[Gemini] Empty response from API")
            fallback = FALLBACK_DOCUMENT_DATA.copy()
            fallback["ai_error"] = "Gemini returned empty response"
            return fallback

        # ── 5. ทำความสะอาดและ Parse JSON ──
        cleaned = clean_gemini_response(raw_text)
        logger.info(f"[Gemini] Raw response (first 200 chars): {cleaned[:200]}")

        try:
            document_data = json.loads(cleaned)
            logger.info(f"[Gemini] Parsed successfully — type: {document_data.get('document_type', 'N/A')}")
            # เพิ่ม metadata
            document_data["gemini_processing_time_ms"] = gemini_elapsed
            return document_data

        except json.JSONDecodeError as je:
            logger.error(f"[Gemini] JSON parse failed: {je}")
            logger.error(f"[Gemini] Raw text was: {cleaned[:500]}")
            # Fallback: ใส่ raw text ไว้ใน extracted_text แทน
            fallback = FALLBACK_DOCUMENT_DATA.copy()
            fallback["extracted_text"] = cleaned
            fallback["ai_error"] = f"Gemini response was not valid JSON: {str(je)}"
            fallback["summary"] = "AI ตอบกลับมาแต่ไม่ใช่ JSON — ข้อความดิบอยู่ใน extracted_text"
            return fallback

    except Exception as e:
        logger.error(f"[Gemini] API call failed: {e}")
        traceback.print_exc()
        fallback = FALLBACK_DOCUMENT_DATA.copy()
        fallback["ai_error"] = f"Gemini API error: {str(e)}"
        return fallback


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Allowed file extensions & validation
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff", ".tif"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


def validate_upload(file: UploadFile, contents: bytes) -> None:
    """ตรวจสอบไฟล์ที่อัปโหลดก่อนประมวลผล."""
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File too large ({len(contents) / 1024 / 1024:.1f} MB). Max: {MAX_FILE_SIZE / 1024 / 1024:.0f} MB",
        )

    filename = (file.filename or "").lower()
    ext = "." + filename.rsplit(".", 1)[-1] if "." in filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: '{ext}'. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# API Endpoint: POST /api/scan
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@app.post("/api/scan")
async def scan_document(file: UploadFile = File(...)):
    """
    รับภาพเอกสาร → Smart Crop → Gemini AI วิเคราะห์ → Return JSON.

    Pipeline:
      1. Validate ไฟล์ (ขนาด, นามสกุล)
      2. Decode เป็น OpenCV image
      3. Smart Crop (Resize → Edge → Corner → Perspective Transform)
      4. ส่งภาพให้ Gemini AI วิเคราะห์ OCR + จัดหมวดหมู่
      5. Encode ภาพเป็น Base64
      6. Return ทั้ง processed_image_base64 + document_data

    Response JSON:
      {
        "status": "success",
        "message": "...",
        "processing_time_ms": 1234,
        "processed_image_base64": "data:image/jpeg;base64,...",
        "document_data": { ... Gemini analysis result ... }
      }
    """
    start_time = time.time()

    try:
        logger.info(f"{'='*50}")
        logger.info(f"Incoming file: {file.filename}")

        # ── 1. Read & Validate ──
        contents = await file.read()
        validate_upload(file, contents)
        logger.info(f"  File size: {len(contents) / 1024:.1f} KB")

        # ── 2. Decode to OpenCV image ──
        nparr = np.frombuffer(contents, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if img is None:
            raise HTTPException(
                status_code=400,
                detail="Cannot decode image. File may be corrupted or not a valid image.",
            )

        orig_h, orig_w = img.shape[:2]
        logger.info(f"  Original size: {orig_w}x{orig_h}")

        # ── 3. Smart Crop (OpenCV pipeline) ──
        processed_img, crop_message = smart_crop(img)
        proc_h, proc_w = processed_img.shape[:2]
        logger.info(f"  Processed size: {proc_w}x{proc_h}")
        logger.info(f"  Crop status: {crop_message}")

        # ── 4. Gemini AI Analysis ──
        document_data = analyze_with_gemini(processed_img)

        # ── 5. Encode processed image to Base64 ──
        img_base64 = encode_image_to_base64(processed_img, quality=90)

        # ── 6. Calculate total timing ──
        elapsed_ms = round((time.time() - start_time) * 1000)
        logger.info(f"  Total processing time: {elapsed_ms}ms")
        logger.info(f"{'='*50}")

        return JSONResponse(
            content={
                "status": "success",
                "message": crop_message,
                "original_size": {"width": orig_w, "height": orig_h},
                "processed_size": {"width": proc_w, "height": proc_h},
                "processing_time_ms": elapsed_ms,
                "processed_image_base64": img_base64,
                "document_data": document_data,
            },
            media_type="application/json; charset=utf-8",
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "error": f"Internal Server Error: {str(e)}",
            },
        )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Health Check
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@app.get("/")
async def health_check():
    """ตรวจสอบสถานะ server และ Gemini AI."""
    return {
        "status": "online",
        "engine": "DocScan OCR v2.1",
        "gemini_model": GEMINI_MODEL_NAME,
        "gemini_ready": gemini_model is not None,
        "endpoints": ["/api/scan"],
    }
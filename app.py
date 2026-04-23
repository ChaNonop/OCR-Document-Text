import sys
import io
import os
import logging
import time
import json
import re

# Fix Windows terminal encoding
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import cv2
import numpy as np
import base64
import traceback

from google import genai
from google.genai import types

from utils.image_proces import smart_crop

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# API KEY — โหลดจาก key.env (Local) หรือ Environment Variable (Railway)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
try:
    from dotenv import load_dotenv
    load_dotenv("key.env", override=False)
except ImportError:
    pass  # บน Railway ไม่จำเป็นต้องใช้ dotenv

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
# Gemini AI — Configuration (New SDK: google-genai)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
GEMINI_MODEL_NAME = "gemini-2.5-flash"
gemini_client = None  # จะ init ตอน startup

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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    global gemini_client

    logger.info("=" * 50)
    logger.info("DocScan OCR Engine v2.1 — Starting up...")

    if not GEMINI_API_KEY:
        logger.warning("GEMINI_API_KEY not set! AI analysis will return fallback data.")
        gemini_client = None
    else:
        try:
            gemini_client = genai.Client(api_key=GEMINI_API_KEY)
            logger.info(f"Gemini AI client initialized — model: '{GEMINI_MODEL_NAME}'")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini client: {e}")
            gemini_client = None

    logger.info("Server is ready!")
    logger.info("=" * 50)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Helpers
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def image_to_jpeg_bytes(image: np.ndarray, quality: int = 85) -> bytes:
    encode_params = [cv2.IMWRITE_JPEG_QUALITY, quality]
    success, buffer = cv2.imencode(".jpg", image, encode_params)
    if not success:
        raise ValueError("Failed to encode image to JPEG bytes")
    return buffer.tobytes()


def encode_image_to_base64(image: np.ndarray, quality: int = 90) -> str:
    encode_params = [cv2.IMWRITE_JPEG_QUALITY, quality]
    success, buffer = cv2.imencode(".jpg", image, encode_params)
    if not success:
        raise ValueError("Failed to encode image to JPEG")
    b64_str = base64.b64encode(buffer).decode("utf-8")
    return f"data:image/jpeg;base64,{b64_str}"


def clean_gemini_response(raw_text: str) -> str:
    text = raw_text.strip()
    text = re.sub(r"^```(?:json)?\s*\n?", "", text)
    text = re.sub(r"\n?```\s*$", "", text)
    return text.strip()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Gemini API Call (New SDK)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def analyze_with_gemini(image: np.ndarray) -> dict:
    if gemini_client is None:
        logger.warning("[Gemini] Client not initialized — returning fallback")
        fallback = FALLBACK_DOCUMENT_DATA.copy()
        fallback["ai_error"] = "Gemini API key not configured"
        return fallback

    try:
        img_bytes = image_to_jpeg_bytes(image, quality=85)
        logger.info(f"[Gemini] Sending image ({len(img_bytes) / 1024:.1f} KB) to {GEMINI_MODEL_NAME}...")

        # สร้าง image part สำหรับ google-genai SDK ใหม่
        image_part = types.Part.from_bytes(data=img_bytes, mime_type="image/jpeg")

        gemini_start = time.time()
        response = gemini_client.models.generate_content(
            model=GEMINI_MODEL_NAME,
            contents=[image_part, GEMINI_PROMPT],
            config=types.GenerateContentConfig(
                temperature=0.1,
                max_output_tokens=4096,
            ),
        )
        gemini_elapsed = round((time.time() - gemini_start) * 1000)
        logger.info(f"[Gemini] Response received in {gemini_elapsed}ms")

        raw_text = response.text
        if not raw_text:
            logger.warning("[Gemini] Empty response from API")
            fallback = FALLBACK_DOCUMENT_DATA.copy()
            fallback["ai_error"] = "Gemini returned empty response"
            return fallback

        cleaned = clean_gemini_response(raw_text)
        logger.info(f"[Gemini] Raw response (first 200 chars): {cleaned[:200]}")

        try:
            document_data = json.loads(cleaned)
            logger.info(f"[Gemini] Parsed successfully — type: {document_data.get('document_type', 'N/A')}")
            document_data["gemini_processing_time_ms"] = gemini_elapsed
            return document_data
        except json.JSONDecodeError as je:
            logger.error(f"[Gemini] JSON parse failed: {je}")
            logger.error(f"[Gemini] Raw text was: {cleaned[:500]}")
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
# File Validation
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff", ".tif"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


def validate_upload(file: UploadFile, contents: bytes) -> None:
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
    start_time = time.time()

    try:
        logger.info(f"{'='*50}")
        logger.info(f"Incoming file: {file.filename}")

        contents = await file.read()
        validate_upload(file, contents)
        logger.info(f"  File size: {len(contents) / 1024:.1f} KB")

        nparr = np.frombuffer(contents, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if img is None:
            raise HTTPException(
                status_code=400,
                detail="Cannot decode image. File may be corrupted or not a valid image.",
            )

        orig_h, orig_w = img.shape[:2]
        logger.info(f"  Original size: {orig_w}x{orig_h}")

        processed_img, crop_message = smart_crop(img)
        proc_h, proc_w = processed_img.shape[:2]
        logger.info(f"  Processed size: {proc_w}x{proc_h}")
        logger.info(f"  Crop status: {crop_message}")

        document_data = analyze_with_gemini(processed_img)

        img_base64 = encode_image_to_base64(processed_img, quality=90)

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

@app.get("/api/health")
async def health_check():
    return {
        "status": "online",
        "engine": "DocScan OCR v2.1",
        "gemini_model": GEMINI_MODEL_NAME,
        "gemini_ready": gemini_client is not None,
        "endpoints": ["/api/scan"],
    }

@app.get("/")
async def serve_frontend():
    return FileResponse("web/index.html")

# Serve static files (CSS, JS, images) from /web
app.mount("/web", StaticFiles(directory="web"), name="static")
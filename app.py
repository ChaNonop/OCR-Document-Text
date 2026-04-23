import sys
import io
import logging

# === Fix Windows terminal encoding (cp1252 -> utf-8) ===
# This prevents UnicodeEncodeError when printing Thai/Unicode text
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import cv2
import numpy as np
import easyocr
import re
import base64
import traceback # เพิ่มตัวช่วยแสดง Error อย่างละเอียด

# === Setup Logging ===
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(stream=sys.stdout)]
)
logger = logging.getLogger("ocr-engine")

# นำเข้าฟังก์ชันจากไฟล์ utils
from utils.image_proces import detect_edges, find_document_corners, four_point_transform

app = FastAPI(title="OCR Document Engine")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logger.info("Loading EasyOCR model (Thai + English)...")
reader = easyocr.Reader(['th', 'en'])
logger.info("Model loaded successfully! Server is ready.")

def generate_tags(text_list):
    tags = []
    full_text = " ".join(text_list).lower()

    if re.search(r'invoice|ใบแจ้งหนี้|tax', full_text):
        tags.append("#Invoice")
    elif re.search(r'receipt|ใบเสร็จ|cash', full_text):
        tags.append("#Receipt")
    
    if re.search(r'date|วันที่|\d{2}/\d{2}/\d{4}', full_text):
        tags.append("#Has_Date")
        
    if re.search(r'total|net|ยอดรวม|สุทธิ', full_text):
        tags.append("#Has_Total_Amount")

    if not tags:
        tags.append("#General_Document")
        
    return tags

@app.post("/api/upload")
async def process_document(file: UploadFile = File(...)):
    try:
        logger.info(f"--- Processing file: {file.filename} ---")
        
        # 1. รับไฟล์
        contents = await file.read()
        nparr = np.frombuffer(contents, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if img is None:
             return JSONResponse(status_code=400, content={"error": "Invalid image file or corrupted data"})
        logger.info("Step 1: Image loaded successfully")

        # 2. กระบวนการ OpenCV
        _, edge_img = detect_edges(img)
        corners = find_document_corners(edge_img)
        logger.info("Step 2: Edge detection completed")

        # ป้องกันบัค! ถ้าหาขอบไม่เจอ ให้ใช้รูปเดิม
        if corners is not None:
            processed_img = four_point_transform(img, corners)
            status_msg = "AI cropped and aligned the document successfully"
            logger.info("Step 3: Document cropped and perspective-corrected")
        else:
            processed_img = img.copy() # ใช้รูปต้นฉบับ
            status_msg = "No clear document edges found, using original image"
            logger.info("Step 3: No 4-corner found, skipping crop")

        # 3. กระบวนการ EasyOCR
        extracted_texts = reader.readtext(processed_img, detail=0)
        
        # เพิ่ม Fallback: ถ้ารูปที่ตัดขอบหาข้อความไม่เจอเลย อาจจะเพราะตัดผิดส่วน ให้ลองใช้รูปต้นฉบับ
        if len(extracted_texts) == 0 and corners is not None:
            logger.warning("Step 4.1: No text found in cropped image. Falling back to original image.")
            processed_img = img.copy()
            extracted_texts = reader.readtext(processed_img, detail=0)
            status_msg = "No text found in cropped area, reverted to original image"

        logger.info(f"Step 4: OCR completed — extracted {len(extracted_texts)} text blocks")

        # 4. จัดหมวดหมู่
        document_tags = generate_tags(extracted_texts)
        logger.info(f"Step 5: Tags generated: {document_tags}")

        # 5. แปลงรูปลง Base64
        success, buffer = cv2.imencode('.jpg', processed_img)
        if not success:
            raise Exception("Failed to encode processed image to Base64")
        
        img_base64 = base64.b64encode(buffer).decode('utf-8')
        logger.info("Step 6: Base64 image encoding done")

        logger.info("Processing complete! Sending response to frontend.")
        return JSONResponse(
            content={
                "status": "success",
                "message": status_msg,
                "tags": document_tags,
                "texts": extracted_texts,
                "processed_image_base64": f"data:image/jpeg;base64,{img_base64}"
            },
            media_type="application/json; charset=utf-8"
        )

    except Exception as e:
        logger.error(f"Critical error (500): {str(e)}")
        traceback.print_exc() # พิมพ์รายละเอียดว่าพังที่บรรทัดไหนใน Terminal
        return JSONResponse(status_code=500, content={"error": f"Internal Server Error: {str(e)}"})
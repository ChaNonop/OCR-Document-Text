from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import cv2
import numpy as np
import easyocr
import re
import base64
from fastapi.middleware.cors import CORSMiddleware

# นำเข้าฟังก์ชันจากไฟล์ utils
from utils.image_proces import detect_edges, find_document_corners, four_point_transform

app = FastAPI(title="OCR Document Engine")

# เพิ่ม / ตรวจสอบส่วนนี้ให้ดีครับ
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # อนุญาตให้เว็บจากทุกที่เข้าถึงได้ (สำคัญมากตอนทดสอบ)
    allow_credentials=True,
    allow_methods=["*"], # อนุญาตทั้ง GET, POST 
    allow_headers=["*"], 
)

print("กำลังโหลดโมเดล AI ภาษาไทยและอังกฤษ...")

# โหลดโมเดล EasyOCR (ตั้งไว้ด้านนอกจะได้ไม่ต้องโหลดใหม่ทุกครั้งที่อัปโหลดรูป)
reader = easyocr.Reader(['th', 'en'])
print("โหลดโมเดลสำเร็จ! เซิร์ฟเวอร์พร้อมใช้งาน")

def generate_tags(text_list):
    """ฟังก์ชันจัดหมวดหมู่ข้อความและสร้าง Tags"""
    tags = []
    full_text = " ".join(text_list).lower()

    # กฎการแยกหมวดหมู่ (แก้ไขเพิ่มเติมได้ตามต้องการ)
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
        # 1. รับไฟล์รูปภาพและแปลงให้ OpenCV อ่านได้
        contents = await file.read()
        nparr = np.frombuffer(contents, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if img is None:
             return JSONResponse(status_code=400, content={"error": "ไม่สามารถอ่านไฟล์รูปภาพได้"})

        # 2. กระบวนการตัดขอบรูปภาพ (OpenCV)
        _, edge_img = detect_edges(img)
        corners = find_document_corners(edge_img)

        if corners is not None:
            # ถ้าหาขอบเจอ ให้ทำการดัดและตัดภาพ
            processed_img = four_point_transform(img, corners)
            status_msg = "ค้นหาขอบและตัดเอกสารสำเร็จ"
        else:
            # ถ้าหาไม่เจอ ให้ใช้รูปเดิม
            processed_img = img
            status_msg = "หาขอบไม่พบ ทำการอ่านข้อความจากภาพต้นฉบับ"

        # 3. กระบวนการอ่านข้อความ (EasyOCR)
        # นำรูปที่ตัดแล้วส่งให้ AI อ่าน (detail=0 คือเอาแค่ตัวหนังสือ ไม่เอาพิกัดกล่อง)
        extracted_texts = reader.readtext(processed_img, detail=0)

        # 4. จัดหมวดหมู่สร้าง Tags
        document_tags = generate_tags(extracted_texts)

        # 5. แปลงรูปภาพที่ตัดแล้วกลับเป็น Base64 เพื่อส่งกลับไปแสดงที่หน้าเว็บ
        _, buffer = cv2.imencode('.jpg', processed_img)
        img_base64 = base64.b64encode(buffer).decode('utf-8')

        # ส่งผลลัพธ์ทั้งหมดกลับไป!
        return {
            "status": "success",
            "message": status_msg,
            "tags": document_tags,
            "texts": extracted_texts,
            "processed_image_base64": f"data:image/jpeg;base64,{img_base64}"
        }

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
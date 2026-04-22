from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse
import cv2
import numpy as np

# นำเข้าฟังก์ชันจากไฟล์ของคุณ
from utils.image_proces import detect_edges, find_document_corners

app = FastAPI(title="OCR Document Categorizer API")

@app.get("/")
def read_root():
    return {"message": "API is Ready"}

@app.post("/upload-document/")
async def upload_document(file: UploadFile = File(...)):
    """จุดรับไฟล์รูปภาพจากหน้าเว็บ"""
    try:
        # 1. อ่านไฟล์ที่ส่งมาจากหน้าเว็บให้เป็น Bytes
        contents = await file.read()
        
        # 2. แปลง Bytes ให้กลายเป็นตัวเลข Matrix เพื่อให้ OpenCV อ่านเข้าใจ
        nparr = np.frombuffer(contents, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if img is None:
             return JSONResponse(status_code=400, content={"error": "ไฟล์ที่อัปโหลดไม่ใช่รูปภาพที่ถูกต้อง"})

        # 3. ส่งรูปเข้าไปหากระบวนการ OpenCV ที่เราเขียนไว้
        enhanced_img, edge_img = detect_edges(img)
        corners = find_document_corners(edge_img)
        
        if corners is not None:
            message = "พบเอกสาร 4 มุมเรียบร้อยแล้ว เตรียมตัดภาพ!"
            # (เดี๋ยวเราจะเขียนโค้ด "ดัดและตัดภาพ" ใส่ตรงนี้ในสเตปถัดไป)
        else:
            message = "หาขอบเอกสารไม่เจอ กรุณาถ่ายรูปในมุมที่เห็นขอบชัดเจนขึ้น"

        return {
            "filename": file.filename,
            "status": message
        }

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
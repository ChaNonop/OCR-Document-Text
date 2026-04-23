import cv2
import numpy as np

def brightness_contrast(gray_image):
    mean_brightness = np.mean(gray_image)
    if mean_brightness < 90:
        adjust = cv2.convertScaleAbs(gray_image, alpha=1.2, beta=30)
    elif mean_brightness > 200:
        adjust = cv2.convertScaleAbs(gray_image, alpha=0.8, beta=-30)
    else:
        adjust = gray_image
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    return clahe.apply(adjust)

def detect_edges(image):
    gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) 
    enhanced_image = brightness_contrast(gray_image) 
    blurred_image = cv2.GaussianBlur(enhanced_image, (5, 5), 0) 
    edge = cv2.Canny(blurred_image, 75, 200) 
    return enhanced_image, edge

def find_document_corners(edged_image, original_image=None):
    """
    หา 4 มุมของเอกสารจากภาพ edge
    เพิ่ม: ตรวจสอบว่า contour ที่เจอต้องมีขนาดอย่างน้อย 5% ของภาพทั้งหมด
    เพื่อป้องกันการ crop ผิดส่วน (เช่น เจอ contour เล็กๆ ที่ไม่ใช่ขอบเอกสาร)
    """
    contours, _ = cv2.findContours(edged_image.copy(), cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    contours = sorted(contours, key=cv2.contourArea, reverse=True)[:5]

    # คำนวณ minimum area threshold (5% ของภาพทั้งหมด)
    img_h, img_w = edged_image.shape[:2]
    total_area = img_h * img_w
    min_area = total_area * 0.05  # contour ต้องใหญ่กว่า 5% ของภาพ

    for c in contours:
        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.02 * peri, True)
        if len(approx) == 4:
            # ตรวจสอบว่า contour ใหญ่พอเป็นเอกสาร
            contour_area = cv2.contourArea(approx)
            if contour_area >= min_area:
                return approx
    return None

def order_points(pts):
    """เรียงลำดับจุด 4 มุม: บนซ้าย, บนขวา, ล่างขวา, ล่างซ้าย"""
    pts = pts.reshape(4, 2) # เพิ่มบรรทัดนี้: รีเชปพิกัดก่อนคำนวณเพื่อป้องกัน Error
    rect = np.zeros((4, 2), dtype="float32")
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]
    return rect

def four_point_transform(image, pts):
    """ฟังก์ชันสำหรับดัดภาพให้ตรงและตัดให้เหลือแค่เอกสาร"""
    rect = order_points(pts) # ลบคำสั่ง reshape ออกจากตรงนี้ เพราะเราย้ายไปทำใน order_points แล้ว

    # คำนวณความกว้างของรูปใหม่
    widthA = np.sqrt(((rect[2][0] - rect[0][0]) ** 2) + ((rect[2][1] - rect[0][1]) ** 2))
    widthB = np.sqrt(((rect[3][0] - rect[1][0]) ** 2) + ((rect[3][1] - rect[1][1]) ** 2))
    maxWidth = max(int(widthA), int(widthB))

    # คำนวณความสูงของรูปใหม่
    heightA = np.sqrt(((rect[0][0] - rect[2][0]) ** 2) + ((rect[0][1] - rect[2][1]) ** 2))
    heightB = np.sqrt(((rect[1][0] - rect[3][0]) ** 2) + ((rect[1][1] - rect[3][1]) ** 2))
    maxHeight = max(int(heightA), int(heightB))

    # กำหนดจุด 4 มุมของภาพปลายทาง (ให้เป็นสี่เหลี่ยมผืนผ้าตรงๆ)
    dst = np.array([
        [0, 0],
        [maxWidth - 1, 0],
        [maxWidth - 1, maxHeight - 1],
        [0, maxHeight - 1]
    ], dtype="float32")

    # คำนวณเมทริกซ์และทำการดัดภาพ
    M = cv2.getPerspectiveTransform(rect, dst)
    warped = cv2.warpPerspective(image, M, (maxWidth, maxHeight))
    return warped
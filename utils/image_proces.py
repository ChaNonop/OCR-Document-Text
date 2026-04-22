from cv2 import blur
import cv2
import os
import numpy as np
from numpy import load


def get_image(image_path):
    image = cv2.imread(image_path)
    if image is None:
        print("Error: unable to read the image.")
        return None
    else:
        return image
    height, width, channels = image.shape[:2]
    new_width = 800
    new_height = int(height * (new_width / width))
    resized_image = cv2.resize(image, (new_width, new_height))
    return resized_image
    cv2.imshow("Resized Image", get_image("new_image.jpg"))
    cv2.waitKey(0)
    cv2.destroyAllWindows()
    return resized_image

def brightness_contrast(gray_image, brightness=0, contrast=0):
    brighness = np.mean(gray_image)
    print(f"Brightness: {brighness}")

    # ปรับความสว่างและคอนทราสต์ตามค่าที่กำหนด
    if brightness < 90:
        print("Brightness is too low. Adjusting...")
        adjust =cv2.convertScaleAbs(gray_image, alpha = 1.2, beta = 30) # ปรับความสว่างโดยเพิ่มค่า beta
    elif brightness > 200:
        print("Brightness is too high. Adjusting...")
        adjust = cv2.convertScaleAbs(gray_image, alpha = 0.8, beta = -30) # ปรับความสว่างโดยลดค่า beta 
    else:
        print("Brightness is within the normal range.")
        adjust = gray_image
        
    # เพิ่ม CLAHE (เกลี่ยแสงให้ตัวหนังสือเด้งออกมา)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    return clahe.apply(adjust)

def detect_edges(image):
    # แปลงภาพเป็นสีเทา
    gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) # แปลงภาพเป็นสีเทา
    enhanced_image = brightness_contrast(gray_image) # ปรับความสว่างและคอนทราสต์
    
    # เบลอภาพเพื่อช่วยลด noise
    blurred_image = cv2.GaussianBlur(gray_image, (5, 5), 0) # (5, 5) คือขนาดของตัวเบลอ เลขมากภาพยิ่งเบลอ (ต้องเป็นเลขคี่เสมอ)
    
    # ตรวจจับขอบด้วย Canny edge detection
    edge = cv2.Canny(blurred_image, 75, 200) # gain treshold สูงต่ำ เส้นที่ความต่างแสงน้อยกว่า 75 ไม่นับเป็นขอบ และมากกว่า 200 คือขอบแน่นอน
    return enhanced_image , edge 

def find_document_corners(edge_image):
    contours, _ = cv2.findContours(edge_image, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    contours = sorted(contours, key=cv2.contourArea, reverse=True)[:5]
    for contour in contours:
        peri = cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, 0.02 * peri, True)
        if len(approx) == 4:
            return approx
    return None

if __name__ == "__main__":    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    test_image_path = os.path.join(script_dir, "../Data_test_eng/images/13.jpg")
    
    #โหลดภาพจากไฟล์
    original_image = get_image(test_image_path)
    
    if original_image is not None:
        print("Image loaded successfully.")
        
        #เรียกฟังก์ชั่นตรวจจับขอบ
        enhanced_image, edge_image = detect_edges(original_image)
        
        #แสดงผลลัพธ์
        # cv2.imwrite("/Load_image/new_image.jpg",orginal_image)
        
        # 3. แสดงผลลัพธ์ทีละขั้นตอนเพื่อเปรียบเทียบ
        # แสดงผลเปรียบเทียบ
        # cv2.imshow("1. Brightness Adjusted", clahe)
        cv2.imshow("2. Enhanced Grayscale (CLAHE)", enhanced_image)
        cv2.imshow("3. Edged", edge_image)
        
        cv2.waitKey(0)
        cv2.destroyAllWindows()
    else:
        print("Failed to load the image.")
        exit(1)
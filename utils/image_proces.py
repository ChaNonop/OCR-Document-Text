from cv2 import blur
import cv2
import os
import numpy as np
from numpy import load


def get_image(image_path):
    image = cv2.imread(image_path)
    return image
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

def detect_edges(image):
    gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) # แปลงภาพเป็นสีเทา
    
     # เบลอภาพเพื่อช่วยลด noise
    blurred_image = cv2.GaussianBlur(gray_image, (5, 5), 0) # (5, 5) คือขนาดของตัวเบลอ เลขมากภาพยิ่งเบลอ (ต้องเป็นเลขคี่เสมอ)
    # ตรวจจับขอบด้วย Canny edge detection
    edges = cv2.Canny(blurred_image, 100, 200) # gain treshold สูงต่ำ เส้นที่ความต่างแสงน้อยกว่า 75 ไม่นับเป็นขอบ และมากกว่า 200 คือขอบแน่นอน
    return edges , blurred_image ,gray_image

if __name__ == "__main__":
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    test_image_path = os.path.join(script_dir, "../Data_test/images/13.jpg")
    
    #โหลดภาพจากไฟล์
    orginal_image = get_image(test_image_path)
    
    if orginal_image is not None:
        print("Image loaded successfully.")
        
        #เรียกฟังก์ชั่นตรวจจับขอบ
        gray_image, blurred_image, edges = detect_edges(orginal_image)
        
        #แสดงผลลัพธ์
        # cv2.imwrite("/Load_image/new_image.jpg",orginal_image)
        
        # 3. แสดงผลลัพธ์ทีละขั้นตอนเพื่อเปรียบเทียบ
        cv2.imshow("1. Original", orginal_image)
        cv2.imshow("2. Grayscale", gray_image)
        cv2.imshow("3. Blurred", blurred_image)
        cv2.imshow("4. Edged (Canny)", edges)
        cv2.imshow("Loaded Image", orginal_image)
        cv2.waitKey(0)
        cv2.destroyAllWindows()
    else:
        print("Failed to load the image.")
        exit(1)
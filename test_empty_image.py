import requests
import numpy as np
import cv2

# Create a blank white image
img = np.ones((500, 500, 3), dtype=np.uint8) * 255
cv2.imwrite('blank.jpg', img)

url = 'http://127.0.0.1:8000/api/upload'
files = {'file': open('blank.jpg', 'rb')}
try:
    response = requests.post(url, files=files)
    print("Status Code:", response.status_code)
    print("Response:", response.json())
except Exception as e:
    print("Error:", e)

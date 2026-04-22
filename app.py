import cv2

def get_image(image_path):
    image = cv2.imread(image_path)
    return image
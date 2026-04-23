import cv2
from utils.image_proces import detect_edges, find_document_corners, four_point_transform
import easyocr
import glob

reader = easyocr.Reader(['th', 'en'])

for img_path in glob.glob('Data_test_eng/images/*.*'):
    img = cv2.imread(img_path)
    if img is None:
        continue
    _, edge = detect_edges(img)
    corners = find_document_corners(edge)
    
    if corners is not None:
        processed = four_point_transform(img, corners)
        texts = reader.readtext(processed, detail=0)
        print(f"{img_path}: Cropped, found {len(texts)} texts")
        if len(texts) == 0:
            print(">>> ERROR: NO TEXT EXTRACTED! <<<")
            cv2.imwrite("debug_cropped.jpg", processed)
    else:
        texts = reader.readtext(img, detail=0)
        print(f"{img_path}: Not cropped, found {len(texts)} texts")

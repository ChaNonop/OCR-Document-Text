import cv2
import numpy as np
import logging

logger = logging.getLogger("ocr-engine")


# ──────────────────────────────────────────────
# 1. Resize — จำกัดด้านยาวไม่เกิน max_size px
# ──────────────────────────────────────────────
def resize_image(image: np.ndarray, max_size: int = 1024) -> tuple[np.ndarray, float]:
    h, w = image.shape[:2]
    longest = max(h, w)

    if longest <= max_size:
        return image.copy(), 1.0

    ratio = max_size / longest
    new_w = int(w * ratio)
    new_h = int(h * ratio)
    resized = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)
    logger.info(f"Resized: {w}x{h} → {new_w}x{new_h} (ratio={ratio:.3f})")
    return resized, ratio


# ──────────────────────────────────────────────
# 2. Enhance — ปรับ Brightness/Contrast อัตโนมัติ
# ──────────────────────────────────────────────
def enhance_grayscale(gray: np.ndarray) -> np.ndarray:
    """
    ปรับความสว่างตามค่าเฉลี่ยของภาพ แล้วใช้ CLAHE เพิ่มความคมชัด.
    """
    mean_brightness = np.mean(gray)

    if mean_brightness < 90:
        adjusted = cv2.convertScaleAbs(gray, alpha=1.2, beta=30)
    elif mean_brightness > 200:
        adjusted = cv2.convertScaleAbs(gray, alpha=0.8, beta=-30)
    else:
        adjusted = gray

    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    return clahe.apply(adjusted)


# ──────────────────────────────────────────────
# 3. Edge Detection — Canny
# ──────────────────────────────────────────────
def detect_edges(image: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """
    แปลง BGR → Grayscale → Enhance → GaussianBlur → Canny.

    Returns:
        enhanced: ภาพ grayscale ที่ enhance แล้ว
        edges:    ภาพขอบจาก Canny
    """
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    enhanced = enhance_grayscale(gray)
    blurred = cv2.GaussianBlur(enhanced, (5, 5), 0)
    edges = cv2.Canny(blurred, 75, 200)
    return enhanced, edges


# ──────────────────────────────────────────────
# 4. Find Document Corners — หา 4 มุมของเอกสาร
# ──────────────────────────────────────────────
def find_document_corners(
    edge_image: np.ndarray,
    min_area_ratio: float = 0.05,
) -> np.ndarray | None:
    """
    ค้นหา contour 4 มุมที่ใหญ่ที่สุดจากภาพ edge.

    Args:
        edge_image:      ภาพ edge จาก Canny
        min_area_ratio:  สัดส่วนขั้นต่ำเมื่อเทียบกับพื้นที่ภาพทั้งหมด (default 5%)

    Returns:
        approx (4,1,2) ndarray หรือ None ถ้าหาไม่เจอ
    """
    contours, _ = cv2.findContours(
        edge_image.copy(), cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE
    )
    # เรียงจากพื้นที่มากสุด เอา 5 ตัวแรก
    contours = sorted(contours, key=cv2.contourArea, reverse=True)[:5]

    img_h, img_w = edge_image.shape[:2]
    total_area = img_h * img_w
    min_area = total_area * min_area_ratio

    for c in contours:
        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.02 * peri, True)

        if len(approx) == 4:
            contour_area = cv2.contourArea(approx)
            if contour_area >= min_area:
                logger.info(
                    f"Document corners found — "
                    f"contour area: {contour_area:.0f} px² "
                    f"({contour_area / total_area * 100:.1f}% of image)"
                )
                return approx

    logger.info("No valid 4-corner contour found (below area threshold or not 4 corners)")
    return None


# ──────────────────────────────────────────────
# 5. Order Points — เรียงจุด 4 มุมให้ถูกลำดับ
# ──────────────────────────────────────────────
def order_points(pts: np.ndarray) -> np.ndarray:
    """
    เรียงลำดับ 4 จุด: [บนซ้าย, บนขวา, ล่างขวา, ล่างซ้าย]
    """
    pts = pts.reshape(4, 2).astype("float32")
    rect = np.zeros((4, 2), dtype="float32")

    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]   # บนซ้าย  (x+y น้อยสุด)
    rect[2] = pts[np.argmax(s)]   # ล่างขวา (x+y มากสุด)

    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]  # บนขวา  (x-y น้อยสุด)
    rect[3] = pts[np.argmax(diff)]  # ล่างซ้าย (x-y มากสุด)

    return rect


# ──────────────────────────────────────────────
# 6. Perspective Transform — ดัดภาพให้ตรง
# ──────────────────────────────────────────────
def four_point_transform(image: np.ndarray, pts: np.ndarray) -> np.ndarray:
    """
    Perspective warp ให้เอกสารตรงเป็นสี่เหลี่ยมผืนผ้า.
    """
    rect = order_points(pts)
    (tl, tr, br, bl) = rect

    # คำนวณขนาดภาพปลายทาง
    width_top = np.linalg.norm(tr - tl)
    width_bot = np.linalg.norm(br - bl)
    max_width = max(int(width_top), int(width_bot))

    height_left = np.linalg.norm(tl - bl)
    height_right = np.linalg.norm(tr - br)
    max_height = max(int(height_left), int(height_right))

    # Safety: ป้องกันภาพขนาด 0
    max_width = max(max_width, 1)
    max_height = max(max_height, 1)

    dst = np.array([
        [0, 0],
        [max_width - 1, 0],
        [max_width - 1, max_height - 1],
        [0, max_height - 1],
    ], dtype="float32")

    M = cv2.getPerspectiveTransform(rect, dst)
    warped = cv2.warpPerspective(image, M, (max_width, max_height))

    logger.info(f"Perspective transform done — output: {max_width}x{max_height}")
    return warped


# ──────────────────────────────────────────────
# 7. Smart Crop — ฟังก์ชันหลักที่รวมทุกอย่าง
# ──────────────────────────────────────────────
def smart_crop(image: np.ndarray) -> tuple[np.ndarray, str]:
    """
    ฟังก์ชัน Orchestrator: Resize → Edge → Find Corners → Transform.

    ถ้าหา 4 มุมไม่เจอหรือ crop แล้วได้ภาพเล็กเกินไป จะ fallback
    ไปใช้ภาพ resized ต้นฉบับแทน (ไม่เกิด Error)

    Returns:
        processed: ภาพที่ผ่านการ process แล้ว
        status:    ข้อความสถานะบอกว่าเกิดอะไรขึ้น
    """
    # Step 1: Resize
    resized, ratio = resize_image(image, max_size=1024)
    logger.info(f"[SmartCrop] Input: {image.shape[1]}x{image.shape[0]} → Resized: {resized.shape[1]}x{resized.shape[0]}")

    # Step 2: Edge Detection
    _, edges = detect_edges(resized)
    logger.info("[SmartCrop] Edge detection completed")

    # Step 3: Find Document Corners
    corners = find_document_corners(edges)

    if corners is None:
        logger.info("[SmartCrop] Fallback → using resized original (no corners found)")
        return resized, "No document edges detected — returned resized original"

    # Step 4: Perspective Transform
    try:
        cropped = four_point_transform(resized, corners)

        # Safety check: ถ้าได้ภาพเล็กเกินไป (เล็กกว่า 50px) → fallback
        ch, cw = cropped.shape[:2]
        if cw < 50 or ch < 50:
            logger.warning(f"[SmartCrop] Cropped image too small ({cw}x{ch}px) — falling back")
            return resized, "Cropped result too small — returned resized original"

        logger.info(f"[SmartCrop] Success — cropped to {cw}x{ch}px")
        return cropped, "Document detected and cropped successfully"

    except Exception as e:
        logger.error(f"[SmartCrop] Transform failed: {e} — falling back")
        return resized, f"Transform error — returned resized original"
"""Test Step 2: ทดสอบ /api/scan ทั้ง Smart Crop + Gemini fallback"""
import urllib.request
import json
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

API_URL = "http://127.0.0.1:8000/api/scan"
IMAGE_PATH = "Data_test_eng/images/7.jpg"
BOUNDARY = "----TestBoundary12345"

with open(IMAGE_PATH, "rb") as f:
    file_data = f.read()

body = (
    f"--{BOUNDARY}\r\n"
    f'Content-Disposition: form-data; name="file"; filename="7.jpg"\r\n'
    f"Content-Type: image/jpeg\r\n\r\n"
).encode() + file_data + f"\r\n--{BOUNDARY}--\r\n".encode()

req = urllib.request.Request(
    API_URL,
    data=body,
    headers={"Content-Type": f"multipart/form-data; boundary={BOUNDARY}"},
    method="POST",
)

try:
    with urllib.request.urlopen(req, timeout=30) as resp:
        result = json.loads(resp.read().decode())
        print("=" * 50)
        print("API RESPONSE:")
        print("=" * 50)
        print(f"  Status:         {result['status']}")
        print(f"  Message:        {result['message']}")
        print(f"  Original:       {result['original_size']}")
        print(f"  Processed:      {result['processed_size']}")
        print(f"  Time:           {result['processing_time_ms']}ms")
        print(f"  Base64 length:  {len(result['processed_image_base64'])} chars")
        print()
        print("DOCUMENT DATA (from Gemini / fallback):")
        print("-" * 50)
        doc = result["document_data"]
        print(json.dumps(doc, indent=2, ensure_ascii=False))
        print()
        
        if doc.get("ai_error"):
            print(f"  ⚠ AI Error: {doc['ai_error']}")
            print("  → This is expected! Set GEMINI_API_KEY to enable AI analysis.")
        else:
            print("  ✅ Gemini AI analysis working!")

except Exception as e:
    print(f"❌ Error: {e}")

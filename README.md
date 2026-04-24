<div align="center">

# 🔍 DocScan OCR

### AI-Powered Document Scanner & Text Extractor

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![OpenCV](https://img.shields.io/badge/OpenCV-4.x-5C3EE8?style=for-the-badge&logo=opencv&logoColor=white)](https://opencv.org)
[![Gemini](https://img.shields.io/badge/Gemini_1.5_Flash-AI-4285F4?style=for-the-badge&logo=google&logoColor=white)](https://deepmind.google/technologies/gemini/)
[![Railway](https://img.shields.io/badge/Deployed_on-Railway-0B0D0E?style=for-the-badge&logo=railway&logoColor=white)](https://railway.app)
[![Live Demo](https://img.shields.io/badge/🚀_Live_Demo-Click_Here-FF6B6B?style=for-the-badge)](https://web-production-3e3e3d.up.railway.app/)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-38B2AC?style=for-the-badge&logo=tailwind-css&logoColor=white)](https://tailwindcss.com)

> ระบบสแกนและอ่านข้อความจากเอกสารด้วย AI แบบ Hybrid Architecture — เร็ว แม่นยำ และ Export เป็น PDF ได้ในคลิกเดียว

**🔗 Live Demo: [https://web-production-3e3e3d.up.railway.app/](https://web-production-3e3e3d.up.railway.app/)**

</div>

---

## 🗺️ ภาพรวมระบบ (System Overview)

**DocScan OCR** คือเว็บแอปพลิเคชันที่ผสานจุดเด่นของแต่ละเทคโนโลยีเข้าด้วยกัน ตั้งแต่การตรวจจับขอบกระดาษด้วย OpenCV, การอ่านและจัดหมวดหมู่ข้อความด้วย Google Gemini AI, ไปจนถึงการ Export เป็นไฟล์ PDF โดยไม่ต้องพึ่งพาเซิร์ฟเวอร์เพิ่มเติม

```
📸 อัปโหลดภาพ  →  ✂️ ตัดและปรับภาพ (OpenCV)  →  🤖 อ่านข้อความ (Gemini AI)  →  📄 Export PDF (jsPDF)
```

---

## ✨ Features

| Feature                    | รายละเอียด                                                    |
| -------------------------- | ------------------------------------------------------------- |
| 📤 **Drag & Drop Upload**  | ลากวางหรือคลิกเลือกภาพได้เลย รองรับไฟล์ขนาดสูงสุด 3 MB        |
| ✂️ **Smart Auto-Crop**     | ตรวจจับขอบกระดาษ 4 มุม และตัดพื้นหลังออกอัตโนมัติ             |
| 🤖 **AI OCR & Categorize** | อ่านข้อความและจัดหมวดหมู่ข้อมูลเป็นโครงสร้าง JSON ด้วย Gemini |
| 📄 **Export as PDF**       | สร้างและดาวน์โหลด PDF ขนาด A4 ได้ทันทีจากเบราว์เซอร์          |
| ⚡ **Fast Processing**     | ปรับขนาดภาพก่อนส่ง ลดการใช้เน็ตและเพิ่มความเร็ว               |
| 🎨 **Cyberpunk UI**        | ออกแบบในสไตล์ Modern Cyberpunk Dashboard                      |

---

## 🛠️ Tech Stack

### 🖥️ Frontend

- **HTML + Tailwind CSS** — UI สไตล์ Cyberpunk / Modern Dashboard
- **Vanilla JavaScript** — ควบคุมการทำงาน (ตรวจสอบไฟล์, อัปโหลด, แสดงผล)
- **jsPDF** — สร้างและส่งออก PDF จากฝั่ง Browser โดยตรง

### ⚙️ Backend

- **Python + FastAPI** — API Server ที่รวดเร็วและ lightweight
- **OpenCV** — Image Processing (Resize, หา 4 มุม, Perspective Transform)
- **Google Gemini API** `gemini-1.5-flash` — OCR + จัดหมวดหมู่เป็น JSON

### 🚀 Deployment

- **Railway** — Deploy Backend แบบ Cloud ไม่ต้องตั้ง Server เอง

---

## 🔄 Workflow

```
┌─────────────────────────────────────────────────────────────────┐
│                         FRONTEND (Browser)                      │
│                                                                 │
│  1️⃣  ผู้ใช้เลือกรูปภาพ (Drag & Drop / Click)                    │
│      └─ JS ตรวจขนาด: ถ้า > 3MB → แจ้ง Error                    │
│                        ถ้า <= 3MB → แสดง Preview + ส่ง API      │
└───────────────────────────┬─────────────────────────────────────┘
                            │ HTTP POST (multipart/form-data)
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                        BACKEND (FastAPI)                        │
│                                                                 │
│  2️⃣  OpenCV รับภาพ                                              │
│      ├─ Resize: ด้านยาวสุดไม่เกิน 1024px                        │
│      └─ Smart Crop: หา 4 มุม → Perspective Transform            │
│         (ถ้าหาขอบไม่เจอ → ใช้ภาพต้นฉบับแทน)                   │
│                                                                 │
│  3️⃣  Gemini API รับภาพที่ตัดแล้ว                                │
│      └─ วิเคราะห์ประเภทเอกสาร + สกัดข้อความ → JSON             │
└───────────────────────────┬─────────────────────────────────────┘
                            │ JSON Response (Base64 Image + Data)
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                         FRONTEND (Browser)                      │
│                                                                 │
│  4️⃣  แสดงผล Tags + ข้อมูลที่อ่านได้                             │
│      └─ กดปุ่ม "Export as PDF" → jsPDF สร้าง A4 → Download     │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📂 Project Structure

```
ocr_project/
│
├── .env                     # Gemini API Key (อย่า Commit ขึ้น GitHub!)
├── app.py                   # FastAPI หลังบ้าน (OpenCV + Gemini)
├── requirements.txt         # Python Dependencies
│
├── utils/
│   └── image_proces.py      # ฟังก์ชัน Resize + Smart Crop (OpenCV)
│
└── web/
    ├── index.html           # โครงสร้างหน้าเว็บหลัก
    ├── style.css            # UI Styling (Tailwind)
    └── scripts.js           # File Check + API Call + jsPDF Logic
```

---

## 🚀 Getting Started

### 1. Clone Repository

```bash
git clone https://github.com/ChaNonop/OCR-Document-Text.git
cd OCR-Document-Text
```

### 2. ติดตั้ง Dependencies

```bash
pip install -r requirements.txt
```

### 3. ตั้งค่า Environment Variables

สร้างไฟล์ `.env` ในโฟลเดอร์หลัก:

```env
GEMINI_API_KEY=your_gemini_api_key_here
```

> 💡 ขอ API Key ได้ที่ [Google AI Studio](https://aistudio.google.com/app/apikey) ฟรี!

### 4. รันเซิร์ฟเวอร์

```bash
uvicorn app:app --reload
```

เปิดเบราว์เซอร์ไปที่ `http://localhost:8000` ✅

---

## ☁️ Deploy บน Railway

โปรเจคนี้ deploy บน **Railway** ทำตามขั้นตอนนี้ได้เลย:

1. Push โค้ดขึ้น GitHub
2. ไปที่ [railway.app](https://railway.app) → New Project → Deploy from GitHub
3. เลือก Repository นี้
4. ตั้งค่า Environment Variable: `GEMINI_API_KEY`
5. Railway จะ Build และ Deploy ให้อัตโนมัติ 🎉

> ตรวจสอบให้แน่ใจว่ามีไฟล์ `requirements.txt` และ `Procfile` (ถ้าจำเป็น) ก่อน Deploy

---

## ⚠️ ข้อจำกัด

- รองรับไฟล์รูปภาพขนาดสูงสุด **3 MB** ต่อครั้ง
- ความแม่นยำของ OCR ขึ้นอยู่กับความชัดของภาพต้นฉบับ
- ต้องการ Internet Connection สำหรับติดต่อ Gemini API

---

## 🤝 Contributing

Pull Request ยินดีต้อนรับเสมอ! กรุณา Fork repo และสร้าง branch ใหม่ก่อน PR นะครับ 😊

---

<div align="center">

Made with ❤️ by [ChaNonop](https://github.com/ChaNonop)

⭐ ถ้าชอบโปรเจคนี้ อย่าลืมกด Star ด้วยนะ!

</div>

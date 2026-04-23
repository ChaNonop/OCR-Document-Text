document.addEventListener("DOMContentLoaded", () => {
  // Elements
  const dropZone = document.getElementById("dropZone");
  const fileInput = document.getElementById("fileInput");
  const submitBtn = document.getElementById("submitBtn");
  const uploadForm = document.getElementById("uploadForm");

  const originalPreviewCard = document.getElementById("originalPreviewCard");
  const originalImg = document.getElementById("originalImg");
  const imageContainer = document.getElementById("imageContainer");
  const scanOverlay = document.getElementById("scanOverlay");

  const emptyState = document.getElementById("emptyState");
  const resultContainer = document.getElementById("resultContainer");

  const processedImg = document.getElementById("processedImg");
  const tagsArea = document.getElementById("tagsArea");
  const ocrTextarea = document.getElementById("ocrTextarea");
  const copyBtn = document.getElementById("copyBtn");

  // 1. จัดการ Drag & Drop ลูกเล่นอัปโหลด
  ["dragenter", "dragover", "dragleave", "drop"].forEach((eventName) => {
    dropZone.addEventListener(eventName, preventDefaults, false);
  });
  function preventDefaults(e) {
    e.preventDefault();
    e.stopPropagation();
  }

  ["dragenter", "dragover"].forEach((eventName) => {
    dropZone.addEventListener(
      eventName,
      () => dropZone.classList.add("dragover"),
      false,
    );
  });
  ["dragleave", "drop"].forEach((eventName) => {
    dropZone.addEventListener(
      eventName,
      () => dropZone.classList.remove("dragover"),
      false,
    );
  });

  dropZone.addEventListener("drop", (e) => {
    let dt = e.dataTransfer;
    let files = dt.files;
    fileInput.files = files;
    handleFileSelect(files[0]);
  });

  fileInput.addEventListener("change", function () {
    handleFileSelect(this.files[0]);
  });

  // 2. แสดงรูปตัวอย่าง
  function handleFileSelect(file) {
    if (file && file.type.startsWith("image/")) {
      const reader = new FileReader();
      reader.onload = (e) => {
        originalImg.src = e.target.result;
        originalPreviewCard.classList.remove("hidden");
        submitBtn.disabled = false;

        // เคลียร์ผลลัพธ์เก่าเวลาเลือกรูปใหม่
        emptyState.classList.remove("hidden");
        resultContainer.classList.add("hidden");
      };
      reader.readAsDataURL(file);

      // เปลี่ยนข้อความใน Dropzone
      dropZone.querySelector("p.font-medium").textContent = file.name;
      dropZone.querySelector("p.font-mono").textContent = `READY TO SCAN`;
    }
  }

  // 3. จัดการตอนกดปุ่ม Upload (ส่งไปหลังบ้าน)
  uploadForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const file = fileInput.files[0];
    if (!file) return;

    // เปิด Animation Loading และ Scanner
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<div class="loader mr-2"></div> SCANNING...';
    imageContainer.classList.add("is-scanning");
    scanOverlay.classList.remove("hidden");
    scanOverlay.classList.add("flex");

    const formData = new FormData();
    formData.append("file", file);

    try {
      // เรียก API Python FastAPI (อย่าลืมรัน uvicorn)
      const response = await fetch("http://127.0.0.1:8000/api/upload", {
        method: "POST",
        body: formData,
      });

      const data = await response.json();

      if (!response.ok) throw new Error(data.error || "Server Error");

      // ปิด Loading
      stopLoadingState();

      // ซ่อนหน้าว่าง แสดงหน้าผลลัพธ์
      emptyState.classList.add("hidden");
      resultContainer.classList.remove("hidden");

      // 4. แสดงรูปที่ตัดขอบแล้ว
      processedImg.src = data.processed_image_base64;

      // 5. แสดง Tags / Categories แบบ Badge ล้ำๆ
      tagsArea.innerHTML = "";
      if (data.tags && data.tags.length > 0) {
        data.tags.forEach((tag) => {
          const badge = document.createElement("div");
          badge.className =
            "tag-badge px-3 py-2 rounded flex items-center font-mono text-sm tracking-wide";
          badge.innerHTML = `<span class="mr-2">◈</span> ${tag.replace("#", "")}`;
          tagsArea.appendChild(badge);
        });
      } else {
        tagsArea.innerHTML =
          '<span class="text-[var(--muted)] font-mono text-sm">NO CATEGORY MATCHED</span>';
      }

      // 6. แสดงข้อความใน Textarea
      if (data.texts && data.texts.length > 0) {
        ocrTextarea.value = data.texts.join("\n");
      } else {
        ocrTextarea.value = "// NO TEXT DETECTED IN THIS DOCUMENT";
      }
    } catch (error) {
      console.error(error);
      stopLoadingState();
      alert(`Error: ${error.message}`);
    }
  });

  function stopLoadingState() {
    submitBtn.disabled = false;
    submitBtn.innerHTML = "<span>Upload Document</span>";
    imageContainer.classList.remove("is-scanning");
    scanOverlay.classList.add("hidden");
    scanOverlay.classList.remove("flex");
  }

  // 7. ฟังก์ชัน Copy
  copyBtn.addEventListener("click", () => {
    if (ocrTextarea.value) {
      ocrTextarea.select();
      document.execCommand("copy");

      const originalText = copyBtn.innerHTML;
      copyBtn.innerHTML =
        '<span class="text-[var(--green)]">[ COPIED! ]</span>';
      setTimeout(() => (copyBtn.innerHTML = originalText), 2000);
    }
  });
});

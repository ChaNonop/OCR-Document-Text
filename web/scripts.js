/**
 * DocScan OCR — Cyberpunk Frontend Logic (Step 4: Final Assembly + PDF Export)
 */
document.addEventListener("DOMContentLoaded", () => {
  const MAX_FILE_SIZE = 4 * 1024 * 1024;
  const API_ENDPOINT = "/api/scan";

  // DOM refs
  const dropZone = document.getElementById("dropZone");
  const fileInput = document.getElementById("fileInput");
  const submitBtn = document.getElementById("submitBtn");
  const uploadForm = document.getElementById("uploadForm");
  const statusBadge = document.getElementById("statusBadge");
  const originalPreviewCard = document.getElementById("originalPreviewCard");
  const originalImg = document.getElementById("originalImg");
  const imageContainer = document.getElementById("imageContainer");
  const scanOverlay = document.getElementById("scanOverlay");
  const fileSizeBadge = document.getElementById("fileSizeBadge");
  const emptyState = document.getElementById("emptyState");
  const resultContainer = document.getElementById("resultContainer");
  const processedImg = document.getElementById("processedImg");
  const tagsArea = document.getElementById("tagsArea");
  const ocrTextContainer = document.getElementById("ocrTextContainer");
  const copyBtn = document.getElementById("copyBtn");
  const statDocType = document.getElementById("statDocType");
  const statConfidence = document.getElementById("statConfidence");
  const statTime = document.getElementById("statTime");
  const docTypeFull = document.getElementById("docTypeFull");
  const summaryText = document.getElementById("summaryText");
  const structuredDataCard = document.getElementById("structuredDataCard");
  const structuredDataContent = document.getElementById("structuredDataContent");
  const cyberAlert = document.getElementById("cyberAlert");
  const alertMessage = document.getElementById("alertMessage");
  const alertCloseBtn = document.getElementById("alertCloseBtn");
  const clockDisplay = document.getElementById("clockDisplay");
  const exportPdfBtn = document.getElementById("exportPdfBtn");

  // State — เก็บผลลัพธ์ล่าสุดสำหรับ PDF Export
  let lastResultData = null;

  // ── Particles ──
  const particleCanvas = document.getElementById("particleCanvas");
  if (particleCanvas) {
    const ctx = particleCanvas.getContext("2d");
    let particles = [];
    function resizeCanvas() { particleCanvas.width = window.innerWidth; particleCanvas.height = window.innerHeight; }
    resizeCanvas(); window.addEventListener("resize", resizeCanvas);
    class Particle {
      constructor() { this.reset(); }
      reset() {
        this.x = Math.random() * particleCanvas.width; this.y = Math.random() * particleCanvas.height;
        this.size = Math.random() * 1.5 + 0.5; this.speedX = (Math.random() - 0.5) * 0.3; this.speedY = (Math.random() - 0.5) * 0.3;
        this.opacity = Math.random() * 0.4 + 0.1; this.color = Math.random() > 0.7 ? "#ff00e5" : "#00f0ff";
      }
      update() { this.x += this.speedX; this.y += this.speedY; if (this.x < 0 || this.x > particleCanvas.width || this.y < 0 || this.y > particleCanvas.height) this.reset(); }
      draw() { ctx.beginPath(); ctx.arc(this.x, this.y, this.size, 0, Math.PI * 2); ctx.fillStyle = this.color; ctx.globalAlpha = this.opacity; ctx.fill(); ctx.globalAlpha = 1; }
    }
    for (let i = 0; i < 50; i++) particles.push(new Particle());
    (function animate() { ctx.clearRect(0, 0, particleCanvas.width, particleCanvas.height); particles.forEach(p => { p.update(); p.draw(); }); requestAnimationFrame(animate); })();
  }

  // ── Clock ──
  function updateClock() { const n = new Date(); if (clockDisplay) clockDisplay.textContent = [n.getHours(), n.getMinutes(), n.getSeconds()].map(v => String(v).padStart(2, "0")).join(":"); }
  updateClock(); setInterval(updateClock, 1000);

  // ── Alert ──
  let alertTimer = null;
  function showCyberAlert(msg, dur = 5000) { if (alertTimer) clearTimeout(alertTimer); alertMessage.textContent = msg; cyberAlert.classList.add("show"); alertTimer = setTimeout(() => cyberAlert.classList.remove("show"), dur); }
  alertCloseBtn.addEventListener("click", () => { cyberAlert.classList.remove("show"); if (alertTimer) clearTimeout(alertTimer); });

  // ── Drag & Drop ──
  ["dragenter","dragover","dragleave","drop"].forEach(e => dropZone.addEventListener(e, ev => { ev.preventDefault(); ev.stopPropagation(); }));
  ["dragenter","dragover"].forEach(e => dropZone.addEventListener(e, () => dropZone.classList.add("dragover")));
  ["dragleave","drop"].forEach(e => dropZone.addEventListener(e, () => dropZone.classList.remove("dragover")));
  dropZone.addEventListener("drop", e => { const f = e.dataTransfer.files; if (f.length) { fileInput.files = f; handleFileSelect(f[0]); } });
  fileInput.addEventListener("change", function () { if (this.files[0]) handleFileSelect(this.files[0]); });

  // ── File Select ──
  function handleFileSelect(file) {
    if (!file || !file.type.startsWith("image/")) { showCyberAlert("Error: กรุณาเลือกไฟล์รูปภาพเท่านั้น"); resetUpload(); return; }
    if (file.size > MAX_FILE_SIZE) { showCyberAlert(`Error: ไฟล์ใหญ่เกินไป (${(file.size/1024/1024).toFixed(1)} MB) — Max 4MB`, 6000); setBadge("error","OVERSIZE"); resetUpload(); return; }
    const reader = new FileReader();
    reader.onload = e => { originalImg.src = e.target.result; originalPreviewCard.classList.remove("hidden"); submitBtn.disabled = false; emptyState.classList.remove("hidden"); resultContainer.classList.add("hidden"); exportPdfBtn.style.display = "none"; };
    reader.readAsDataURL(file);
    const dc = document.getElementById("dropZoneContent");
    if (dc) { const p1 = dc.querySelector("p.text-sm"); const p2 = dc.querySelector("p.text-xs"); if (p1) p1.textContent = file.name.length > 30 ? file.name.slice(0,27)+"..." : file.name; if (p2) p2.innerHTML = `${(file.size/1024/1024).toFixed(2)} MB — <span class="text-cyber-green">READY</span>`; }
    if (fileSizeBadge) fileSizeBadge.textContent = `${(file.size/1024/1024).toFixed(2)} MB`;
    setBadge("ready","READY");
  }
  function resetUpload() { fileInput.value = ""; submitBtn.disabled = true; }

  // ── Upload ──
  uploadForm.addEventListener("submit", async e => {
    e.preventDefault();
    const file = fileInput.files[0];
    if (!file) return;
    if (file.size > MAX_FILE_SIZE) { showCyberAlert("Error: ไฟล์ใหญ่เกินไป (Max 4MB)"); return; }
    startLoading();
    const fd = new FormData(); fd.append("file", file);
    try {
      const res = await fetch(API_ENDPOINT, { method: "POST", body: fd });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || data.error || `Server Error (${res.status})`);
      stopLoading();
      lastResultData = data;
      displayResults(data);
      setBadge("done","COMPLETE");
    } catch (err) { console.error(err); stopLoading(); showCyberAlert(`Error: ${err.message}`, 8000); setBadge("error","ERROR"); }
  });

  // ── Display Results ──
  function displayResults(data) {
    emptyState.classList.add("hidden");
    resultContainer.classList.remove("hidden");
    const dd = data.document_data || {};

    if (data.processed_image_base64) processedImg.src = data.processed_image_base64;
    statDocType.textContent = (dd.document_type || "unknown").toUpperCase();
    statConfidence.textContent = dd.confidence ? `${(dd.confidence * 100).toFixed(0)}%` : "—";
    statTime.textContent = data.processing_time_ms ? `${data.processing_time_ms}ms` : "—";
    docTypeFull.textContent = dd.document_type_th ? `${dd.document_type_th} (${dd.document_type})` : (dd.document_type || "—");
    summaryText.textContent = dd.summary || "ไม่มีสรุป";

    // Tags
    tagsArea.innerHTML = "";
    const tc = ["green","cyan","magenta","yellow"];
    if (dd.tags && dd.tags.length) {
      dd.tags.forEach((t, i) => { 
        const b = document.createElement("span"); 
        b.className = `tag-badge tag-badge--clickable tag-badge--${tc[i%tc.length]}`; 
        b.innerHTML = `<span>◈</span> ${esc(t.replace("#",""))}`; 
        b.dataset.tag = t;
        b.addEventListener("click", () => handleTagClick(t, dd));
        tagsArea.appendChild(b); 
      });
    } else { tagsArea.innerHTML = '<span class="font-mono text-xs text-cyber-muted">NO TAGS</span>'; }

    // Structured Data
    const sd = dd.structured_data;
    if (sd) {
      const fields = [{l:"Title",v:sd.title},{l:"Date",v:sd.date},{l:"Total Amount",v:sd.total_amount},{l:"Company",v:sd.company_name}];
      const hasData = fields.some(f => f.v);
      if (hasData) {
        structuredDataCard.classList.remove("hidden");
        structuredDataContent.innerHTML = "";
        fields.forEach(f => { if (f.v) { const d = document.createElement("div"); d.className = "data-field"; d.innerHTML = `<div class="data-field__label">${f.l}</div><div class="data-field__value">${esc(f.v)}</div>`; structuredDataContent.appendChild(d); } });
        if (sd.items && sd.items.length) { const d = document.createElement("div"); d.className = "data-field sm:col-span-2"; d.innerHTML = `<div class="data-field__label">Items (${sd.items.length})</div><div class="data-field__value">${sd.items.map(esc).join(", ")}</div>`; structuredDataContent.appendChild(d); }
      } else { structuredDataCard.classList.add("hidden"); }
    }

    // OCR Text
    ocrTextContainer.textContent = dd.extracted_text || "// NO TEXT EXTRACTED";

    // Show PDF Export button
    exportPdfBtn.style.display = "flex";
    // Animate
    Array.from(resultContainer.children).forEach((c, i) => { c.classList.add("animate-in", `animate-in-delay-${i+1}`); });
  }

  // ── Loading States ──
  function startLoading() {
    submitBtn.disabled = true;
    submitBtn.querySelector(".cyber-btn__text").innerHTML = '<div class="scan-overlay__ring" style="width:20px;height:20px;border-width:2px;margin:0"></div> SCANNING...';
    imageContainer.classList.add("is-scanning"); scanOverlay.classList.remove("hidden"); setBadge("scanning","SCANNING");
  }
  function stopLoading() {
    submitBtn.disabled = false;
    submitBtn.querySelector(".cyber-btn__text").innerHTML = '<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/></svg> INITIALIZE SCAN';
    imageContainer.classList.remove("is-scanning"); scanOverlay.classList.add("hidden");
  }

  // ── Copy ──
  copyBtn.addEventListener("click", () => {
    const textToCopy = lastResultData?.document_data?.extracted_text || "";
    if (!textToCopy) return;
    navigator.clipboard.writeText(textToCopy).catch(() => { 
        const textArea = document.createElement("textarea");
        textArea.value = textToCopy;
        document.body.appendChild(textArea);
        textArea.select();
        document.execCommand("copy");
        document.body.removeChild(textArea);
    });
    const o = copyBtn.innerHTML; copyBtn.innerHTML = '<span class="text-cyber-green">[ COPIED ✓ ]</span>'; setTimeout(() => copyBtn.innerHTML = o, 2000);
  });

  // ── Interactive Highlight ──
  function handleTagClick(tag, dd) {
    if (!dd.tag_mapping || !dd.extracted_text) return;
    const mapping = dd.tag_mapping.find(m => m.tag === tag);
    if (!mapping || !mapping.exact_text) return;

    const exactText = mapping.exact_text;
    const fullText = dd.extracted_text;
    const idx = fullText.indexOf(exactText);

    if (idx === -1) {
      showCyberAlert(`ไม่พบข้อความหัวข้อสำหรับ ${tag} ในเอกสาร`, 3000);
      return;
    }

    // Reset container text
    ocrTextContainer.textContent = fullText;
    
    // Inject highlight HTML
    const before = esc(fullText.substring(0, idx));
    const highlighted = `<span class="highlight-flash" id="active-highlight">${esc(exactText)}</span>`;
    const after = esc(fullText.substring(idx + exactText.length));

    ocrTextContainer.innerHTML = before + highlighted + after;

    // Scroll into view inside the container
    const highlightEl = document.getElementById('active-highlight');
    if (highlightEl) {
      highlightEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
      setTimeout(() => {
        const el = document.getElementById('active-highlight');
        if (el) {
          const textNode = document.createTextNode(el.textContent);
          el.parentNode.replaceChild(textNode, el);
        }
      }, 2000);
    }
  }

  // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  // 📄 PDF EXPORT — jsPDF + html2canvas
  // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  exportPdfBtn.addEventListener("click", () => exportToPDF());

  async function exportToPDF() {
    if (!lastResultData) { showCyberAlert("ไม่มีข้อมูลสำหรับ Export"); return; }

    // UI feedback
    const origText = exportPdfBtn.querySelector(".cyber-btn__text").innerHTML;
    exportPdfBtn.disabled = true;
    exportPdfBtn.querySelector(".cyber-btn__text").innerHTML = '<div class="scan-overlay__ring" style="width:20px;height:20px;border-width:2px;margin:0"></div> GENERATING PDF...';

    try {
      const dd = lastResultData.document_data || {};
      const sd = dd.structured_data || {};

      // ── Populate the hidden PDF template ──
      const tpl = document.getElementById("pdfTemplate");
      document.getElementById("pdfTimestamp").textContent = `Generated: ${new Date().toLocaleString("th-TH")}  |  Processing: ${lastResultData.processing_time_ms || 0}ms`;

      // Image section
      const imgSection = document.getElementById("pdfImageSection");
      imgSection.innerHTML = "";
      if (lastResultData.processed_image_base64) {
        const img = document.createElement("img");
        img.src = lastResultData.processed_image_base64;
        img.style.cssText = "max-width:100%;max-height:400px;object-fit:contain;border:1px solid #ddd;border-radius:6px;";
        imgSection.appendChild(img);
      }

      // Info section
      const infoSection = document.getElementById("pdfInfoSection");
      infoSection.innerHTML = buildInfoHTML(dd, sd);

      // Text section
      const textSection = document.getElementById("pdfTextSection");
      const rawText = dd.extracted_text || "";
      textSection.innerHTML = `
        <div style="border:1px solid #ddd;border-radius:6px;padding:14px;background:#f8f9fa;">
          <div style="font-weight:700;font-size:13px;color:#333;margin-bottom:8px;border-bottom:1px solid #eee;padding-bottom:6px;">📝 EXTRACTED TEXT</div>
          <div style="font-size:13px;line-height:1.7;color:#222;white-space:pre-wrap;word-break:break-word;">${esc(rawText) || "No text extracted"}</div>
        </div>`;

      // Wait for image to load in template
      const tplImg = imgSection.querySelector("img");
      if (tplImg && !tplImg.complete) {
        await new Promise(r => { tplImg.onload = r; tplImg.onerror = r; setTimeout(r, 3000); });
      }

      // Move template on-screen temporarily (needed by html2canvas)
      tpl.style.left = "0px";
      tpl.style.zIndex = "-1";
      tpl.style.opacity = "0.01";

      // Capture with html2canvas at 2x resolution
      const canvas = await html2canvas(tpl, { scale: 2, backgroundColor: "#ffffff", useCORS: true, logging: false });

      // Hide template again
      tpl.style.left = "-9999px";
      tpl.style.opacity = "1";

      // ── Build PDF ──
      const { jsPDF } = window.jspdf;
      const pdf = new jsPDF("p", "mm", "a4");
      const pageW = 210, pageH = 297, margin = 10;
      const contentW = pageW - margin * 2;

      const canvasDataUrl = canvas.toDataURL("image/png");
      const imgW = contentW;
      const imgH = (canvas.height / canvas.width) * imgW;

      // If the captured content is taller than one page, split across pages
      let remainH = imgH;
      let srcY = 0;
      const srcPixelW = canvas.width;
      const srcPixelH = canvas.height;
      let pageNum = 0;

      while (remainH > 0) {
        if (pageNum > 0) pdf.addPage();
        const sliceH = Math.min(remainH, pageH - margin * 2);
        const slicePixelH = (sliceH / imgH) * srcPixelH;

        // Create a slice canvas
        const sliceCanvas = document.createElement("canvas");
        sliceCanvas.width = srcPixelW;
        sliceCanvas.height = Math.round(slicePixelH);
        const sCtx = sliceCanvas.getContext("2d");
        sCtx.drawImage(canvas, 0, Math.round(srcY), srcPixelW, Math.round(slicePixelH), 0, 0, srcPixelW, Math.round(slicePixelH));

        pdf.addImage(sliceCanvas.toDataURL("image/png"), "PNG", margin, margin, contentW, sliceH);
        srcY += slicePixelH;
        remainH -= sliceH;
        pageNum++;
      }

      // Save
      const ts = new Date().toISOString().replace(/[:.]/g, "-").slice(0, 19);
      pdf.save(`DocScan_${ts}.pdf`);

    } catch (err) {
      console.error("PDF Export error:", err);
      showCyberAlert(`PDF Export Error: ${err.message}`, 6000);
    } finally {
      exportPdfBtn.disabled = false;
      exportPdfBtn.querySelector(".cyber-btn__text").innerHTML = origText;
    }
  }

  // ── Build info HTML for the PDF template ──
  function buildInfoHTML(dd, sd) {
    let html = '<div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:16px;">';
    const infoFields = [
      { label: "Document Type", value: dd.document_type_th ? `${dd.document_type_th} (${dd.document_type})` : dd.document_type },
      { label: "Confidence", value: dd.confidence ? `${(dd.confidence * 100).toFixed(0)}%` : "—" },
      { label: "Language", value: dd.language || "—" },
      { label: "Processing Time", value: lastResultData.processing_time_ms ? `${lastResultData.processing_time_ms}ms` : "—" },
    ];
    infoFields.forEach(f => {
      html += `<div style="background:#f0f4ff;border-radius:6px;padding:10px;border:1px solid #e0e7f1;">
        <div style="font-size:10px;font-weight:700;color:#888;text-transform:uppercase;letter-spacing:0.05em;">${f.label}</div>
        <div style="font-size:14px;color:#111;margin-top:2px;">${esc(f.value || "—")}</div>
      </div>`;
    });
    html += "</div>";

    // Tags
    if (dd.tags && dd.tags.length) {
      html += '<div style="margin-bottom:12px;"><span style="font-size:10px;font-weight:700;color:#888;">TAGS: </span>';
      dd.tags.forEach(t => { html += `<span style="display:inline-block;background:#e0fff0;color:#059669;border:1px solid #a7f3d0;border-radius:4px;padding:2px 8px;font-size:11px;margin:2px;">${esc(t)}</span>`; });
      html += "</div>";
    }

    // Structured data
    const sdFields = [{l:"Title",v:sd.title},{l:"Date",v:sd.date},{l:"Total Amount",v:sd.total_amount},{l:"Company",v:sd.company_name}];
    if (sdFields.some(f => f.v)) {
      html += '<div style="border:1px solid #ddd;border-radius:6px;padding:14px;background:#f8f9fa;margin-bottom:12px;">';
      html += '<div style="font-weight:700;font-size:13px;color:#333;margin-bottom:8px;border-bottom:1px solid #eee;padding-bottom:6px;">📋 STRUCTURED DATA</div>';
      html += '<div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;">';
      sdFields.forEach(f => { if (f.v) html += `<div><span style="font-size:10px;color:#888;font-weight:700;">${f.l}:</span><div style="font-size:13px;color:#111;">${esc(f.v)}</div></div>`; });
      html += "</div>";
      if (sd.items && sd.items.length) { html += `<div style="margin-top:8px;"><span style="font-size:10px;color:#888;font-weight:700;">Items:</span><div style="font-size:12px;color:#333;">${sd.items.map(esc).join(" / ")}</div></div>`; }
      html += "</div>";
    }

    // Summary
    if (dd.summary) {
      html += `<div style="background:#fffbeb;border:1px solid #fde68a;border-radius:6px;padding:10px;margin-bottom:12px;">
        <span style="font-size:10px;font-weight:700;color:#92400e;">SUMMARY:</span>
        <div style="font-size:13px;color:#78350f;margin-top:2px;">${esc(dd.summary)}</div>
      </div>`;
    }
    return html;
  }

  // ── Helpers ──
  function setBadge(type, text) { statusBadge.className = `cyber-badge cyber-badge--${type}`; statusBadge.textContent = text; }
  function esc(s) { if (!s) return ""; const d = document.createElement("div"); d.textContent = s; return d.innerHTML; }
});

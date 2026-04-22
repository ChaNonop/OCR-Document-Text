const dropArea = document.getElementById("dropArea");
const fileInput = document.getElementById("fileInput");
const uploadBtn = document.getElementById("uploadBtn");
const loading = document.getElementById("loading");

const modal = document.getElementById("modal");
const modalText = document.getElementById("modalText");
const closeModal = document.getElementById("closeModal");
const copyBtn = document.getElementById("copyBtn");

const resultSection = document.getElementById("resultSection");
const textContent = document.getElementById("textContent");
const tagsContainer = document.getElementById("tags");

/* Click upload */
dropArea.addEventListener("click", () => fileInput.click());

/* Drag & Drop */
dropArea.addEventListener("dragover", (e) => {
  e.preventDefault();
  dropArea.classList.add("border-indigo-500");
});

dropArea.addEventListener("dragleave", () => {
  dropArea.classList.remove("border-indigo-500");
});

dropArea.addEventListener("drop", (e) => {
  e.preventDefault();
  fileInput.files = e.dataTransfer.files;
});

/* Upload button */
uploadBtn.addEventListener("click", () => {
  if (!fileInput.files.length) {
    alert("Please upload a file first");
    return;
  }

  loading.classList.remove("hidden");

  setTimeout(() => {
    loading.classList.add("hidden");

    const fakeText = `
# Invoice

Date: 2026-04-22
Customer: John Doe

## Items
- Product A - $100
- Product B - $50

## Total
$150
    `;

    // Show modal
    modal.classList.remove("hidden");
    modal.classList.add("flex");
    modalText.value = fakeText;

    // Show result section
    renderResult(fakeText);

  }, 2000);
});

/* Render result with tags */
function renderResult(text) {
  resultSection.classList.remove("hidden");

  textContent.innerHTML = "";
  tagsContainer.innerHTML = "";

  const lines = text.split("\n");

  lines.forEach((line, index) => {
    if (line.startsWith("#")) {
      const id = "section-" + index;

      // Create tag
      const tag = document.createElement("button");
      tag.textContent = line.replace(/#/g, "").trim();
      tag.className = "bg-indigo-100 text-indigo-700 px-3 py-1 rounded-full text-xs";

      tag.onclick = () => {
        document.getElementById(id).scrollIntoView({ behavior: "smooth" });
      };

      tagsContainer.appendChild(tag);

      // Create heading
      const h = document.createElement("div");
      h.id = id;
      h.className = "font-semibold mt-3";
      h.textContent = line.replace(/#/g, "").trim();

      textContent.appendChild(h);
    } else {
      const p = document.createElement("div");
      p.className = "text-sm";
      p.textContent = line;
      textContent.appendChild(p);
    }
  });
}

/* Close modal */
closeModal.addEventListener("click", () => {
  modal.classList.add("hidden");
});

/* Copy text */
copyBtn.addEventListener("click", () => {
  navigator.clipboard.writeText(modalText.value);
  copyBtn.textContent = "Copied!";
  setTimeout(() => (copyBtn.textContent = "Copy Text"), 1500);
});
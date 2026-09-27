const inputEl = document.getElementById("input");
const outputEl = document.getElementById("output");
const inputTag = document.getElementById("inputTag");
const outputTag = document.getElementById("outputTag");
const statusEl = document.getElementById("status");
const statsEl = document.getElementById("stats");
const jsonTokensEl = document.getElementById("jsonTokens");
const jsonCharsEl = document.getElementById("jsonChars");
const toonTokensEl = document.getElementById("toonTokens");
const toonCharsEl = document.getElementById("toonChars");
const savingsEl = document.getElementById("savings");
const savingsText = document.getElementById("savingsText");
const savingsBar = document.getElementById("savingsBar");

function setTag(el, format) {
  el.textContent = format;
  el.classList.toggle("toon", format === "toon");
}

function setDirectionTags(endpoint) {
  if (endpoint === "/api/to-toon") {
    setTag(inputTag, "json");
    setTag(outputTag, "toon");
  } else {
    setTag(inputTag, "toon");
    setTag(outputTag, "json");
  }
}

function renderStats(stats) {
  if (!stats) {
    statsEl.classList.add("hidden");
    return;
  }
  jsonTokensEl.textContent = stats.json_tokens;
  jsonCharsEl.textContent = stats.json_chars;
  toonTokensEl.textContent = stats.toon_tokens;
  toonCharsEl.textContent = stats.toon_chars;

  const pct = stats.savings_pct;
  savingsEl.classList.toggle("negative", pct < 0);
  savingsText.textContent = pct >= 0 ? `-${pct}% tokens` : `+${Math.abs(pct)}% tokens`;
  savingsBar.style.width = `${Math.min(100, Math.max(0, Math.abs(pct)))}%`;

  statsEl.classList.remove("hidden");
}

async function convert(endpoint) {
  statusEl.textContent = "";
  setDirectionTags(endpoint);
  const input = inputEl.value;
  if (!input.trim()) {
    outputEl.value = "";
    renderStats(null);
    return;
  }
  try {
    const res = await fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ input }),
    });
    const data = await res.json();
    if (!res.ok) {
      statusEl.textContent = data.error || "Conversion failed";
      renderStats(null);
      return;
    }
    outputEl.value = data.output;
    renderStats(data.stats);
  } catch (err) {
    statusEl.textContent = "Network error: " + err.message;
    renderStats(null);
  }
}

document.getElementById("toToon").addEventListener("click", () => convert("/api/to-toon"));
document.getElementById("toJson").addEventListener("click", () => convert("/api/to-json"));
document.getElementById("swap").addEventListener("click", () => {
  const tmpValue = inputEl.value;
  inputEl.value = outputEl.value;
  outputEl.value = tmpValue;

  const tmpFormat = inputTag.textContent;
  setTag(inputTag, outputTag.textContent);
  setTag(outputTag, tmpFormat);

  renderStats(null);
  statusEl.textContent = "";
});
document.getElementById("copy").addEventListener("click", async (e) => {
  const btn = e.currentTarget;
  const original = btn.textContent;
  try {
    await navigator.clipboard.writeText(outputEl.value);
    btn.textContent = "Copied";
  } catch {
    outputEl.select();
    btn.textContent = "Select output";
  }
  setTimeout(() => { btn.textContent = original; }, 1200);
});

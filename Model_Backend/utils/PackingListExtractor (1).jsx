import { useState, useRef } from "react";

const STATUS = { IDLE: "idle", LOADING: "loading", DONE: "done", ERROR: "error" };

export default function PackingListExtractor({ onItemsExtracted }) {
  const [status, setStatus] = useState(STATUS.IDLE);
  const [items, setItems] = useState([]);
  const [fileName, setFileName] = useState("");
  const [errorMsg, setErrorMsg] = useState("");
  const [dragOver, setDragOver] = useState(false);
  const fileRef = useRef();

  async function handleFile(file) {
    if (!file || file.type !== "application/pdf") {
      setErrorMsg("Please upload a PDF file.");
      setStatus(STATUS.ERROR);
      return;
    }

    setFileName(file.name);
    setStatus(STATUS.LOADING);
    setItems([]);
    setErrorMsg("");

    // Convert PDF to base64
    const base64 = await new Promise((res, rej) => {
      const reader = new FileReader();
      reader.onload = () => res(reader.result.split(",")[1]);
      reader.onerror = () => rej(new Error("Failed to read file"));
      reader.readAsDataURL(file);
    });

    const GEMINI_API_KEY = "YOUR_GEMINI_API_KEY"; // replace with your key
    const GEMINI_MODEL = "gemini-1.5-flash";

    try {
      const response = await fetch(
        `https://generativelanguage.googleapis.com/v1beta/models/${GEMINI_MODEL}:generateContent?key=${GEMINI_API_KEY}`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            systemInstruction: {
              parts: [{ text: `You are a cargo inspection assistant. Extract only the item names from the cargo packing list PDF. Return ONLY a valid JSON array of strings, no preamble, no markdown, no explanation. Example: ["Laptop Computer","Mobile Phones","USB Cables"]` }]
            },
            contents: [{
              role: "user",
              parts: [
                { inlineData: { mimeType: "application/pdf", data: base64 } },
                { text: "Extract all item names from this cargo packing list. Return only the JSON array." }
              ]
            }],
            generationConfig: { maxOutputTokens: 1000 }
          }),
        }
      );

      const data = await response.json();
      if (!response.ok) throw new Error(data.error?.message || "Gemini API error");

      const raw = data.candidates?.[0]?.content?.parts?.[0]?.text || "[]";
      const clean = raw.replace(/```json|```/g, "").trim();
      const parsed = JSON.parse(clean);

      setItems(parsed);
      setStatus(STATUS.DONE);
      if (onItemsExtracted) onItemsExtracted(parsed);
    } catch (err) {
      setErrorMsg(err.message || "Extraction failed.");
      setStatus(STATUS.ERROR);
    }
  }

  function onDrop(e) {
    e.preventDefault();
    setDragOver(false);
    handleFile(e.dataTransfer.files[0]);
  }

  function onInputChange(e) {
    handleFile(e.target.files[0]);
  }

  function reset() {
    setStatus(STATUS.IDLE);
    setItems([]);
    setFileName("");
    setErrorMsg("");
    if (fileRef.current) fileRef.current.value = "";
  }

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <span style={styles.headerIcon}>📋</span>
        <div>
          <div style={styles.headerTitle}>Packing List Extractor</div>
          <div style={styles.headerSub}>Upload a cargo PDF — AI extracts the item list automatically</div>
        </div>
      </div>

      {/* Upload Zone */}
      {status === STATUS.IDLE || status === STATUS.ERROR ? (
        <div
          style={{ ...styles.dropZone, ...(dragOver ? styles.dropZoneActive : {}) }}
          onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
          onDragLeave={() => setDragOver(false)}
          onDrop={onDrop}
          onClick={() => fileRef.current?.click()}
        >
          <input ref={fileRef} type="file" accept="application/pdf" style={{ display: "none" }} onChange={onInputChange} />
          <div style={styles.dropIcon}>📄</div>
          <div style={styles.dropTitle}>Drop your packing list PDF here</div>
          <div style={styles.dropSub}>or click to browse</div>
          {status === STATUS.ERROR && (
            <div style={styles.errorBadge}>⚠ {errorMsg}</div>
          )}
        </div>
      ) : null}

      {/* Loading State */}
      {status === STATUS.LOADING && (
        <div style={styles.loadingBox}>
          <div style={styles.spinner} />
          <div style={styles.loadingText}>Extracting items from <strong>{fileName}</strong>...</div>
          <div style={styles.loadingSub}>Claude is reading your packing list</div>
        </div>
      )}

      {/* Results */}
      {status === STATUS.DONE && (
        <div style={styles.resultsBox}>
          <div style={styles.resultsHeader}>
            <div>
              <div style={styles.resultsTitle}>✅ {items.length} items extracted</div>
              <div style={styles.resultsSub}>from {fileName}</div>
            </div>
            <button style={styles.resetBtn} onClick={reset}>Upload another</button>
          </div>

          <div style={styles.listWrapper}>
            {items.map((name, i) => (
              <div key={i} style={i % 2 === 0 ? {...styles.listItem, ...styles.listItemEven} : styles.listItem}>
                <span style={styles.listNum}>{i + 1}</span>
                <span style={styles.listName}>{name}</span>
              </div>
            ))}
          </div>

          {/* JSON Export */}
          <details style={styles.details}>
            <summary style={styles.summary}>View raw JSON output</summary>
            <pre style={styles.pre}>{JSON.stringify(items, null, 2)}</pre>
          </details>
        </div>
      )}
    </div>
  );
}

const styles = {
  container: {
    fontFamily: "'IBM Plex Sans', 'Segoe UI', sans-serif",
    background: "#0f1117",
    color: "#e2e8f0",
    borderRadius: 12,
    border: "1px solid #1e2433",
    overflow: "hidden",
    maxWidth: 860,
    margin: "0 auto",
  },
  header: {
    display: "flex",
    alignItems: "center",
    gap: 14,
    padding: "18px 24px",
    borderBottom: "1px solid #1e2433",
    background: "#0a0d14",
  },
  headerIcon: { fontSize: 28 },
  headerTitle: { fontSize: 16, fontWeight: 600, color: "#f1f5f9" },
  headerSub: { fontSize: 13, color: "#64748b", marginTop: 2 },

  dropZone: {
    margin: 24,
    border: "2px dashed #1e2433",
    borderRadius: 10,
    padding: "48px 24px",
    textAlign: "center",
    cursor: "pointer",
    transition: "all .2s",
    background: "#0a0d14",
  },
  dropZoneActive: {
    borderColor: "#3b82f6",
    background: "#0f1827",
  },
  dropIcon: { fontSize: 40, marginBottom: 12 },
  dropTitle: { fontSize: 15, fontWeight: 500, color: "#cbd5e1", marginBottom: 4 },
  dropSub: { fontSize: 13, color: "#475569" },
  errorBadge: {
    marginTop: 14,
    display: "inline-block",
    background: "#2d1515",
    color: "#f87171",
    border: "1px solid #7f1d1d",
    borderRadius: 6,
    padding: "6px 14px",
    fontSize: 13,
  },

  loadingBox: {
    padding: "56px 24px",
    textAlign: "center",
  },
  spinner: {
    width: 36,
    height: 36,
    border: "3px solid #1e2433",
    borderTop: "3px solid #3b82f6",
    borderRadius: "50%",
    animation: "spin 0.8s linear infinite",
    margin: "0 auto 18px",
  },
  loadingText: { fontSize: 15, color: "#cbd5e1", marginBottom: 4 },
  loadingSub: { fontSize: 13, color: "#475569" },

  resultsBox: { padding: 24 },
  resultsHeader: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 16,
  },
  resultsTitle: { fontSize: 15, fontWeight: 600, color: "#4ade80" },
  resultsSub: { fontSize: 12, color: "#475569", marginTop: 2 },
  resetBtn: {
    background: "#1e2433",
    color: "#94a3b8",
    border: "1px solid #334155",
    borderRadius: 6,
    padding: "6px 14px",
    fontSize: 13,
    cursor: "pointer",
  },

  listWrapper: { borderRadius: 8, border: "1px solid #1e2433", overflow: "hidden" },
  listItem: { display: "flex", alignItems: "center", gap: 12, padding: "10px 16px", borderBottom: "1px solid #1a1f2e", background: "#0c0f1a" },
  listItemEven: { background: "#0f1117" },
  listNum: { fontSize: 12, color: "#475569", minWidth: 24, textAlign: "right" },
  listName: { fontSize: 14, color: "#e2e8f0" },

  details: { marginTop: 16 },
  summary: { fontSize: 12, color: "#475569", cursor: "pointer", marginBottom: 8 },
  pre: {
    background: "#0a0d14",
    border: "1px solid #1e2433",
    borderRadius: 6,
    padding: 14,
    fontSize: 12,
    color: "#64748b",
    overflowX: "auto",
    maxHeight: 200,
    overflowY: "auto",
  },
};

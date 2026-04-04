# SHAP Integration Guide for React Frontend

## Overview

Your backend (FastAPI + YOLOv8 + SHAP) is now working correctly and returns SHAP-based explainability in the API response.

The next step is to **integrate SHAP output into your React frontend**.

---

# 1. Backend Response Structure

Your `/api/analyze` endpoint should return something like:

```json
{
  "detections": [...],
  "risk": {...},
  "outputs": {
    "gradcam": "...",
    "shap": {
      "label": "Gun",
      "confidence": 0.684,
      "strength": "Medium",
      "reliability": "Moderate",
      "coverage": 31.25,
      "verdict": "Suspicious object detected with moderate confidence."
    }
  }
}
```

---

# 2. Frontend Integration Strategy

You need to:

1. Call API
2. Extract SHAP data
3. Display it in UI

---

# 3. API Call in React

## Example (using fetch)

```javascript
const analyzeImage = async (file) => {
  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch("https://your-ngrok-url/api/analyze", {
    method: "POST",
    body: formData,
  });

  const data = await res.json();
  return data;
};
```

---

# 4. Extract SHAP Data

```javascript
const shapData = data.outputs?.shap;
```

---

# 5. Create SHAP Component

## File: `ShapAnalysis.jsx`

```javascript
import React from "react";

const ShapAnalysis = ({ shap }) => {
  if (!shap) return null;

  const getColor = () => {
    if (shap.strength === "High") return "#ff4444";
    if (shap.strength === "Medium") return "#ffaa00";
    return "#44bb44";
  };

  return (
    <div style={{
      background: "#1a1a2e",
      padding: "16px",
      borderRadius: "10px",
      marginTop: "20px",
      color: "white"
    }}>
      <h3>Explainability Analysis (SHAP)</h3>

      <p><b>Object:</b> {shap.label}</p>
      <p><b>Confidence:</b> {(shap.confidence * 100).toFixed(1)}%</p>

      <hr />

      <p>
        <b>Explanation Strength:</b>{" "}
        <span style={{ color: getColor() }}>
          {shap.strength} ({shap.coverage.toFixed(1)}%)
        </span>
      </p>

      <p><b>Model Reliability:</b> {shap.reliability}</p>

      <hr />

      <p>
        <b>Verdict:</b><br />
        {shap.verdict}
      </p>
    </div>
  );
};

export default ShapAnalysis;
```

---

# 6. Use Component in Main Page

```javascript
import ShapAnalysis from "./ShapAnalysis";

const [result, setResult] = useState(null);

const handleUpload = async (file) => {
  const data = await analyzeImage(file);
  setResult(data);
};
```

---

## Render in JSX

```javascript
{result && result.outputs?.shap && (
  <ShapAnalysis shap={result.outputs.shap} />
)}
```

---

# 7. Optional: Add SHAP Heatmap Image

Currently, you are NOT returning SHAP image.

## Backend Improvement (Optional)

Save SHAP heatmap:

```python
heatmap_path = "outputs/shap_heatmap.png"
outputs["shap"]["image"] = heatmap_path
```

---

## Frontend Display

```javascript
{shap.image && (
  <img
    src={`https://your-ngrok-url/api/files?path=${shap.image}`}
    alt="SHAP Heatmap"
    style={{ width: "100%", marginTop: "10px" }}
  />
)}
```

---

# 8. UI Design Suggestions

### Use Cards

* Detection Card
* Grad-CAM Card
* SHAP Card

---

### Color Coding

| Strength | Color  |
| -------- | ------ |
| High     | Red    |
| Medium   | Orange |
| Low      | Green  |

---

# 9. Performance Considerations

* SHAP is slow (~6–12 sec)
* Show loading spinner:

```javascript
{loading && <p>Analyzing image... (SHAP running)</p>}
```

---

# 10. Error Handling

```javascript
if (!result.outputs?.shap) {
  return <p>No explainability data available</p>;
}
```

---

# 11. Final Architecture

```text
React Frontend
      ↓
FastAPI (Colab GPU)
      ↓
YOLO Detection
      ↓
SHAP Analysis
      ↓
JSON Response
      ↓
React UI Rendering
```

---

# 12. Summary

You have now:

* Detection ✔️
* Explainability ✔️
* API ✔️
* Frontend integration ✔️

This is a **complete Explainable AI system**.

---

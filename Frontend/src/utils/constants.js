export const PROHIBITED_TERMS = ["Gun", "Bullet", "Knife"];
export const SUSPICIOUS_TERMS = [
  "Baton",
  "Plier", 
  "Hammer",
  "Powerbank",
  "Scissors",
  "Wrench",
  "Sprayer",
  "HandCuffs",
  "Lighter"
];

export const PROHIBITED_TERMS_LOWER = new Set(
  PROHIBITED_TERMS.map(term => term.toLowerCase())
);
export const SUSPICIOUS_TERMS_LOWER = new Set(
  SUSPICIOUS_TERMS.map(term => term.toLowerCase())
);

export const DUMMY_DETECTIONS = [
  {
    id: 1,
    label: "Gun",
    confidence: 0.85,
    category: "prohibited",
    bbox: { x: 120, y: 200, width: 150, height: 100 }
  },
  {
    id: 2,
    label: "Knife", 
    confidence: 0.62,
    category: "prohibited",
    bbox: { x: 300, y: 150, width: 80, height: 40 }
  },
  {
    id: 3,
    label: "Battery Pack",
    confidence: 0.45,
    category: "suspicious",
    bbox: { x: 50, y: 300, width: 100, height: 60 }
  },
  {
    id: 4,
    label: "Laptop",
    confidence: 0.23,
    category: "clear",
    bbox: { x: 400, y: 250, width: 200, height: 150 }
  }
];

export const DUMMY_RISK = {
  level: "PROHIBITED",
  score: 85,
  reason: "Firearms detected with high confidence. Manifest mismatch found - 2 items undeclared."
};

export const MODEL_METRICS = {
  "mAP@0.5": 0.924,
  "Precision": 0.933,
  "Recall": 0.862,
  "Model": "YOLOv8m",
  "Dataset": "PIXray Partial Sixray"
};

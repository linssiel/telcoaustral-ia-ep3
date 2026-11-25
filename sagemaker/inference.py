import os
import json
import joblib
import numpy as np

CONFIDENCE_THRESHOLD = 0.75

def model_fn(model_dir):
    model_path = os.path.join(model_dir, "model.joblib")
    return joblib.load(model_path)

def input_fn(request_body, request_content_type):
    if request_content_type == "application/json":
        data = json.loads(request_body)
        return data.get("text", "")
    raise ValueError(f"Content-Type no soportado: {request_content_type}")

def predict_fn(input_data, model):
    probas = model.predict_proba([input_data])[0]
    classes = model.classes_
    top_idx = int(np.argmax(probas))
    confidence = float(probas[top_idx])
    predicted_intent = str(classes[top_idx])

    top3_idx = np.argsort(probas)[::-1][:3]
    explainability = [
        {"intent": str(classes[i]), "probability": round(float(probas[i]), 4)}
        for i in top3_idx
    ]

    requires_human_handoff = (
        confidence < CONFIDENCE_THRESHOLD
        or predicted_intent in ["reclamo_cobro", "baja_servicio"]
    )

    return {
        "predicted_intent": predicted_intent,
        "confidence": round(confidence, 4),
        "threshold": CONFIDENCE_THRESHOLD,
        "requires_human_handoff": requires_human_handoff,
        "explainability_top3": explainability
    }

def output_fn(prediction, response_content_type):
    return json.dumps(prediction), "application/json"
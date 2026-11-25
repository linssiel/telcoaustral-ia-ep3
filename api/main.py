import os
import json
import time
import joblib
import boto3
import numpy as np
from fastapi import FastAPI, Depends, Request
from pydantic import BaseModel, Field
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from api.security import verify_api_key, sanitize_pii, check_input_guardrails
from api.rabbitmq_producer import publish_siebel_event

# Configuración de Rate Limiting (Seguridad IE7)
limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="TelcoAustral AI Chatbot API",
    description="API REST empresarial con AWS SageMaker, RAG FAQ, Guardrails PII (Ley 21.719) y mensajería distribuida RabbitMQ -> CRM Siebel.",
    version="1.0.0"
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Cargar FAQs corporativas y modelo local de respaldo
with open("data/faqs_telcoaustral.json", "r", encoding="utf-8") as f:
    FAQS_DB = {item["intent"]: item for item in json.load(f)}

LOCAL_MODEL = joblib.load("model_artifacts/model.joblib")
SAGEMAKER_ENDPOINT = os.getenv("SAGEMAKER_ENDPOINT_NAME", "")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")

# Métricas en memoria para observabilidad rápida
METRICS_STATE = {
    "total_requests": 0,
    "blocked_guardrails": 0,
    "human_handoffs": 0,
    "siebel_events_sent": 0,
    "latencies_ms": []
}

class ChatRequest(BaseModel):
    user_id: str = Field(..., example="cliente_500123")
    channel: str = Field(..., example="WhatsApp", description="Canal: Web, WhatsApp o App")
    message: str = Field(..., example="Hola, mi rut es 18.456.789-2 y se me cayó la fibra óptica hace rato")

def predict_with_sagemaker_or_local(text: str) -> tuple[dict, str]:
    """
    Invoca el endpoint real de AWS SageMaker si está configurado;
    de lo contrario usa el artefacto entrenado localmente.
    """
    if SAGEMAKER_ENDPOINT:
        try:
            runtime = boto3.client("sagemaker-runtime", region_name=AWS_REGION)
            response = runtime.invoke_endpoint(
                EndpointName=SAGEMAKER_ENDPOINT,
                ContentType="application/json",
                Body=json.dumps({"text": text})
            )
            result = json.loads(response["Body"].read().decode("utf-8"))
            return result, f"AWS SageMaker ({SAGEMAKER_ENDPOINT})"
        except Exception as e:
            print(f"[WARN] Fallback a modelo local por error SageMaker: {e}")

    probas = LOCAL_MODEL.predict_proba([text])[0]
    classes = LOCAL_MODEL.classes_
    top_idx = int(np.argmax(probas))
    confidence = float(probas[top_idx])
    predicted_intent = str(classes[top_idx])
    top3_idx = np.argsort(probas)[::-1][:3]
    explainability = [
        {"intent": str(classes[i]), "probability": round(float(probas[i]), 4)}
        for i in top3_idx
    ]
    requires_handoff = confidence < 0.75 or predicted_intent in ["reclamo_cobro", "baja_servicio"]

    return {
        "predicted_intent": predicted_intent,
        "confidence": round(confidence, 4),
        "threshold": 0.75,
        "requires_human_handoff": requires_handoff,
        "explainability_top3": explainability
    }, "Local Model Artifact (SageMaker-compatible)"

@app.get("/health", tags=["Operación"])
def health_check():
    return {
        "status": "healthy",
        "service": "TelcoAustral Chatbot API",
        "sagemaker_endpoint": SAGEMAKER_ENDPOINT or "local-fallback-active"
    }

@app.get("/metrics", tags=["Observabilidad"], dependencies=[Depends(verify_api_key)])
def get_metrics():
    lats = METRICS_STATE["latencies_ms"]
    avg_lat = round(sum(lats) / len(lats), 2) if lats else 0.0
    p95_lat = round(float(np.percentile(lats, 95)), 2) if lats else 0.0
    total = METRICS_STATE["total_requests"]
    handoff_rate = round((METRICS_STATE["human_handoffs"] / total) * 100, 2) if total else 0.0

    return {
        "total_requests": total,
        "blocked_guardrails": METRICS_STATE["blocked_guardrails"],
        "human_handoffs": METRICS_STATE["human_handoffs"],
        "handoff_rate_percent": handoff_rate,
        "siebel_events_sent": METRICS_STATE["siebel_events_sent"],
        "latency_avg_ms": avg_lat,
        "latency_p95_ms": p95_lat,
        "sla_target_ms": 3000
    }

@app.post("/api/v1/chat", tags=["Inferencia IA"], dependencies=[Depends(verify_api_key)])
@limiter.limit("100/minute")
def chat_endpoint(request: Request, payload: ChatRequest):
    start_time = time.perf_counter()
    METRICS_STATE["total_requests"] += 1

    # 1. Input Guardrail (Seguridad)
    is_safe, guardrail_msg = check_input_guardrails(payload.message)
    if not is_safe:
        METRICS_STATE["blocked_guardrails"] += 1
        return {
            "status": "blocked",
            "guardrail_reason": guardrail_msg,
            "response_text": "Lo siento, tu mensaje contiene patrones no permitidos por nuestras políticas de seguridad."
        }

    # 2. Anonimización PII (Ley 19.628 / 21.719)
    clean_text, pii_detected = sanitize_pii(payload.message)

    # 3. Inferencia de Intención (SageMaker / Modelo)
    prediction, inference_backend = predict_with_sagemaker_or_local(clean_text)
    intent = prediction["predicted_intent"]

    # 4. Recuperación de Conocimiento (RAG FAQ)
    faq_entry = FAQS_DB.get(intent, {
        "faq_id": "FAQ-000",
        "respuesta": "Derivando tu consulta con un ejecutivo especializado de TelcoAustral.",
        "requiere_siebel": True
    })

    # 5. Integración Asíncrona con RabbitMQ -> CRM Siebel si aplica
    siebel_status = {"queued": False, "detail": "No requiere gestión en CRM Siebel"}
    if faq_entry["requiere_siebel"] or prediction["requires_human_handoff"]:
        siebel_status = publish_siebel_event({
            "user_id": payload.user_id,
            "channel": payload.channel,
            "sanitized_query": clean_text,
            "intent": intent,
            "confidence": prediction["confidence"],
            "human_handoff": prediction["requires_human_handoff"]
        })
        METRICS_STATE["siebel_events_sent"] += 1

    if prediction["requires_human_handoff"]:
        METRICS_STATE["human_handoffs"] += 1

    elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
    METRICS_STATE["latencies_ms"].append(elapsed_ms)

    return {
        "status": "ok",
        "channel": payload.channel,
        "latency_ms": elapsed_ms,
        "sla_compliant": elapsed_ms < 3000,
        "privacy": {
            "sanitized_text": clean_text,
            "pii_masked": pii_detected
        },
        "ai_interpretability": {
            "inference_engine": inference_backend,
            "predicted_intent": intent,
            "confidence": prediction["confidence"],
            "confidence_threshold": prediction["threshold"],
            "requires_human_handoff": prediction["requires_human_handoff"],
            "top3_probabilities": prediction["explainability_top3"],
            "rag_source_id": faq_entry["faq_id"]
        },
        "response_text": faq_entry["respuesta"],
        "distributed_crm_event": siebel_status
    }
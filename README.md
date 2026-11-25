# 📡 Caso 2: Chatbot Inteligente - TelcoAustral

> **Evaluación Parcial N° 3 — Arquitectura de Sistemas de Inteligencia Artificial (Duoc UC)**  
> Solución empresarial distribuida para atención omnicanal (500.000 clientes) con **AWS SageMaker AI**, **FastAPI**, **RAG**, **RabbitMQ**, observabilidad en **Streamlit** y cumplimiento normativo (**Leyes N° 19.628 / N° 21.719** y **MITRE ATLAS**).

---

## 1. Arquitectura y Flujo del Sistema (IE2, IE7)

[Cliente Web / WhatsApp] --> [Streamlit Dashboard :8501]
                                      |
                                      v (POST /api/v1/chat + X-API-Key)
                       [FastAPI API Gateway :8000]
                         |-- 1. Rate Limiting (100 req/min) & MITRE Guardrails
                         |-- 2. Sanitizacion PII ([RUT_ANONIMIZADO], Email, Tel)
                         |-- 3. Inferencia NLP (AWS SageMaker / Fallback Local)
                         |-- 4. Recuperacion RAG (data/faqs_telcoaustral.json)
                         +-- 5. Cola Asincrona (RabbitMQ --> Siebel CRM Worker)

## 2. Estructura del Repositorio

| Ruta / Archivo | Descripción Técnica |
| :--- | :--- |
| `api/main.py` | API Gateway RESTful (`/health`, `/metrics`, `POST /api/v1/chat`) con Swagger UI (`/docs`). |
| `api/security.py` | Anonimización PII (Ley 21.719), validación `X-API-Key` y *Input Guardrails* contra *Prompt Injection*. |
| `api/rabbitmq_producer.py` | Publicador desacoplado de eventos hacia colas distribuidas con patrón *Circuit Breaker*. |
| `sagemaker/train.py` | Entrenamiento del pipeline `TfidfVectorizer` + `LogisticRegression` (1.200 muestras en español chileno). |
| `sagemaker/inference.py` | Manejador de inferencia compatible con contenedores AWS SageMaker Scikit-Learn (`model_fn`, `predict_fn`). |
| `sagemaker/deploy_aws.py` | Automatización MLOps con `boto3` (empaquetado `model_deploy.tar.gz`, carga S3 y registro en SageMaker AI). |
| `dashboard/app.py` | Interfaz omnicanal e interpretabilidad ejecutiva (probabilidades Top-3, umbral 75% y trazabilidad SLA). |
| `worker/siebel_worker.py` | Consumidor asíncrono para generación automática de tickets en CRM Siebel (`TCK-XXXXXXXX`). |
| `tests/test_suite.py` | Suite de 10 pruebas unitarias y de integración automatizadas con `pytest`. |
| `locustfile.py` | Escenario de pruebas de carga y estrés concurrente con `Locust`. |
| `Dockerfile` | Contenedorización reproducible del servicio productivo. |

## 3. Despliegue Cloud en AWS Academy (IE1, IE4, IE5)

* **Almacenamiento S3:** `s3://sagemaker-us-east-1-000416566918/telcoaustral-ep3/model/model_deploy.tar.gz` (`35.1 KB`).
* **Modelo Registrado en SageMaker AI:** `telcoaustral-sklearn-model-1795644777` (Región `us-east-1`, Rol `LabRole`).
* **Continuidad Operativa (*Fallback Local*):** Ante la restricción de políticas Sandbox (`Pvoclabs2`) sobre `sagemaker:CreateEndpointConfig`, el orquestador FastAPI conmuta automáticamente al artefacto local manteniendo idéntico contrato JSON y latencias `< 15 ms`.

## 4. Resultados de Calidad y Rendimiento (IE10)

* **Métricas del Modelo (240 muestras de prueba):** `Accuracy = 100%`, `Precision = 1.00`, `Recall = 1.00`, `F1-Score = 1.00`.
* **Pruebas Automatizadas (`pytest -v`):** **10/10 casos `PASSED`** en `5.68s` (PII, Guardrails, Auth, RAG, Siebel y SLA).
* **Prueba de Carga (`Locust`, 50 usuarios concurrentes):** `262 requests`, **`0.00%` errores**, **`17.78 RPS`**, `p50 = 2000 ms`, `p95 = 2000 ms`, **`p99 = 2200 ms`** (cumple SLA `< 3000 ms`).

## 5. Instalación y Ejecución Local / Docker

### Ejecución Local
* `pip install -r requirements.txt`
* `uvicorn api.main:app --host 0.0.0.0 --port 8000`
* `streamlit run dashboard/app.py`
* `python -m pytest -v`

### Construcción con Docker
* `docker build -t telcoaustral-ai-ep3 .`
* `docker run -p 8000:8000 telcoaustral-ai-ep3`

import re
from fastapi import Security, HTTPException, status
from fastapi.security.api_key import APIKeyHeader

API_KEY_NAME = "X-API-Key"
VALID_API_KEY = "telcoaustral-ep3-secret-2026"

api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

async def verify_api_key(api_key: str = Security(api_key_header)):
    if api_key != VALID_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API Key inválida o ausente. Incluye el header 'X-API-Key'."
        )
    return api_key

def sanitize_pii(text: str) -> tuple[str, list[str]]:
    """
    Sanitiza datos personales (Ley N° 19.628 y N° 21.719 - Plan Seguridad EP2).
    Retorna el texto anonimizado y la lista de entidades detectadas.
    """
    detected = []
    sanitized = text

    # Detección de RUT chileno (ej: 12.345.678-9 o 12345678-K)
    rut_pattern = r"\b\d{1,2}\.?\d{3}\.?\d{3}-[\dkK]\b"
    if re.search(rut_pattern, sanitized):
        sanitized = re.sub(rut_pattern, "[RUT_ANONIMIZADO]", sanitized)
        detected.append("RUT")

    # Detección de correos electrónicos
    email_pattern = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
    if re.search(email_pattern, sanitized):
        sanitized = re.sub(email_pattern, "[EMAIL_ANONIMIZADO]", sanitized)
        detected.append("EMAIL")

    # Detección de teléfonos móviles chilenos (+569XXXXXXXX o 9XXXXXXXX)
    phone_pattern = r"(\+?56\s?9\s?\d{4}\s?\d{4}|\b9\d{8}\b)"
    if re.search(phone_pattern, sanitized):
        sanitized = re.sub(phone_pattern, "[TELEFONO_ANONIMIZADO]", sanitized)
        detected.append("TELEFONO")

    return sanitized, detected

def check_input_guardrails(text: str) -> tuple[bool, str]:
    """
    Input Guardrails (MITRE ATLAS AML.T0051 - Prompt Injection / Jailbreak).
    """
    blocked_patterns = [
        "ignore previous instructions",
        "ignora las instrucciones",
        "system prompt",
        "drop table",
        "<script>",
        "modo desarrollador"
    ]
    lower_text = text.lower()
    for pattern in blocked_patterns:
        if pattern in lower_text:
            return False, f"Bloqueado por Input Guardrail (patrón no permitido: '{pattern}')"
    return True, "OK"
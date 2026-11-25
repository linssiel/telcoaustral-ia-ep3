import os
import json
import random
import pandas as pd

os.makedirs("data", exist_ok=True)

FAQS = [
    {
        "faq_id": "FAQ-001",
        "intent": "consulta_boleta",
        "pregunta": "¿Cómo puedo revisar o descargar mi boleta mensual?",
        "respuesta": "Puedes descargar tu boleta en PDF desde la Sucursal Virtual en telcoaustral.cl o en la App Mi TelcoAustral ingresando con tu RUT y clave.",
        "requiere_siebel": False
    },
    {
        "faq_id": "FAQ-002",
        "intent": "soporte_tecnico_internet",
        "pregunta": "Mi internet fibra óptica está lento o sin señal",
        "respuesta": "Reinicia tu router ONT desenchufándolo por 30 segundos. Si la luz LOS sigue parpadeando en rojo, hemos generado un ticket técnico automático en Siebel.",
        "requiere_siebel": True
    },
    {
        "faq_id": "FAQ-003",
        "intent": "cambio_plan",
        "pregunta": "¿Cómo cambio mi plan móvil o aumento mis gigas?",
        "respuesta": "Puedes actualizar tu plan sin costo de habilitación desde la sección 'Mi Plan' en la App o solicitar el cambio ejecutivo aquí mismo.",
        "requiere_siebel": True
    },
    {
        "faq_id": "FAQ-004",
        "intent": "roaming_internacional",
        "pregunta": "¿Cómo activo el roaming para viajar fuera de Chile?",
        "respuesta": "Activa tu bolsa Roaming Libre 24 horas antes de viajar en la App Mi TelcoAustral. Disponible en América y Europa sin cambio de chip.",
        "requiere_siebel": False
    },
    {
        "faq_id": "FAQ-005",
        "intent": "reclamo_cobro",
        "pregunta": "Me aparece un cobro desconocido o duplicado en mi cuenta",
        "respuesta": "Lamentamos el inconveniente. Tu caso requiere revisión de facturación detallada, por lo que lo estamos derivando con prioridad a un ejecutivo humano y registrando el folio en Siebel.",
        "requiere_siebel": True
    },
    {
        "faq_id": "FAQ-006",
        "intent": "baja_servicio",
        "pregunta": "Quiero dar de baja o cancelar mi servicio",
        "respuesta": "Para gestionar solicitudes de término de contrato de forma segura según normativa vigente, te comunicaremos de inmediato con un especialista de retención.",
        "requiere_siebel": True
    }
]

EJEMPLOS_CHILENOS = {
    "consulta_boleta": [
        "hola necesito ver mi boleta de este mes porfa",
        "cuanto me salio la cuenta del telefono este mes",
        "no me ha llegado la factura al correo",
        "donde pago mi cuenta atrasada de internet",
        "quiero saber la fecha de vencimiento de mi boleta",
        "me pueden mandar el detalle de lo que me cobraron en la boleta",
        "necesito descargar la boleta con mi rut",
        "cuanto debo en mi plan hogar"
    ],
    "soporte_tecnico_internet": [
        "se me cayo el internet de la casa hace rato y no vuelve",
        "la fibra optica anda super lenta no carga nada",
        "el router tiene una luz roja prendida que hago",
        "estoy sin señal en el wifi desde la mañana",
        "se corta a cada rato la conexion del internet hogar",
        "no tengo red en el telefono ni datos moviles",
        "necesito que venga un tecnico a revisar el modem",
        "esta caida la señal de telcoaustral en mi sector"
    ],
    "cambio_plan": [
        "quiero cambiarme a un plan con mas gigas",
        "tienen alguna promo para subir los megas de la fibra",
        "necesito portar un numero a telcoaustral",
        "quiero contratar un plan multimedia mas barato",
        "como subo los minutos y datos de mi plan actual",
        "busco mejorar mi plan hogar con television",
        "quiero renovar mi equipo y cambiar de plan",
        "me interesa contratar internet fibra optica"
    ],
    "roaming_internacional": [
        "viajo a argentina mañana como activo el roaming",
        "cuanto sale la bolsa de datos para usar el celu en brasil",
        "voy a europa y necesito tener internet en el telefono",
        "mi plan incluye roaming libre en sudamerica",
        "no me funciona el roaming estando fuera de chile",
        "como habilito los datos internacionales antes de volar",
        "precios de bolsas roaming para estados unidos",
        "necesito activar el servicio internacional en mi linea"
    ],
    "reclamo_cobro": [
        "me estan cobrando de mas en la boleta de este mes",
        "aparece un cargo raro que yo nunca contrate",
        "pague la cuenta ayer y todavia me sale deuda",
        "me cobraron doble este mes quiero un reembolso",
        "no corresponde el monto de mi factura hubo un error",
        "reclamo por cobro indebido en servicios adicionales",
        "me subieron el plan sin avisarme y me cobraron mas",
        "quiero desconocer un cobro en mi estado de cuenta"
    ],
    "baja_servicio": [
        "quiero dar de baja el internet hogar ahora ya",
        "necesito cancelar mi plan movil no lo voy a usar mas",
        "como renuncio al servicio de telcoaustral",
        "quiero terminar el contrato de fibra optica",
        "me voy de la casa y necesito cortar el servicio",
        "dar de baja mi linea telefonica definitivamente",
        "quiero anular mi suscripcion con ustedes",
        "solicito la desactivacion total de mis servicios"
    ]
}

variaciones_inicio = ["", "hola ", "buenas tardes ", "disculpa ", "oye ", "por favor ", "necesito ayuda, "]
variaciones_fin = ["", " porfa", " gracias", " urgente", " por favor", " hoy dia", " al tiro"]

rows = []
random.seed(42)

for _ in range(200):
    for intent, frases in EJEMPLOS_CHILENOS.items():
        base = random.choice(frases)
        texto = f"{random.choice(variaciones_inicio)}{base}{random.choice(variaciones_fin)}".strip()
        rows.append({"text": texto, "intent": intent})

df = pd.DataFrame(rows).sample(frac=1, random_state=42).reset_index(drop=True)
df.to_csv("data/telcoaustral_tickets.csv", index=False, encoding="utf-8")

with open("data/faqs_telcoaustral.json", "w", encoding="utf-8") as f:
    json.dump(FAQS, f, ensure_ascii=False, indent=2)

print(f"Dataset generado: {len(df)} registros en data/telcoaustral_tickets.csv")
print(f"FAQs generadas: {len(FAQS)} artículos en data/faqs_telcoaustral.json")
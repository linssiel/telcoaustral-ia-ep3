import random
from locust import HttpUser, task, between

CONSULTAS_CHILENAS = [
    "hola necesito ver mi boleta de este mes porfa",
    "se me cayo el internet de la casa hace rato y no vuelve",
    "quiero cambiarme a un plan con mas gigas",
    "viajo a argentina mañana como activo el roaming",
    "me estan cobrando de mas en la boleta de este mes",
    "mi rut es 15.234.567-8 y quiero descargar mi factura"
]

class TelcoAustralUser(HttpUser):
    wait_time = between(0.5, 1.5)

    @task
    def send_chat_message(self):
        self.client.post(
            "/api/v1/chat",
            headers={"X-API-Key": "telcoaustral-ep3-secret-2026"},
            json={
                "user_id": f"load_user_{random.randint(1, 1000)}",
                "channel": random.choice(["Web", "WhatsApp", "App Móvil"]),
                "message": random.choice(CONSULTAS_CHILENAS)
            }
        )
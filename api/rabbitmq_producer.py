import os
import json
import uuid
from datetime import datetime, timezone
import pika

RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")
QUEUE_NAME = "siebel_tickets_queue"

def publish_siebel_event(payload: dict) -> dict:
    """
    Publica un evento asíncrono hacia RabbitMQ para ser procesado por el Worker CRM Siebel.
    Si RabbitMQ no está levantado aún en local, registra fallback seguro sin bloquear el chat (<3s).
    """
    event_id = f"TCK-{uuid.uuid4().hex[:8].upper()}"
    message = {
        "event_id": event_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source": "TelcoAustral-Chatbot-API",
        **payload
    }

    try:
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(host=RABBITMQ_HOST, connection_attempts=1, socket_timeout=1)
        )
        channel = connection.channel()
        channel.queue_declare(queue=QUEUE_NAME, durable=True)
        channel.basic_publish(
            exchange="",
            routing_key=QUEUE_NAME,
            body=json.dumps(message, ensure_ascii=False),
            properties=pika.BasicProperties(delivery_mode=2)  # Mensaje persistente
        )
        connection.close()
        return {"queued": True, "broker": "RabbitMQ", "queue": QUEUE_NAME, "ticket_id": event_id}
    except Exception as e:
        return {
            "queued": False,
            "broker": "RabbitMQ (offline-fallback)",
            "ticket_id": event_id,
            "detail": str(e)
        }
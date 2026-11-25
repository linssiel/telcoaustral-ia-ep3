import os
import json
import time
import pika

RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")
QUEUE_NAME = "siebel_tickets_queue"

class SiebelCircuitBreaker:
    """Patrón Circuit Breaker definido en Plan de Seguridad EP2 (umbral 5s)."""
    def __init__(self, failure_threshold=3, recovery_timeout=15):
        self.failures = 0
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.state = "CLOSED"
        self.opened_at = 0

    def allow_request(self) -> bool:
        if self.state == "OPEN":
            if time.time() - self.opened_at > self.recovery_timeout:
                self.state = "HALF-OPEN"
                return True
            return False
        return True

    def record_success(self):
        self.failures = 0
        self.state = "CLOSED"

    def record_failure(self):
        self.failures += 1
        if self.failures >= self.failure_threshold:
            self.state = "OPEN"
            self.opened_at = time.time()

cb = SiebelCircuitBreaker()

def process_siebel_ticket(ch, method, properties, body):
    event = json.loads(body.decode("utf-8"))
    print(f"\n[RabbitMQ -> Siebel Worker] Recibido evento: {event['event_id']}")

    if not cb.allow_request():
        print(f"[CIRCUIT BREAKER OPEN] Siebel legacy saturado. Reencolando {event['event_id']}...")
        time.sleep(2)
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
        return

    # Simula inserción controlada en CRM Siebel legacy (< 500ms)
    time.sleep(0.2)
    cb.record_success()
    print(f"[SIEBEL CRM OK] Ticket {event['event_id']} registrado | Intención: {event['intent']} | Canal: {event['channel']} | Derivación humana: {event['human_handoff']}")
    ch.basic_ack(delivery_tag=method.delivery_tag)

def start_worker():
    print(f"Conectando Worker CRM Siebel a RabbitMQ ({RABBITMQ_HOST})...")
    while True:
        try:
            connection = pika.BlockingConnection(pika.ConnectionParameters(host=RABBITMQ_HOST))
            channel = connection.channel()
            channel.queue_declare(queue=QUEUE_NAME, durable=True)
            channel.basic_qos(prefetch_count=1)
            channel.basic_consume(queue=QUEUE_NAME, on_message_callback=process_siebel_ticket)
            print("Worker CRM Siebel escuchando eventos en 'siebel_tickets_queue'...")
            channel.start_consuming()
        except Exception as e:
            print(f"Esperando a RabbitMQ ({e})... reintentando en 5s")
            time.sleep(5)

if __name__ == "__main__":
    start_worker()
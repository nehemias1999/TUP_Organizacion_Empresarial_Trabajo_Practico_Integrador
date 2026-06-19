from utils.json_db import get_reservas, actualizar_reserva
from utils.date_utils import checkout_vencido, timestamp_ahora
from whatsapp_client import enviar_mensaje

GOOGLE_MAPS_URL = "https://maps.app.goo.gl/laspircas"


def _texto_resena(nombre):
    return (
        f"¡Hola {nombre}! 🏡 Esperamos que hayas disfrutado tu estadía en *Las Pircas Cabañas*.\n\n"
        "Tu opinión es muy valiosa para nosotros. ¿Podrías dejarnos una reseña en Google Maps? "
        "¡Te llevará solo un minuto!\n\n"
        f"👉 {GOOGLE_MAPS_URL}\n\n"
        "¡Muchas gracias y esperamos verte pronto! 🌿"
    )


def verificar_checkouts():
    """Detecta reservas cuyo checkout venció, las marca como FINALIZADA y envía mensaje de reseña."""
    db = get_reservas()
    for reserva in db["reservas"]:
        if reserva["estado"] != "CONFIRMADA":
            continue
        if reserva.get("resena_solicitada"):
            continue
        if checkout_vencido(reserva["fechas"]["checkout"]):
            historial = reserva["historial_estados"] + [
                {"estado": "FINALIZADA", "timestamp": timestamp_ahora()}
            ]
            actualizar_reserva(reserva["codigo_reserva"], {
                "estado": "FINALIZADA",
                "resena_solicitada": True,
                "historial_estados": historial,
                "timestamps": {**reserva["timestamps"], "ultima_modificacion": timestamp_ahora()},
            })
            nombre = reserva["huesped"]["nombre_completo"].split()[0]
            whatsapp = reserva["huesped"].get("whatsapp", "")
            if whatsapp:
                enviar_mensaje(whatsapp, _texto_resena(nombre))
            print(f"[SCHEDULER] Reserva {reserva['codigo_reserva']} → FINALIZADA. Reseña enviada a {whatsapp}.")


def iniciar_scheduler():
    print("[SCHEDULER] Modo local: el scheduler no se inicia en simulación.")

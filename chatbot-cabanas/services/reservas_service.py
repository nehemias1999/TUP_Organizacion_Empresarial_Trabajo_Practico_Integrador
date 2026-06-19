from datetime import datetime
from utils.json_db import (
    get_tarifas, guardar_reserva, buscar_reserva,
    actualizar_reserva, get_reservas
)
from utils.date_utils import (
    horas_hasta_checkin, dias_hasta_checkin, timestamp_ahora, fecha_a_iso, noches
)
from utils.notificaciones import (
    notificar_nueva_reserva, notificar_cancelacion,
    notificar_cambio_fechas, notificar_comprobante_recibido
)


ESTADOS_CANCELABLES = {"PENDIENTE_PAGO", "PAGO_PARCIAL", "CONFIRMADA"}


def crear_reserva(cabana, checkin, checkout, personas, huesped, modalidad_pago, precios):
    db = get_reservas()
    numero = db["ultimo_numero"] + 1
    fecha_hoy = datetime.now().strftime("%Y%m%d")
    codigo = f"RES-{fecha_hoy}-{numero:04d}"

    monto_pagado = precios["monto_sena"] if modalidad_pago == "SENA" else precios["total_final"]
    monto_pendiente = precios["total_final"] - monto_pagado

    reserva = {
        "codigo_reserva": codigo,
        "cabana_id": cabana["id"],
        "huesped": huesped,
        "fechas": {
            "checkin": fecha_a_iso(checkin),
            "checkout": fecha_a_iso(checkout),
            "noches": noches(checkin, checkout),
            "checkin_hora": "10:00",
            "checkout_hora": "10:00",
        },
        "personas": personas,
        "precios": {
            "precio_por_noche_base": precios["precio_por_noche_base"],
            "recargo_fin_semana": precios["recargo_fin_semana"],
            "recargo_temporada": precios["recargo_temporada"],
            "descuento_estadia": precios["descuento_estadia"],
            "total_final": precios["total_final"],
            "monto_sena": precios["monto_sena"],
            "saldo_pendiente": monto_pendiente,
        },
        "pago": {
            "modalidad": modalidad_pago,
            "monto_pagado": monto_pagado,
            "monto_pendiente": monto_pendiente,
            "comprobante": None,
        },
        "estado": "PENDIENTE_PAGO",
        "resena_solicitada": False,
        "historial_estados": [
            {"estado": "PENDIENTE_PAGO", "timestamp": timestamp_ahora()}
        ],
        "timestamps": {
            "creacion": timestamp_ahora(),
            "ultima_modificacion": timestamp_ahora(),
        },
        "notas_admin": "",
    }

    guardar_reserva(reserva)
    try:
        notificar_nueva_reserva(reserva)
    except Exception as e:
        print(f"[ADVERTENCIA] No se pudo enviar notificación: {e}")
    return reserva


def registrar_comprobante(codigo, texto_comprobante):
    reserva = buscar_reserva(codigo)
    if not reserva:
        return None
    actualizar_reserva(codigo, {
        "pago": {**reserva["pago"], "comprobante": texto_comprobante},
        "timestamps": {**reserva["timestamps"], "ultima_modificacion": timestamp_ahora()},
    })
    try:
        notificar_comprobante_recibido(reserva, texto_comprobante)
    except Exception as e:
        print(f"[ADVERTENCIA] No se pudo enviar notificación: {e}")
    return buscar_reserva(codigo)


def confirmar_pago(codigo):
    """Llamado cuando el dueño ejecuta CONFIRMAR <codigo>."""
    reserva = buscar_reserva(codigo)
    if not reserva:
        return None, "Reserva no encontrada."
    if reserva["estado"] not in {"PENDIENTE_PAGO", "PAGO_PARCIAL"}:
        return None, f"La reserva ya está en estado {reserva['estado']}."
    historial = reserva["historial_estados"] + [{"estado": "CONFIRMADA", "timestamp": timestamp_ahora()}]
    actualizar_reserva(codigo, {
        "estado": "CONFIRMADA",
        "historial_estados": historial,
        "timestamps": {**reserva["timestamps"], "ultima_modificacion": timestamp_ahora()},
    })
    return buscar_reserva(codigo), None


def cancelar_reserva(codigo):
    reserva = buscar_reserva(codigo)
    if not reserva:
        return None, "Reserva no encontrada."
    if reserva["estado"] not in ESTADOS_CANCELABLES:
        return None, f"La reserva no puede cancelarse (estado: {reserva['estado']})."

    horas = horas_hasta_checkin(reserva["fechas"]["checkin"])
    tarifas = get_tarifas()

    if horas < tarifas["politica_cancelacion"]["sin_reembolso_horas"]:
        return None, "No se puede cancelar con menos de 48 horas al check-in."

    dias = dias_hasta_checkin(reserva["fechas"]["checkin"])
    if dias >= tarifas["politica_cancelacion"]["sin_penalidad_dias"]:
        politica = "Reembolso total del monto pagado."
    else:
        pct = tarifas["politica_cancelacion"]["reembolso_parcial_porcentaje"] * 100
        politica = f"Reembolso del {pct:.0f}% del monto pagado."

    historial = reserva["historial_estados"] + [{"estado": "CANCELADA", "timestamp": timestamp_ahora()}]
    actualizar_reserva(codigo, {
        "estado": "CANCELADA",
        "historial_estados": historial,
        "timestamps": {**reserva["timestamps"], "ultima_modificacion": timestamp_ahora()},
    })
    try:
        notificar_cancelacion(reserva, politica)
    except Exception as e:
        print(f"[ADVERTENCIA] No se pudo enviar notificación: {e}")
    return buscar_reserva(codigo), politica


def modificar_fechas(codigo, nuevo_checkin, nuevo_checkout, nueva_cabana=None):
    reserva = buscar_reserva(codigo)
    if not reserva:
        return None, "Reserva no encontrada."
    if reserva["estado"] not in ESTADOS_CANCELABLES:
        return None, f"No se puede modificar una reserva en estado {reserva['estado']}."

    fechas_originales = dict(reserva["fechas"])
    from utils.date_utils import fecha_a_iso
    historial = reserva["historial_estados"] + [{"estado": "MODIFICADA", "timestamp": timestamp_ahora()}]

    from services.precio_service import calcular_precio
    from utils.json_db import get_cabanas
    cabanas = {c["id"]: c for c in get_cabanas()}
    cabana = cabanas[nueva_cabana or reserva["cabana_id"]]
    nuevos_precios = calcular_precio(cabana, nuevo_checkin, nuevo_checkout)

    monto_pagado = reserva["pago"]["monto_pagado"]
    nuevo_pendiente = max(0, nuevos_precios["total_final"] - monto_pagado)

    actualizar_reserva(codigo, {
        "fechas": {
            "checkin": fecha_a_iso(nuevo_checkin),
            "checkout": fecha_a_iso(nuevo_checkout),
            "noches": noches(nuevo_checkin, nuevo_checkout),
            "checkin_hora": "10:00",
            "checkout_hora": "10:00",
        },
        "precios": {**reserva["precios"], **nuevos_precios, "saldo_pendiente": nuevo_pendiente},
        "historial_estados": historial,
        "timestamps": {**reserva["timestamps"], "ultima_modificacion": timestamp_ahora()},
    })
    try:
        notificar_cambio_fechas(buscar_reserva(codigo), fechas_originales)
    except Exception as e:
        print(f"[ADVERTENCIA] No se pudo enviar notificación: {e}")
    return buscar_reserva(codigo), None

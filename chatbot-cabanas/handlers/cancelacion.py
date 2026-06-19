from utils.json_db import buscar_reserva, get_tarifas
from utils.date_utils import horas_hasta_checkin, dias_hasta_checkin, formato_fecha

ESTADOS_CANCELABLES = {"PENDIENTE_PAGO", "PAGO_PARCIAL", "CONFIRMADA"}


def solicitar_codigo():
    return (
        "❌ *Cancelar reserva*\n\n"
        "Ingresá el *código de tu reserva* (ej: RES-20260601-0001)"
    )


def procesar_codigo(texto):
    codigo = texto.strip().upper()
    reserva = buscar_reserva(codigo)
    if not reserva:
        return None, (
            f"❌ No encontré ninguna reserva con el código *{codigo}*.\n"
            "Verificá que esté bien escrito o escribí MENU para volver."
        )
    if reserva["estado"] not in ESTADOS_CANCELABLES:
        return None, (
            f"❌ La reserva *{codigo}* está en estado *{reserva['estado']}* "
            "y no puede cancelarse.\nEscribí MENU para volver."
        )

    horas = horas_hasta_checkin(reserva["fechas"]["checkin"])
    tarifas = get_tarifas()

    if horas < tarifas["politica_cancelacion"]["sin_reembolso_horas"]:
        ci = formato_fecha(reserva["fechas"]["checkin"])
        return None, (
            f"⛔ No es posible cancelar la reserva *{codigo}*.\n\n"
            f"El check-in es el *{ci}* y quedan menos de 48 horas.\n"
            "Según nuestra política, no se aceptan cancelaciones en ese período.\n\n"
            "¿Querés modificar las fechas en cambio? Escribí MENU y elegí la opción 3."
        )

    return reserva, None


def texto_confirmacion_cancelacion(reserva):
    tarifas = get_tarifas()
    ci = formato_fecha(reserva["fechas"]["checkin"])
    co = formato_fecha(reserva["fechas"]["checkout"])
    dias = dias_hasta_checkin(reserva["fechas"]["checkin"])
    monto_pagado = reserva["pago"]["monto_pagado"]

    if dias >= tarifas["politica_cancelacion"]["sin_penalidad_dias"]:
        reembolso_texto = f"*Reembolso total* de ${monto_pagado:,}"
    else:
        pct = tarifas["politica_cancelacion"]["reembolso_parcial_porcentaje"]
        monto_reembolso = round(monto_pagado * pct)
        reembolso_texto = f"Reembolso del 50%: *${monto_reembolso:,}*"

    return (
        f"⚠️ *Confirmar cancelación*\n\n"
        f"Reserva: *{reserva['codigo_reserva']}*\n"
        f"Cabaña: {reserva['cabana_id']}\n"
        f"Fechas: {ci} → {co}\n"
        f"Monto pagado: ${monto_pagado:,}\n\n"
        f"💰 Política de reembolso: {reembolso_texto}\n\n"
        "¿Confirmás la cancelación? Respondé *SI* o *NO*."
    )


def texto_cancelacion_exitosa(reserva, politica):
    return (
        f"✅ Tu reserva *{reserva['codigo_reserva']}* fue cancelada.\n\n"
        f"📋 {politica}\n\n"
        "El reembolso será procesado en los próximos días hábiles.\n"
        "¡Esperamos verte en otra oportunidad! 🏡\n\n"
        "_Escribí MENU para volver al inicio._"
    )

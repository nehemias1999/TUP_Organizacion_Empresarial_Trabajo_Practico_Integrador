def _enviar_mail(asunto, cuerpo):
    print("\n" + "="*60)
    print("[SIMULADO - EMAIL AL DUEÑO]")
    print(f"Asunto: {asunto}")
    print("-"*60)
    print(cuerpo)
    print("="*60 + "\n")


def notificar_nueva_reserva(reserva):
    cab = reserva["cabana_id"]
    h = reserva["huesped"]
    f = reserva["fechas"]
    p = reserva["precios"]
    pago = reserva["pago"]
    asunto = f"Nueva reserva {reserva['codigo_reserva']} - {h['nombre_completo']}"
    cuerpo = f"""
Nueva reserva recibida en Las Pircas Cabañas.

Código: {reserva['codigo_reserva']}
Huésped: {h['nombre_completo']} | DNI: {h['dni']} | Tel: {h['telefono']}
Cabaña: {cab}
Check-in: {f['checkin']} a las 10:00 hs
Check-out: {f['checkout']} a las 10:00 hs
Noches: {f['noches']} | Personas: {reserva['personas']}

Total: ${p['total_final']:,.0f}
Modalidad de pago: {pago['modalidad']}
Monto pagado (seña): ${pago['monto_pagado']:,.0f}
Saldo pendiente al check-in: ${pago['monto_pendiente']:,.0f}

Verificá la transferencia y confirmá con el comando:
CONFIRMAR {reserva['codigo_reserva']}
"""
    _enviar_mail(asunto, cuerpo)


def notificar_cancelacion(reserva, politica_reembolso):
    h = reserva["huesped"]
    f = reserva["fechas"]
    asunto = f"Reserva CANCELADA {reserva['codigo_reserva']} - {h['nombre_completo']}"
    cuerpo = f"""
Se canceló una reserva en Las Pircas Cabañas.

Código: {reserva['codigo_reserva']}
Huésped: {h['nombre_completo']} | Tel: {h['telefono']}
Cabaña: {reserva['cabana_id']} — DISPONIBLE NUEVAMENTE
Check-in cancelado: {f['checkin']} | Check-out: {f['checkout']}

Política de reembolso aplicada: {politica_reembolso}
"""
    _enviar_mail(asunto, cuerpo)


def notificar_cambio_fechas(reserva, fechas_originales):
    h = reserva["huesped"]
    f = reserva["fechas"]
    asunto = f"Cambio de fechas {reserva['codigo_reserva']} - {h['nombre_completo']}"
    cuerpo = f"""
Se modificaron las fechas de una reserva en Las Pircas Cabañas.

Código: {reserva['codigo_reserva']}
Huésped: {h['nombre_completo']} | Tel: {h['telefono']}
Cabaña: {reserva['cabana_id']}

Fechas originales: {fechas_originales['checkin']} → {fechas_originales['checkout']}
Nuevas fechas: {f['checkin']} → {f['checkout']}
"""
    _enviar_mail(asunto, cuerpo)


def notificar_comprobante_recibido(reserva, texto_comprobante):
    h = reserva["huesped"]
    asunto = f"Comprobante de pago recibido - {reserva['codigo_reserva']}"
    cuerpo = f"""
El cliente envió un comprobante de pago.

Código: {reserva['codigo_reserva']}
Huésped: {h['nombre_completo']} | Tel: {h['telefono']}
Monto esperado: ${reserva['precios']['monto_sena']:,.0f}

Comprobante: {texto_comprobante}

Verificá la transferencia y confirmá con:
CONFIRMAR {reserva['codigo_reserva']}
"""
    _enviar_mail(asunto, cuerpo)

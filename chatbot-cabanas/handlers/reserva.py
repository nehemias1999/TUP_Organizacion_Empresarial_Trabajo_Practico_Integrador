from utils.validators import validar_nombre, validar_dni, validar_telefono
from services.reservas_service import crear_reserva, registrar_comprobante
from utils.date_utils import formato_fecha
from utils.json_db import get_tarifas


def solicitar_seleccion_cabana(disponibles):
    lineas = ["🏕️ *¿Qué cabaña querés reservar?*\n"]
    for i, item in enumerate(disponibles, 1):
        c = item["cabana"]
        p = item["precios"]
        lineas.append(f"{i}. Cabaña *{c['nombre']}* — Total: ${p['total_final']:,}")
    lineas.append("\nRespondé con el número.")
    return "\n".join(lineas)


def procesar_seleccion_cabana(texto, disponibles):
    try:
        idx = int(texto.strip()) - 1
        if 0 <= idx < len(disponibles):
            return disponibles[idx], None
    except ValueError:
        pass
    return None, f"Opción inválida. Ingresá un número del 1 al {len(disponibles)}."


def solicitar_nombre():
    return "👤 ¿Cuál es tu *nombre y apellido completo*?"


def procesar_nombre(texto, sesion):
    nombre, error = validar_nombre(texto)
    if error:
        return None, f"❌ {error}\n\nPor favor ingresá una opción correcta.", False
    return nombre, None, False


def solicitar_dni():
    return "🪪 ¿Cuál es tu *número de DNI*? (sin puntos ni espacios)"


def procesar_dni(texto, sesion):
    dni, error = validar_dni(texto)
    if error:
        return None, f"❌ {error}\n\nPor favor ingresá una opción correcta.", False
    return dni, None, False


def solicitar_telefono():
    return "📱 ¿Cuál es tu *número de teléfono*? (con código de área, ej: 3512345678)"


def procesar_telefono(texto, sesion):
    tel, error = validar_telefono(texto)
    if error:
        return None, f"❌ {error}\n\nPor favor ingresá una opción correcta.", False
    return tel, None, False


def solicitar_modalidad_pago(precios):
    total = precios["total_final"]
    sena = precios["monto_sena"]
    return (
        f"💳 *Elegí tu modalidad de pago:*\n\n"
        f"1️⃣ *Pago total* — ${total:,} ahora por transferencia\n"
        f"2️⃣ *Seña + saldo* — ${sena:,} ahora y ${total - sena:,} al llegar\n\n"
        "Respondé 1 o 2."
    )


def procesar_modalidad_pago(texto):
    opcion = texto.strip()
    if opcion == "1":
        return "TOTAL", None
    if opcion == "2":
        return "SENA", None
    return None, "Opción inválida. Respondé *1* para pago total o *2* para seña."


def texto_resumen_reserva(cabana, checkin, checkout, personas, nombre, dni, tel, modalidad, precios):
    ci = formato_fecha(checkin.strftime("%Y-%m-%d"))
    co = formato_fecha(checkout.strftime("%Y-%m-%d"))
    noches = (checkout - checkin).days
    monto = precios["total_final"] if modalidad == "TOTAL" else precios["monto_sena"]
    tipo_pago = "Pago total" if modalidad == "TOTAL" else "Seña (50%)"
    return (
        f"📋 *Resumen de tu reserva:*\n\n"
        f"🏕️ Cabaña: *{cabana['nombre']}*\n"
        f"📅 Check-in: *{ci}* a las 10:00 hs\n"
        f"📅 Check-out: *{co}* a las 10:00 hs\n"
        f"🌙 Noches: {noches} | 👥 Personas: {personas}\n"
        f"👤 Titular: {nombre} | DNI: {dni} | Tel: {tel}\n"
        f"💰 Total estadía: ${precios['total_final']:,}\n"
        f"💳 {tipo_pago}: *${monto:,}*\n\n"
        "¿Confirmás la reserva? Respondé *SI* o *NO*."
    )


def texto_datos_pago(reserva):
    tarifas = get_tarifas()
    monto = reserva["pago"]["monto_pagado"]
    return (
        f"✅ ¡Reserva registrada!\n\n"
        f"📌 Código de reserva: *{reserva['codigo_reserva']}*\n\n"
        f"Para confirmar tu reserva realizá la transferencia:\n"
        f"💰 Monto: *${monto:,}*\n"
        f"🏦 CBU: `{tarifas['pago']['cbu']}`\n"
        f"🔑 Alias: `{tarifas['pago']['alias']}`\n\n"
        "Una vez realizada la transferencia, *enviá el comprobante* "
        "en este chat (imagen o número de operación).\n\n"
        "_El administrador verificará el pago y recibirás la confirmación._"
    )


def texto_pago_confirmado(reserva, telefono_dueno):
    return (
        f"🎉 *¡Tu pago fue aprobado!*\n\n"
        f"Tu reserva *{reserva['codigo_reserva']}* está confirmada.\n\n"
        f"📞 Si necesitás coordinar algo con el dueño podés contactarlo directamente:\n"
        f"*{telefono_dueno}*\n\n"
        f"¡Te esperamos! 🏡"
    )

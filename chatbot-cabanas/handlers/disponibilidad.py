from utils.validators import validar_fecha, validar_checkout, validar_personas, validar_anticipacion
from services.disponibilidad_service import consultar_disponibilidad
from utils.date_utils import formato_fecha


def solicitar_fecha_checkin():
    return (
        "📅 *Consulta de disponibilidad*\n\n"
        "¿Cuál es la fecha de *llegada* (check-in)?\n"
        "Formato: DD/MM/AAAA  (ej: 25/07/2026)"
    )


def procesar_fecha_checkin(texto, sesion):
    fecha, error = validar_fecha(texto)
    if error:
        return None, f"❌ {error}\n\nPor favor ingresá una opción correcta.", False

    ok, err_anticip = validar_anticipacion(fecha)
    if not ok:
        return None, f"❌ {err_anticip}\n\nPor favor ingresá una opción correcta.", False

    sesion["checkin"] = fecha.isoformat()
    return fecha, None, False


def solicitar_fecha_checkout(checkin):
    return (
        f"✅ Check-in: *{formato_fecha(checkin.strftime('%Y-%m-%d'))}*\n\n"
        "¿Cuál es la fecha de *salida* (check-out)?\n"
        "Formato: DD/MM/AAAA"
    )


def procesar_fecha_checkout(texto, checkin, sesion):
    fecha, error = validar_checkout(checkin, texto)
    if error:
        return None, f"❌ {error}\n\nPor favor ingresá una opción correcta.", False

    sesion["checkout"] = fecha.isoformat()
    return fecha, None, False


def solicitar_personas():
    return "👥 ¿Cuántas personas se hospedarán?"


def procesar_personas(texto, sesion):
    personas, error = validar_personas(texto)
    if error:
        return None, f"❌ {error}\n\nPor favor ingresá una opción correcta.", False

    sesion["personas"] = personas
    return personas, None, False


def mostrar_disponibilidad(checkin, checkout, personas):
    disponibles, reservadas = consultar_disponibilidad(checkin, checkout, personas)
    ci_str = formato_fecha(checkin.strftime("%Y-%m-%d"))
    co_str = formato_fecha(checkout.strftime("%Y-%m-%d"))
    noches = (checkout - checkin).days

    def _lineas_reservadas(reservadas):
        if not reservadas:
            return []
        lineas = ["\n⛔ *Ya reservadas para esas fechas:*"]
        for c in reservadas:
            lineas.append(f"   ❌ Cabaña *{c['nombre']}* (hasta {c['capacidad_max']} personas) — ocupada")
        return lineas

    if not disponibles:
        lineas = [
            f"😔 No hay cabañas disponibles para *{personas} personas* "
            f"del *{ci_str}* al *{co_str}*."
        ]
        lineas += _lineas_reservadas(reservadas)
        lineas.append("\nEscribí *FECHAS* para buscar otras fechas o *MENU* para volver al inicio.")
        return None, "\n".join(lineas)

    lineas = [
        f"🏡 Cabañas disponibles para *{personas} personas*\n"
        f"📅 {ci_str} → {co_str} ({noches} noche{'s' if noches > 1 else ''})\n"
    ]
    for i, item in enumerate(disponibles, 1):
        c = item["cabana"]
        p = item["precios"]
        lineas.append(
            f"{i}. *Cabaña {c['nombre']}* (hasta {c['capacidad_max']} personas)\n"
            f"   💰 Total estimado: *${p['total_final']:,}*\n"
            f"   💳 Seña (50%): ${p['monto_sena']:,} | Saldo al llegar: ${p['saldo_pendiente']:,}\n"
        )

    lineas += _lineas_reservadas(reservadas)
    lineas.append("\n¿Querés hacer una reserva? Escribí *RESERVAR*, *FECHAS* para buscar otras fechas, o *MENU* para volver.")
    return disponibles, "\n".join(lineas)

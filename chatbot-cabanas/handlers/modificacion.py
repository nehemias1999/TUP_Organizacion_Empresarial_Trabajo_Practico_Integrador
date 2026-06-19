from utils.validators import validar_fecha, validar_checkout, validar_anticipacion
from services.disponibilidad_service import consultar_disponibilidad
from services.reservas_service import modificar_fechas
from utils.date_utils import formato_fecha
from utils.json_db import buscar_reserva

ESTADOS_MODIFICABLES = {"PENDIENTE_PAGO", "PAGO_PARCIAL", "CONFIRMADA"}


def solicitar_codigo():
    return (
        "✏️ *Modificar reserva*\n\n"
        "Ingresá el *código de tu reserva* (ej: RES-20260601-0001)\n\n"
        "_Si no lo recordás, podés buscarlo en la confirmación que te enviamos._"
    )


def procesar_codigo(texto):
    codigo = texto.strip().upper()
    reserva = buscar_reserva(codigo)
    if not reserva:
        return None, (
            f"❌ No encontré ninguna reserva con el código *{codigo}*.\n"
            "Verificá que esté bien escrito o escribí MENU para volver."
        )
    if reserva["estado"] not in ESTADOS_MODIFICABLES:
        return None, (
            f"❌ La reserva *{codigo}* está en estado *{reserva['estado']}* "
            "y no puede modificarse.\nEscribí MENU para volver."
        )
    return reserva, None


def solicitar_nueva_checkin(reserva):
    ci = formato_fecha(reserva["fechas"]["checkin"])
    co = formato_fecha(reserva["fechas"]["checkout"])
    return (
        f"📅 Reserva *{reserva['codigo_reserva']}*\n"
        f"Fechas actuales: {ci} → {co}\n\n"
        "¿Cuál será la nueva fecha de *llegada* (check-in)?\n"
        "Formato: DD/MM/AAAA"
    )


def procesar_nueva_checkin(texto, sesion):
    fecha, error = validar_fecha(texto)
    if error:
        return None, f"❌ {error}\n\nPor favor ingresá una opción correcta.", False

    ok, err_anticip = validar_anticipacion(fecha)
    if not ok:
        return None, f"❌ {err_anticip}\n\nPor favor ingresá una opción correcta.", False

    return fecha, None, False


def solicitar_nueva_checkout():
    return "📅 ¿Cuál será la nueva fecha de *salida* (check-out)?\nFormato: DD/MM/AAAA"


def procesar_nueva_checkout(texto, nuevo_checkin, sesion):
    fecha, error = validar_checkout(nuevo_checkin, texto)
    if error:
        return None, f"❌ {error}\n\nPor favor ingresá una opción correcta.", False

    return fecha, None, False


def verificar_disponibilidad_cambio(reserva, nuevo_checkin, nuevo_checkout):
    from utils.json_db import get_cabanas
    cabanas = {c["id"]: c for c in get_cabanas()}
    cabana = cabanas[reserva["cabana_id"]]

    from services.disponibilidad_service import _cabana_disponible
    from utils.json_db import actualizar_reserva
    # Temporalmente marcamos la reserva como CANCELADA para no bloquear su propia disponibilidad
    estado_original = reserva["estado"]
    actualizar_reserva(reserva["codigo_reserva"], {"estado": "_VERIFICANDO"})
    disponible = _cabana_disponible(reserva["cabana_id"], nuevo_checkin, nuevo_checkout)
    actualizar_reserva(reserva["codigo_reserva"], {"estado": estado_original})

    if not disponible:
        return False, (
            f"😔 La cabaña *{cabana['nombre']}* no está disponible en las nuevas fechas.\n"
            "¿Querés consultar otras cabañas? Escribí MENU para ver opciones."
        )
    return True, None


def texto_confirmacion_cambio(reserva, nuevo_checkin, nuevo_checkout, nuevos_precios):
    ci_orig = formato_fecha(reserva["fechas"]["checkin"])
    co_orig = formato_fecha(reserva["fechas"]["checkout"])
    ci_nuevo = formato_fecha(nuevo_checkin.strftime("%Y-%m-%d"))
    co_nuevo = formato_fecha(nuevo_checkout.strftime("%Y-%m-%d"))
    noches = (nuevo_checkout - nuevo_checkin).days
    return (
        f"📋 *Confirmación de cambio*\n\n"
        f"Reserva: *{reserva['codigo_reserva']}*\n"
        f"Fechas originales: {ci_orig} → {co_orig}\n"
        f"Nuevas fechas: *{ci_nuevo} → {co_nuevo}* ({noches} noche{'s' if noches > 1 else ''})\n"
        f"Nuevo total: *${nuevos_precios['total_final']:,}*\n\n"
        "¿Confirmás el cambio? Respondé *SI* o *NO*."
    )

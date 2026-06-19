import os
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from dotenv import load_dotenv

load_dotenv()

from states import (
    MENU_PRINCIPAL, CONSULTA_FECHA_CHECKIN, CONSULTA_FECHA_CHECKOUT,
    CONSULTA_PERSONAS, MOSTRANDO_DISPONIBILIDAD,
    SELECCION_CABANA, CAPTURA_NOMBRE, CAPTURA_DNI, CAPTURA_TELEFONO,
    SELECCION_MODALIDAD_PAGO, CONFIRMACION_RESERVA, ESPERA_COMPROBANTE, COMPROBANTE_RECIBIDO,
    MODIFICACION_PEDIR_CODIGO, MODIFICACION_NUEVA_CHECKIN,
    MODIFICACION_NUEVA_CHECKOUT, MODIFICACION_CONFIRMACION,
    CANCELACION_PEDIR_CODIGO, CANCELACION_CONFIRMACION,
    PALABRAS_MENU
)
from utils.json_db import get_sesion, guardar_sesion, eliminar_sesion
from utils.date_utils import timestamp_ahora, fecha_a_iso
from handlers import menu as h_menu
from handlers import disponibilidad as h_disp
from handlers import reserva as h_res
from handlers import modificacion as h_mod
from handlers import cancelacion as h_can
from services.reservas_service import (
    crear_reserva, registrar_comprobante, confirmar_pago,
    cancelar_reserva, modificar_fechas
)
from services.precio_service import calcular_precio
from utils.json_db import get_cabanas

TIMEOUT_MINUTOS = 30
TELEFONO_DUENO = os.getenv("TELEFONO_DUENO", "+54 9 351 555-0000")
ADMIN_WHATSAPP = os.getenv("ADMIN_WHATSAPP", "")

app = Flask(__name__)


def responder(mensaje):
    r = MessagingResponse()
    r.message(mensaje)
    return str(r)


def nueva_sesion(estado):
    return {"estado": estado, "contexto": {}, "ultima_actividad": timestamp_ahora()}


def volver_menu(chat_id):
    eliminar_sesion(chat_id)
    return responder(h_menu.texto_bienvenida())


@app.route("/whatsapp", methods=["POST"])
def webhook():
    from datetime import datetime, timedelta

    incoming = request.form.get("Body", "").strip()
    chat_id = request.form.get("From", "")
    media_url = request.form.get("MediaUrl0", "")

    sesion = get_sesion(chat_id) or nueva_sesion(MENU_PRINCIPAL)

    # Timeout de sesión
    ultima = datetime.strptime(sesion.get("ultima_actividad", timestamp_ahora()), "%Y-%m-%dT%H:%M:%S")
    if datetime.now() - ultima > timedelta(minutes=TIMEOUT_MINUTOS):
        guardar_sesion(chat_id, nueva_sesion(MENU_PRINCIPAL))
        return responder(
            "⏰ Tu sesión expiró por inactividad.\n\n" + h_menu.texto_bienvenida()
        )

    sesion["ultima_actividad"] = timestamp_ahora()
    estado = sesion["estado"]
    ctx = sesion["contexto"]

    # Comando de admin: CONFIRMAR <codigo>
    if chat_id == ADMIN_WHATSAPP and incoming.upper().startswith("CONFIRMAR "):
        codigo = incoming.split(" ", 1)[1].strip().upper()
        reserva, error = confirmar_pago(codigo)
        if error:
            guardar_sesion(chat_id, sesion)
            return responder(f"❌ {error}")
        from whatsapp_client import enviar_mensaje
        enviar_mensaje(reserva["huesped"]["whatsapp"], h_res.texto_pago_confirmado(reserva, TELEFONO_DUENO))
        guardar_sesion(chat_id, sesion)
        return responder(f"✅ Reserva {codigo} confirmada. Se notificó al cliente.")

    # Palabras clave globales → menú
    if incoming.lower() in PALABRAS_MENU:
        return volver_menu(chat_id)

    # ── MENU PRINCIPAL ─────────────────────────────────────────
    if estado == MENU_PRINCIPAL:
        if incoming == "1":
            sesion["estado"] = CONSULTA_FECHA_CHECKIN
            guardar_sesion(chat_id, sesion)
            return responder(h_disp.solicitar_fecha_checkin())

        elif incoming == "2":
            sesion["estado"] = MODIFICACION_PEDIR_CODIGO
            guardar_sesion(chat_id, sesion)
            return responder(h_mod.solicitar_codigo())

        elif incoming == "3":
            sesion["estado"] = CANCELACION_PEDIR_CODIGO
            guardar_sesion(chat_id, sesion)
            return responder(h_can.solicitar_codigo())

        elif incoming == "4":
            guardar_sesion(chat_id, sesion)
            return responder(h_menu.texto_info_cabanas())

        elif incoming == "5":
            guardar_sesion(chat_id, sesion)
            return responder(h_menu.texto_instagram())

        else:
            guardar_sesion(chat_id, sesion)
            return responder(h_menu.texto_opcion_invalida())

    # ── CONSULTA / RESERVA: FECHA CHECKIN ──────────────────────
    elif estado == CONSULTA_FECHA_CHECKIN:
        fecha, error, limite = h_disp.procesar_fecha_checkin(incoming, ctx)
        if error:
            guardar_sesion(chat_id, sesion)
            if limite:
                return volver_menu(chat_id)
            return responder(error)
        sesion["estado"] = CONSULTA_FECHA_CHECKOUT
        guardar_sesion(chat_id, sesion)
        return responder(h_disp.solicitar_fecha_checkout(fecha))

    # ── CONSULTA / RESERVA: FECHA CHECKOUT ─────────────────────
    elif estado == CONSULTA_FECHA_CHECKOUT:
        from datetime import datetime
        checkin = datetime.strptime(fecha_a_iso(ctx["checkin"]) if not isinstance(ctx["checkin"], str) else ctx["checkin"], "%Y-%m-%d").date() if isinstance(ctx.get("checkin"), str) else ctx["checkin"]
        fecha, error, limite = h_disp.procesar_fecha_checkout(incoming, checkin, ctx)
        if error:
            guardar_sesion(chat_id, sesion)
            if limite:
                return volver_menu(chat_id)
            return responder(error)
        sesion["estado"] = CONSULTA_PERSONAS
        guardar_sesion(chat_id, sesion)
        return responder(h_disp.solicitar_personas())

    # ── CONSULTA / RESERVA: PERSONAS ───────────────────────────
    elif estado == CONSULTA_PERSONAS:
        personas, error, limite = h_disp.procesar_personas(incoming, ctx)
        if error:
            guardar_sesion(chat_id, sesion)
            if limite:
                return volver_menu(chat_id)
            return responder(error)
        from datetime import datetime
        checkin = ctx["checkin"] if not isinstance(ctx["checkin"], str) else datetime.strptime(ctx["checkin"], "%Y-%m-%d").date()
        checkout = ctx["checkout"] if not isinstance(ctx["checkout"], str) else datetime.strptime(ctx["checkout"], "%Y-%m-%d").date()
        disponibles, texto = h_disp.mostrar_disponibilidad(checkin, checkout, personas)
        ctx["disponibles_ids"] = [d["cabana"]["id"] for d in disponibles] if disponibles else []
        ctx["_disponibles"] = [{"cabana": d["cabana"], "precios": d["precios"]} for d in disponibles] if disponibles else []

        if ctx.get("flujo") == "reserva" and disponibles:
            sesion["estado"] = SELECCION_CABANA
            guardar_sesion(chat_id, sesion)
            return responder(texto + "\n\n" + h_res.solicitar_seleccion_cabana(disponibles))

        sesion["estado"] = MOSTRANDO_DISPONIBILIDAD
        guardar_sesion(chat_id, sesion)
        return responder(texto)

    # ── DISPONIBILIDAD: MOSTRADO ────────────────────────────────
    elif estado == MOSTRANDO_DISPONIBILIDAD:
        if incoming.upper() == "RESERVAR":
            sesion["estado"] = SELECCION_CABANA
            sesion["contexto"]["flujo"] = "reserva"
            guardar_sesion(chat_id, sesion)
            disponibles = ctx.get("_disponibles", [])
            return responder(h_res.solicitar_seleccion_cabana(disponibles))
        if incoming.upper() == "FECHAS":
            for key in ("checkin", "checkout", "personas", "_disponibles", "disponibles_ids"):
                ctx.pop(key, None)
            sesion["estado"] = CONSULTA_FECHA_CHECKIN
            guardar_sesion(chat_id, sesion)
            return responder(h_disp.solicitar_fecha_checkin())
        guardar_sesion(chat_id, sesion)
        return responder("❌ Opción inválida.\n\nEscribí *RESERVAR* para hacer una reserva, *FECHAS* para buscar otras fechas, o *MENU* para volver al inicio.")

    # ── RESERVA: SELECCION CABAÑA ───────────────────────────────
    elif estado == SELECCION_CABANA:
        disponibles = ctx.get("_disponibles", [])
        seleccion, error = h_res.procesar_seleccion_cabana(incoming, disponibles)
        if error:
            guardar_sesion(chat_id, sesion)
            return responder(f"❌ {error}\n\n" + h_res.solicitar_seleccion_cabana(disponibles))
        ctx["cabana_seleccionada"] = seleccion["cabana"]
        ctx["precios_seleccionados"] = seleccion["precios"]
        sesion["estado"] = CAPTURA_NOMBRE
        guardar_sesion(chat_id, sesion)
        return responder(h_res.solicitar_nombre())

    # ── RESERVA: NOMBRE ─────────────────────────────────────────
    elif estado == CAPTURA_NOMBRE:
        nombre, error, limite = h_res.procesar_nombre(incoming, ctx)
        if error:
            guardar_sesion(chat_id, sesion)
            if limite:
                return volver_menu(chat_id)
            return responder(error)
        ctx["nombre"] = nombre
        sesion["estado"] = CAPTURA_DNI
        guardar_sesion(chat_id, sesion)
        return responder(h_res.solicitar_dni())

    # ── RESERVA: DNI ────────────────────────────────────────────
    elif estado == CAPTURA_DNI:
        dni, error, limite = h_res.procesar_dni(incoming, ctx)
        if error:
            guardar_sesion(chat_id, sesion)
            if limite:
                return volver_menu(chat_id)
            return responder(error)
        ctx["dni"] = dni
        sesion["estado"] = CAPTURA_TELEFONO
        guardar_sesion(chat_id, sesion)
        return responder(h_res.solicitar_telefono())

    # ── RESERVA: TELEFONO ───────────────────────────────────────
    elif estado == CAPTURA_TELEFONO:
        tel, error, limite = h_res.procesar_telefono(incoming, ctx)
        if error:
            guardar_sesion(chat_id, sesion)
            if limite:
                return volver_menu(chat_id)
            return responder(error)
        ctx["telefono"] = tel
        sesion["estado"] = SELECCION_MODALIDAD_PAGO
        guardar_sesion(chat_id, sesion)
        return responder(h_res.solicitar_modalidad_pago(ctx["precios_seleccionados"]))

    # ── RESERVA: MODALIDAD PAGO ─────────────────────────────────
    elif estado == SELECCION_MODALIDAD_PAGO:
        modalidad, error = h_res.procesar_modalidad_pago(incoming)
        if error:
            guardar_sesion(chat_id, sesion)
            return responder(f"❌ {error}\n\n" + h_res.solicitar_modalidad_pago(ctx["precios_seleccionados"]))
        ctx["modalidad_pago"] = modalidad
        sesion["estado"] = CONFIRMACION_RESERVA
        guardar_sesion(chat_id, sesion)
        from datetime import datetime
        ci = ctx["checkin"] if not isinstance(ctx["checkin"], str) else datetime.strptime(ctx["checkin"], "%Y-%m-%d").date()
        co = ctx["checkout"] if not isinstance(ctx["checkout"], str) else datetime.strptime(ctx["checkout"], "%Y-%m-%d").date()
        return responder(h_res.texto_resumen_reserva(
            ctx["cabana_seleccionada"], ci, co, ctx["personas"],
            ctx["nombre"], ctx["dni"], ctx["telefono"],
            modalidad, ctx["precios_seleccionados"]
        ))

    # ── RESERVA: CONFIRMACION ───────────────────────────────────
    elif estado == CONFIRMACION_RESERVA:
        if incoming.upper() == "SI":
            from datetime import datetime
            ci = ctx["checkin"] if not isinstance(ctx["checkin"], str) else datetime.strptime(ctx["checkin"], "%Y-%m-%d").date()
            co = ctx["checkout"] if not isinstance(ctx["checkout"], str) else datetime.strptime(ctx["checkout"], "%Y-%m-%d").date()
            huesped = {
                "nombre_completo": ctx["nombre"],
                "dni": ctx["dni"],
                "telefono": ctx["telefono"],
                "whatsapp": chat_id,
            }
            reserva = crear_reserva(
                ctx["cabana_seleccionada"], ci, co,
                ctx["personas"], huesped,
                ctx["modalidad_pago"], ctx["precios_seleccionados"]
            )
            ctx["codigo_reserva_activo"] = reserva["codigo_reserva"]
            sesion["estado"] = ESPERA_COMPROBANTE
            guardar_sesion(chat_id, sesion)
            return responder(h_res.texto_datos_pago(reserva))
        elif incoming.upper() in ("NO", "N"):
            return volver_menu(chat_id)
        else:
            guardar_sesion(chat_id, sesion)
            return responder("❌ Por favor respondé *SI* para confirmar la reserva o *NO* para cancelar.")

    # ── RESERVA: ESPERA COMPROBANTE ─────────────────────────────
    elif estado == ESPERA_COMPROBANTE:
        codigo = ctx.get("codigo_reserva_activo", "")
        comprobante = media_url if media_url else incoming
        registrar_comprobante(codigo, comprobante)
        sesion["estado"] = COMPROBANTE_RECIBIDO
        guardar_sesion(chat_id, sesion)
        return responder(
            "✅ *¡Comprobante recibido!*\n\n"
            "Le avisamos al administrador. Recibirás la confirmación pronto.\n\n"
            "¡Gracias por elegir *Las Pircas Cabañas*! 🏡\n\n"
            "¿Qué querés hacer ahora?\n"
            "  *1* — Volver al menú principal\n"
            "  *2* — Terminar la conversación"
        )

    elif estado == COMPROBANTE_RECIBIDO:
        if incoming.strip() == "2":
            eliminar_sesion(chat_id)
            return responder("¡Hasta pronto! Si necesitás algo más, escribinos cuando quieras. 👋")
        return volver_menu(chat_id)

    # ── MODIFICACION: PEDIR CODIGO ──────────────────────────────
    elif estado == MODIFICACION_PEDIR_CODIGO:
        reserva, error = h_mod.procesar_codigo(incoming)
        if error:
            guardar_sesion(chat_id, sesion)
            return responder(error + "\n\n" + h_mod.solicitar_codigo())
        ctx["reserva_a_modificar"] = reserva
        sesion["estado"] = MODIFICACION_NUEVA_CHECKIN
        guardar_sesion(chat_id, sesion)
        return responder(h_mod.solicitar_nueva_checkin(reserva))

    # ── MODIFICACION: NUEVA CHECKIN ─────────────────────────────
    elif estado == MODIFICACION_NUEVA_CHECKIN:
        fecha, error, limite = h_mod.procesar_nueva_checkin(incoming, ctx)
        if error:
            guardar_sesion(chat_id, sesion)
            if limite:
                return volver_menu(chat_id)
            return responder(error)
        ctx["nuevo_checkin"] = fecha
        sesion["estado"] = MODIFICACION_NUEVA_CHECKOUT
        guardar_sesion(chat_id, sesion)
        return responder(h_mod.solicitar_nueva_checkout())

    # ── MODIFICACION: NUEVA CHECKOUT ────────────────────────────
    elif estado == MODIFICACION_NUEVA_CHECKOUT:
        from datetime import datetime
        ci = ctx["nuevo_checkin"] if not isinstance(ctx["nuevo_checkin"], str) else datetime.strptime(ctx["nuevo_checkin"], "%Y-%m-%d").date()
        fecha, error, limite = h_mod.procesar_nueva_checkout(incoming, ci, ctx)
        if error:
            guardar_sesion(chat_id, sesion)
            if limite:
                return volver_menu(chat_id)
            return responder(error)
        ctx["nuevo_checkout"] = fecha

        disponible, error_disp = h_mod.verificar_disponibilidad_cambio(
            ctx["reserva_a_modificar"], ci, fecha
        )
        if not disponible:
            guardar_sesion(chat_id, sesion)
            return responder(f"❌ {error_disp}\n\n" + h_mod.solicitar_nueva_checkout())

        from services.precio_service import calcular_precio
        cabanas = {c["id"]: c for c in get_cabanas()}
        cabana = cabanas[ctx["reserva_a_modificar"]["cabana_id"]]
        nuevos_precios = calcular_precio(cabana, ci, fecha)
        ctx["nuevos_precios"] = nuevos_precios
        sesion["estado"] = MODIFICACION_CONFIRMACION
        guardar_sesion(chat_id, sesion)
        return responder(h_mod.texto_confirmacion_cambio(ctx["reserva_a_modificar"], ci, fecha, nuevos_precios))

    # ── MODIFICACION: CONFIRMACION ──────────────────────────────
    elif estado == MODIFICACION_CONFIRMACION:
        if incoming.upper() == "SI":
            from datetime import datetime
            ci = ctx["nuevo_checkin"] if not isinstance(ctx["nuevo_checkin"], str) else datetime.strptime(ctx["nuevo_checkin"], "%Y-%m-%d").date()
            co = ctx["nuevo_checkout"] if not isinstance(ctx["nuevo_checkout"], str) else datetime.strptime(ctx["nuevo_checkout"], "%Y-%m-%d").date()
            reserva_mod, error = modificar_fechas(ctx["reserva_a_modificar"]["codigo_reserva"], ci, co)
            if error:
                guardar_sesion(chat_id, sesion)
                return responder(f"❌ {error}")
            sesion["estado"] = MENU_PRINCIPAL
            guardar_sesion(chat_id, sesion)
            return responder(
                f"✅ Fechas actualizadas para la reserva *{reserva_mod['codigo_reserva']}*.\n"
                f"Nueva estadía: {h_mod.formato_fecha(ci.strftime('%Y-%m-%d'))} → "
                f"{h_mod.formato_fecha(co.strftime('%Y-%m-%d'))}\n\n"
                "_Escribí MENU para volver al inicio._"
            )
        elif incoming.upper() in ("NO", "N"):
            return volver_menu(chat_id)
        else:
            guardar_sesion(chat_id, sesion)
            return responder("❌ Por favor respondé *SI* para confirmar el cambio o *NO* para cancelar.")

    # ── CANCELACION: PEDIR CODIGO ───────────────────────────────
    elif estado == CANCELACION_PEDIR_CODIGO:
        reserva, error = h_can.procesar_codigo(incoming)
        if error:
            guardar_sesion(chat_id, sesion)
            return responder(error + "\n\n" + h_can.solicitar_codigo())
        ctx["reserva_a_cancelar"] = reserva
        sesion["estado"] = CANCELACION_CONFIRMACION
        guardar_sesion(chat_id, sesion)
        return responder(h_can.texto_confirmacion_cancelacion(reserva))

    # ── CANCELACION: CONFIRMACION ───────────────────────────────
    elif estado == CANCELACION_CONFIRMACION:
        if incoming.upper() == "SI":
            reserva_cancel, politica = cancelar_reserva(ctx["reserva_a_cancelar"]["codigo_reserva"])
            sesion["estado"] = MENU_PRINCIPAL
            guardar_sesion(chat_id, sesion)
            return responder(h_can.texto_cancelacion_exitosa(reserva_cancel, politica))
        elif incoming.upper() in ("NO", "N"):
            return volver_menu(chat_id)
        else:
            guardar_sesion(chat_id, sesion)
            return responder("❌ Por favor respondé *SI* para confirmar la cancelación o *NO* para conservar la reserva.")

    # Fallback
    guardar_sesion(chat_id, sesion)
    return volver_menu(chat_id)


if __name__ == "__main__":
    from scheduler import iniciar_scheduler
    iniciar_scheduler()
    app.run(debug=True, port=5000)

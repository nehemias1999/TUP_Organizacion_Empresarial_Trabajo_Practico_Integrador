"""
Simulador CLI del Bot de Las Pircas Cabañas
Permite probar todos los flujos sin Twilio ni internet.
Ejecutar: python simulador/cli_simulator.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["MODO_SIMULACION"] = "true"

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
from utils.date_utils import timestamp_ahora, fecha_a_iso
from utils.json_db import get_sesion, guardar_sesion, eliminar_sesion, get_cabanas
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

CHAT_ID = "CLI_USER_001"
TELEFONO_DUENO = "+54 9 351 555-0000"


def nueva_sesion():
    return {"estado": MENU_PRINCIPAL, "contexto": {}, "ultima_actividad": timestamp_ahora()}


def bot_responde(texto):
    print("\n" + "─"*60)
    print("🤖 BOT:")
    print(texto)
    print("─"*60)


def usuario_escribe(prompt=""):
    try:
        return input(f"\n📱 Vos: ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\n\n[Simulación terminada]")
        sys.exit(0)


def procesar(incoming, sesion):
    """Núcleo de la FSM — misma lógica que app.py pero sin HTTP."""
    ctx = sesion["contexto"]
    estado = sesion["estado"]

    # Comando admin
    if incoming.upper().startswith("CONFIRMAR "):
        codigo = incoming.split(" ", 1)[1].strip().upper()
        reserva, error = confirmar_pago(codigo)
        if error:
            return f"❌ {error}"
        msg_cliente = h_res.texto_pago_confirmado(reserva, TELEFONO_DUENO)
        print(f"\n[→ MENSAJE AL CLIENTE]\n{msg_cliente}")
        return f"✅ Reserva {codigo} confirmada. Mensaje enviado al cliente."

    # Palabras clave globales
    if incoming.lower() in PALABRAS_MENU:
        eliminar_sesion(CHAT_ID)
        sesion.update(nueva_sesion())
        return h_menu.texto_bienvenida()

    # ── MENU ────────────────────────────────────────────────────
    if estado == MENU_PRINCIPAL:
        if incoming == "1":
            sesion["estado"] = CONSULTA_FECHA_CHECKIN
            return h_disp.solicitar_fecha_checkin()
        elif incoming == "2":
            sesion["estado"] = MODIFICACION_PEDIR_CODIGO
            return h_mod.solicitar_codigo()
        elif incoming == "3":
            sesion["estado"] = CANCELACION_PEDIR_CODIGO
            return h_can.solicitar_codigo()
        elif incoming == "4":
            return h_menu.texto_info_cabanas()
        elif incoming == "5":
            return h_menu.texto_instagram()
        else:
            return "❌ Por favor ingresá una opción correcta.\n\n" + h_menu.texto_bienvenida()

    elif estado == CONSULTA_FECHA_CHECKIN:
        fecha, error, _ = h_disp.procesar_fecha_checkin(incoming, ctx)
        if error:
            return error + "\n\n" + h_disp.solicitar_fecha_checkin()
        sesion["estado"] = CONSULTA_FECHA_CHECKOUT
        return h_disp.solicitar_fecha_checkout(fecha)

    elif estado == CONSULTA_FECHA_CHECKOUT:
        from datetime import datetime
        ci = ctx["checkin"] if not isinstance(ctx["checkin"], str) else datetime.strptime(ctx["checkin"], "%Y-%m-%d").date()
        fecha, error, _ = h_disp.procesar_fecha_checkout(incoming, ci, ctx)
        if error:
            return error + "\n\n" + h_disp.solicitar_fecha_checkout(ci)
        sesion["estado"] = CONSULTA_PERSONAS
        return h_disp.solicitar_personas()

    elif estado == CONSULTA_PERSONAS:
        personas, error, _ = h_disp.procesar_personas(incoming, ctx)
        if error:
            return error + "\n\n" + h_disp.solicitar_personas()
        from datetime import datetime
        ci = ctx["checkin"] if not isinstance(ctx["checkin"], str) else datetime.strptime(ctx["checkin"], "%Y-%m-%d").date()
        co = ctx["checkout"] if not isinstance(ctx["checkout"], str) else datetime.strptime(ctx["checkout"], "%Y-%m-%d").date()
        disponibles, texto = h_disp.mostrar_disponibilidad(ci, co, personas)
        ctx["_disponibles"] = disponibles or []

        if ctx.get("flujo") == "reserva" and disponibles:
            sesion["estado"] = SELECCION_CABANA
            return texto + "\n\n" + h_res.solicitar_seleccion_cabana(disponibles)

        sesion["estado"] = MOSTRANDO_DISPONIBILIDAD
        return texto

    elif estado == MOSTRANDO_DISPONIBILIDAD:
        if incoming.upper() == "RESERVAR":
            sesion["estado"] = SELECCION_CABANA
            ctx["flujo"] = "reserva"
            return h_res.solicitar_seleccion_cabana(ctx.get("_disponibles", []))
        if incoming.upper() == "FECHAS":
            for key in ("checkin", "checkout", "personas", "_disponibles", "disponibles_ids"):
                ctx.pop(key, None)
            sesion["estado"] = CONSULTA_FECHA_CHECKIN
            return h_disp.solicitar_fecha_checkin()
        return "❌ Opción inválida.\n\nEscribí *RESERVAR* para hacer una reserva, *FECHAS* para buscar otras fechas, o *MENU* para volver al inicio."

    elif estado == SELECCION_CABANA:
        disponibles = ctx.get("_disponibles", [])
        seleccion, error = h_res.procesar_seleccion_cabana(incoming, disponibles)
        if error:
            return f"❌ {error}\n\n" + h_res.solicitar_seleccion_cabana(disponibles)
        ctx["cabana_seleccionada"] = seleccion["cabana"]
        ctx["precios_seleccionados"] = seleccion["precios"]
        sesion["estado"] = CAPTURA_NOMBRE
        return h_res.solicitar_nombre()

    elif estado == CAPTURA_NOMBRE:
        nombre, error, _ = h_res.procesar_nombre(incoming, ctx)
        if error:
            return error + "\n\n" + h_res.solicitar_nombre()
        ctx["nombre"] = nombre
        sesion["estado"] = CAPTURA_DNI
        return h_res.solicitar_dni()

    elif estado == CAPTURA_DNI:
        dni, error, _ = h_res.procesar_dni(incoming, ctx)
        if error:
            return error + "\n\n" + h_res.solicitar_dni()
        ctx["dni"] = dni
        sesion["estado"] = CAPTURA_TELEFONO
        return h_res.solicitar_telefono()

    elif estado == CAPTURA_TELEFONO:
        tel, error, _ = h_res.procesar_telefono(incoming, ctx)
        if error:
            return error + "\n\n" + h_res.solicitar_telefono()
        ctx["telefono"] = tel
        sesion["estado"] = SELECCION_MODALIDAD_PAGO
        return h_res.solicitar_modalidad_pago(ctx["precios_seleccionados"])

    elif estado == SELECCION_MODALIDAD_PAGO:
        modalidad, error = h_res.procesar_modalidad_pago(incoming)
        if error:
            return f"❌ {error}\n\n" + h_res.solicitar_modalidad_pago(ctx["precios_seleccionados"])
        ctx["modalidad_pago"] = modalidad
        sesion["estado"] = CONFIRMACION_RESERVA
        from datetime import datetime
        ci = ctx["checkin"] if not isinstance(ctx["checkin"], str) else datetime.strptime(ctx["checkin"], "%Y-%m-%d").date()
        co = ctx["checkout"] if not isinstance(ctx["checkout"], str) else datetime.strptime(ctx["checkout"], "%Y-%m-%d").date()
        return h_res.texto_resumen_reserva(
            ctx["cabana_seleccionada"], ci, co, ctx["personas"],
            ctx["nombre"], ctx["dni"], ctx["telefono"],
            modalidad, ctx["precios_seleccionados"]
        )

    elif estado == CONFIRMACION_RESERVA:
        if incoming.upper() == "SI":
            from datetime import datetime
            ci = ctx["checkin"] if not isinstance(ctx["checkin"], str) else datetime.strptime(ctx["checkin"], "%Y-%m-%d").date()
            co = ctx["checkout"] if not isinstance(ctx["checkout"], str) else datetime.strptime(ctx["checkout"], "%Y-%m-%d").date()
            huesped = {
                "nombre_completo": ctx["nombre"],
                "dni": ctx["dni"],
                "telefono": ctx["telefono"],
                "whatsapp": f"whatsapp:+54{ctx['telefono']}",
            }
            reserva = crear_reserva(
                ctx["cabana_seleccionada"], ci, co,
                ctx["personas"], huesped,
                ctx["modalidad_pago"], ctx["precios_seleccionados"]
            )
            ctx["codigo_reserva_activo"] = reserva["codigo_reserva"]
            sesion["estado"] = ESPERA_COMPROBANTE
            return h_res.texto_datos_pago(reserva)
        elif incoming.upper() in ("NO", "N"):
            sesion.update(nueva_sesion())
            return "Operación cancelada.\n\n" + h_menu.texto_bienvenida()
        else:
            return "❌ Por favor respondé *SI* para confirmar la reserva o *NO* para cancelar."

    elif estado == ESPERA_COMPROBANTE:
        codigo = ctx.get("codigo_reserva_activo", "")
        registrar_comprobante(codigo, incoming)
        sesion["estado"] = COMPROBANTE_RECIBIDO
        return (
            "✅ *¡Comprobante recibido!*\n\n"
            "Le avisamos al administrador. Recibirás la confirmación pronto.\n\n"
            "¡Gracias por elegir *Las Pircas Cabañas*! 🏡\n\n"
            "¿Qué querés hacer ahora?\n"
            "  *1* — Volver al menú principal\n"
            "  *2* — Salir"
        )

    elif estado == COMPROBANTE_RECIBIDO:
        if incoming.strip() == "2":
            return "__SALIR__"
        sesion.update(nueva_sesion())
        return h_menu.texto_bienvenida()

    elif estado == MODIFICACION_PEDIR_CODIGO:
        reserva, error = h_mod.procesar_codigo(incoming)
        if error:
            return error + "\n\n" + h_mod.solicitar_codigo()
        ctx["reserva_a_modificar"] = reserva
        sesion["estado"] = MODIFICACION_NUEVA_CHECKIN
        return h_mod.solicitar_nueva_checkin(reserva)

    elif estado == MODIFICACION_NUEVA_CHECKIN:
        fecha, error, _ = h_mod.procesar_nueva_checkin(incoming, ctx)
        if error:
            return error + "\n\n" + h_mod.solicitar_nueva_checkin(ctx["reserva_a_modificar"])
        ctx["nuevo_checkin"] = fecha
        sesion["estado"] = MODIFICACION_NUEVA_CHECKOUT
        return h_mod.solicitar_nueva_checkout()

    elif estado == MODIFICACION_NUEVA_CHECKOUT:
        from datetime import datetime
        ci = ctx["nuevo_checkin"] if not isinstance(ctx["nuevo_checkin"], str) else datetime.strptime(ctx["nuevo_checkin"], "%Y-%m-%d").date()
        fecha, error, _ = h_mod.procesar_nueva_checkout(incoming, ci, ctx)
        if error:
            return error + "\n\n" + h_mod.solicitar_nueva_checkout()
        ctx["nuevo_checkout"] = fecha
        disponible, error_disp = h_mod.verificar_disponibilidad_cambio(ctx["reserva_a_modificar"], ci, fecha)
        if not disponible:
            return f"❌ {error_disp}\n\n" + h_mod.solicitar_nueva_checkout()
        cabanas = {c["id"]: c for c in get_cabanas()}
        cabana = cabanas[ctx["reserva_a_modificar"]["cabana_id"]]
        nuevos_precios = calcular_precio(cabana, ci, fecha)
        ctx["nuevos_precios"] = nuevos_precios
        sesion["estado"] = MODIFICACION_CONFIRMACION
        return h_mod.texto_confirmacion_cambio(ctx["reserva_a_modificar"], ci, fecha, nuevos_precios)

    elif estado == MODIFICACION_CONFIRMACION:
        if incoming.upper() == "SI":
            from datetime import datetime
            ci = ctx["nuevo_checkin"] if not isinstance(ctx["nuevo_checkin"], str) else datetime.strptime(ctx["nuevo_checkin"], "%Y-%m-%d").date()
            co = ctx["nuevo_checkout"] if not isinstance(ctx["nuevo_checkout"], str) else datetime.strptime(ctx["nuevo_checkout"], "%Y-%m-%d").date()
            reserva_mod, error = modificar_fechas(ctx["reserva_a_modificar"]["codigo_reserva"], ci, co)
            if error:
                return f"❌ {error}"
            sesion["estado"] = MENU_PRINCIPAL
            from utils.date_utils import formato_fecha
            return (
                f"✅ Fechas actualizadas para *{reserva_mod['codigo_reserva']}*.\n"
                f"Nueva estadía: {formato_fecha(ci.strftime('%Y-%m-%d'))} → {formato_fecha(co.strftime('%Y-%m-%d'))}"
            )
        elif incoming.upper() in ("NO", "N"):
            sesion.update(nueva_sesion())
            return h_menu.texto_bienvenida()
        else:
            return "❌ Por favor respondé *SI* para confirmar el cambio o *NO* para cancelar."

    elif estado == CANCELACION_PEDIR_CODIGO:
        reserva, error = h_can.procesar_codigo(incoming)
        if error:
            return error + "\n\n" + h_can.solicitar_codigo()
        ctx["reserva_a_cancelar"] = reserva
        sesion["estado"] = CANCELACION_CONFIRMACION
        return h_can.texto_confirmacion_cancelacion(reserva)

    elif estado == CANCELACION_CONFIRMACION:
        if incoming.upper() == "SI":
            reserva_cancel, politica = cancelar_reserva(ctx["reserva_a_cancelar"]["codigo_reserva"])
            sesion["estado"] = MENU_PRINCIPAL
            return h_can.texto_cancelacion_exitosa(reserva_cancel, politica)
        elif incoming.upper() in ("NO", "N"):
            sesion.update(nueva_sesion())
            return h_menu.texto_bienvenida()
        else:
            return "❌ Por favor respondé *SI* para confirmar la cancelación o *NO* para conservar la reserva."

    sesion.update(nueva_sesion())
    return h_menu.texto_bienvenida()


def main():
    print("\n" + "="*60)
    print("  LAS PIRCAS CABAÑAS — Simulador de Bot WhatsApp")
    print("  Escribí 'salir' para terminar | 'menu' para reiniciar")
    print("="*60)

    sesion = nueva_sesion()
    bot_responde(h_menu.texto_bienvenida())

    while True:
        incoming = usuario_escribe()
        if not incoming:
            continue
        if incoming.lower() == "salir":
            print("\n[Simulación finalizada]\n")
            break

        try:
            respuesta = procesar(incoming, sesion)
        except Exception as e:
            respuesta = (
                f"⚠️ Ocurrió un error inesperado: {e}\n"
                "El bot continúa funcionando. Escribí MENU para volver al inicio."
            )
        guardar_sesion(CHAT_ID, sesion)
        if respuesta == "__SALIR__":
            print("\n[Simulación finalizada]\n")
            break
        bot_responde(respuesta)


if __name__ == "__main__":
    main()

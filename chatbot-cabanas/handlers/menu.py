import os
from utils.json_db import get_cabanas

INSTAGRAM_URL = os.getenv("INSTAGRAM_URL", "https://www.instagram.com/laspircascabanas")
GOOGLE_MAPS_URL = os.getenv("GOOGLE_MAPS_URL", "https://maps.app.goo.gl/laspircas")
TELEFONO_DUENO = os.getenv("TELEFONO_DUENO", "+54 9 351 555-0000")


def texto_bienvenida():
    return (
        "¡Hola! 👋 Bienvenido al sistema de reservas de *Las Pircas Cabañas*.\n"
        "Soy tu asistente virtual. ¿En qué te puedo ayudar?\n\n"
        "1️⃣ Hacer una reserva\n"
        "2️⃣ Modificar una reserva\n"
        "3️⃣ Cancelar una reserva\n"
        "4️⃣ Ver información de nuestras cabañas\n"
        "5️⃣ Seguinos en Instagram\n\n"
        "Respondé con el número de la opción que deseás.\n"
        "_En cualquier momento escribí MENU para volver acá._"
    )


def texto_info_cabanas():
    cabanas = get_cabanas()
    lineas = ["🏡 *Nuestras Cabañas — Las Pircas*\n"]
    for c in cabanas:
        amenities = ", ".join(c["amenities"])
        lineas.append(
            f"*{c['nombre']}* ({c['capacidad_max']} personas)\n"
            f"  💰 ${c['precio_base_noche']:,}/noche (precio base)\n"
            f"  📝 {c['descripcion']}\n"
            f"  ✅ {amenities}\n"
        )
    lineas.append("_Check-in y check-out: 10:00 hs_")
    lineas.append("_Escribí MENU para volver al inicio._")
    return "\n".join(lineas)


def texto_instagram():
    return (
        f"📸 ¡Seguinos en Instagram para ver fotos de nuestras cabañas!\n\n"
        f"👉 {INSTAGRAM_URL}\n\n"
        "_Escribí MENU para volver al menú principal._"
    )


def texto_opcion_invalida():
    return (
        "No entendí tu elección. 😅\n"
        "Por favor respondé con un número del 1 al 5, o escribí MENU para ver las opciones."
    )

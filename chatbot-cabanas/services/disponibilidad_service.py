from utils.json_db import get_cabanas, hay_solapamiento

ESTADOS_OCUPADOS = {"PENDIENTE_PAGO", "PAGO_PARCIAL", "CONFIRMADA", "ACTIVA"}


def _cabana_disponible(cabana_id, checkin, checkout):
    return not hay_solapamiento(cabana_id, checkin, checkout, ESTADOS_OCUPADOS)


def consultar_disponibilidad(checkin, checkout, personas):
    """
    Retorna (disponibles, reservadas) para el rango y cantidad de personas.
    disponibles: lista de {cabana, precios}
    reservadas: lista de cabanas con capacidad suficiente pero ocupadas en esas fechas
    """
    from services.precio_service import calcular_precio
    cabanas = get_cabanas()
    disponibles = []
    reservadas = []
    for cabana in cabanas:
        if not cabana["activa"]:
            continue
        if cabana["capacidad_max"] < personas:
            continue
        if _cabana_disponible(cabana["id"], checkin, checkout):
            precios = calcular_precio(cabana, checkin, checkout)
            disponibles.append({"cabana": cabana, "precios": precios})
        else:
            reservadas.append(cabana)
    return disponibles, reservadas

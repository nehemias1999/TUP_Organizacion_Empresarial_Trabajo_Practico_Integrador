from utils.json_db import get_tarifas
from utils.date_utils import noches


def calcular_precio(cabana, checkin, checkout):
    """
    Calcula el precio total para una cabaña y rango de fechas.
    Aplica recargos por fin de semana, temporada alta y descuentos por estadía larga.
    Retorna un dict con el desglose.
    """
    tarifas = get_tarifas()
    precio_base = cabana["precio_base_noche"]
    cant_noches = noches(checkin, checkout)

    total = 0.0
    recargo_finde_aplicado = False
    recargo_temporada_aplicado = False

    from datetime import timedelta
    noche_actual = checkin
    while noche_actual < checkout:
        precio_noche = precio_base
        dia_semana = noche_actual.strftime("%A")

        # Recargo fin de semana
        dias_finde = tarifas["recargos"]["fin_de_semana"]["dias"]
        if dia_semana in dias_finde:
            precio_noche *= (1 + tarifas["recargos"]["fin_de_semana"]["porcentaje"])
            recargo_finde_aplicado = True

        # Recargo temporada alta
        mes_dia = noche_actual.strftime("%m-%d")
        for periodo in tarifas["recargos"]["temporada_alta"]["periodos"]:
            if periodo["desde"] <= mes_dia <= periodo["hasta"]:
                precio_noche *= (1 + tarifas["recargos"]["temporada_alta"]["porcentaje"])
                recargo_temporada_aplicado = True
                break

        total += precio_noche
        noche_actual += timedelta(days=1)

    # Descuento estadía larga
    descuento = 0.0
    min_noches = tarifas["descuentos"]["estadia_larga"]["noches_minimas"]
    if cant_noches >= min_noches:
        descuento = tarifas["descuentos"]["estadia_larga"]["porcentaje"]
        total *= (1 - descuento)

    sena = round(total * tarifas["pago"]["sena_porcentaje"])

    return {
        "precio_por_noche_base": precio_base,
        "noches": cant_noches,
        "recargo_fin_semana": tarifas["recargos"]["fin_de_semana"]["porcentaje"] if recargo_finde_aplicado else 0.0,
        "recargo_temporada": tarifas["recargos"]["temporada_alta"]["porcentaje"] if recargo_temporada_aplicado else 0.0,
        "descuento_estadia": descuento,
        "total_final": round(total),
        "monto_sena": sena,
        "saldo_pendiente": round(total) - sena,
    }

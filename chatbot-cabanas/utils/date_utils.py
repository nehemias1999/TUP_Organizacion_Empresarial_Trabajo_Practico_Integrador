from datetime import datetime, timedelta


HORA_CHECKIN = 10
HORA_CHECKOUT = 10


def checkin_dt(fecha):
    """Datetime exacto del check-in (fecha a las 10:00)."""
    return datetime.combine(fecha, datetime.strptime("10:00", "%H:%M").time())


def checkout_dt(fecha):
    """Datetime exacto del check-out (fecha a las 10:00)."""
    return datetime.combine(fecha, datetime.strptime("10:00", "%H:%M").time())


def noches(checkin, checkout):
    """Cantidad de noches entre dos fechas."""
    return (checkout - checkin).days


def horas_hasta_checkin(fecha_checkin_str):
    """Horas restantes hasta el check-in desde ahora."""
    from datetime import date
    checkin = datetime.strptime(fecha_checkin_str, "%Y-%m-%d").date()
    diff = checkin_dt(checkin) - datetime.now()
    return diff.total_seconds() / 3600


def dias_hasta_checkin(fecha_checkin_str):
    """Días completos hasta el check-in."""
    return horas_hasta_checkin(fecha_checkin_str) / 24


def checkout_vencido(fecha_checkout_str):
    """True si el check-out (a las 10:00) ya pasó."""
    from datetime import date
    co = datetime.strptime(fecha_checkout_str, "%Y-%m-%d").date()
    return checkout_dt(co) <= datetime.now()


def formato_fecha(fecha_str):
    """'2026-07-10' → '10/07/2026'"""
    d = datetime.strptime(fecha_str, "%Y-%m-%d")
    return d.strftime("%d/%m/%Y")


def fecha_a_iso(fecha):
    """objeto date → '2026-07-10'"""
    return fecha.strftime("%Y-%m-%d")


def timestamp_ahora():
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

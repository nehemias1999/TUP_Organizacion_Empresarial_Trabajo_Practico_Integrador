import re
from datetime import datetime, timedelta


FORMATO_FECHA = "%d/%m/%Y"


def validar_fecha(texto):
    """Retorna objeto date si el texto es una fecha válida futura, o None."""
    try:
        fecha = datetime.strptime(texto.strip(), FORMATO_FECHA).date()
        if fecha <= datetime.now().date():
            return None, "La fecha debe ser posterior a hoy."
        return fecha, None
    except ValueError:
        return None, "Formato inválido. Usá DD/MM/AAAA (ej: 25/07/2026)."


def validar_checkout(checkin, texto):
    """Valida que checkout sea al menos 1 noche después del checkin."""
    fecha, error = validar_fecha(texto)
    if error:
        return None, error
    if fecha <= checkin:
        return None, "La fecha de salida debe ser posterior a la de entrada."
    return fecha, None


def validar_anticipacion(checkin, horas_minimas=48):
    """Verifica que el checkin sea al menos N horas en el futuro."""
    ahora = datetime.now()
    checkin_dt = datetime.combine(checkin, datetime.strptime("10:00", "%H:%M").time())
    diferencia = checkin_dt - ahora
    if diferencia < timedelta(hours=horas_minimas):
        return False, f"Las reservas requieren al menos {horas_minimas} horas de anticipación."
    return True, None


def validar_personas(texto):
    """Valida que el número de personas sea entero positivo."""
    try:
        n = int(texto.strip())
        if n < 1 or n > 20:
            return None, "El número de personas debe estar entre 1 y 20."
        return n, None
    except ValueError:
        return None, "Ingresá un número válido (ej: 3)."


def validar_dni(texto):
    """Valida DNI argentino: 7 u 8 dígitos numéricos."""
    dni = re.sub(r"[\.\s\-]", "", texto.strip())
    if re.fullmatch(r"\d{7,8}", dni):
        return dni, None
    return None, "El DNI debe tener 7 u 8 dígitos numéricos, sin puntos ni espacios."


def validar_telefono(texto):
    """Valida teléfono: 8 a 15 dígitos, permite + al inicio."""
    tel = re.sub(r"[\s\-\(\)]", "", texto.strip())
    if re.fullmatch(r"\+?\d{8,15}", tel):
        return tel, None
    return None, "El teléfono debe tener entre 8 y 15 dígitos (podés incluir código de área)."


def validar_nombre(texto):
    """Valida que el nombre tenga al menos dos palabras y solo letras/espacios."""
    nombre = texto.strip()
    if len(nombre) < 3:
        return None, "Ingresá tu nombre completo (nombre y apellido)."
    if not re.fullmatch(r"[A-Za-záéíóúÁÉÍÓÚüÜñÑ\s\-']+", nombre):
        return None, "El nombre solo puede contener letras y espacios."
    if len(nombre.split()) < 2:
        return None, "Ingresá nombre y apellido completos."
    return nombre.title(), None

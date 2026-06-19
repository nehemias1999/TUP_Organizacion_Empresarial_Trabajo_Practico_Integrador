# Las Pircas Cabañas — Bot de Reservas WhatsApp

Bot conversacional de WhatsApp para gestión integral de reservas del complejo "Las Pircas Cabañas". Desarrollado como Trabajo Práctico Integrador de Organización Empresarial — UTN.

---

## Modelo del problema

**Las Pircas Cabañas** es un complejo de alojamiento rural con múltiples cabañas de distinta capacidad y precio. Antes de implementar este sistema, toda la operativa de reservas se manejaba de forma manual:

- El dueño respondía consultas por WhatsApp personal o llamadas telefónicas
- Las reservas se anotaban en planillas o agendas físicas
- No existía un mecanismo automatizado para verificar disponibilidad en tiempo real
- Los precios con recargos de temporada alta o fin de semana se calculaban a mano
- La política de cancelaciones y reembolsos se aplicaba de forma inconsistente
- No había registro estructurado del historial de reservas por huésped

Esto generaba errores frecuentes (doble reserva de la misma cabaña), tiempos de respuesta lentos en horarios fuera de oficina, y una experiencia de usuario fragmentada.

**La solución** es un bot que atiende las 24 horas por el canal que los clientes ya usan (WhatsApp), automatizando el ciclo completo:

```
Consulta de disponibilidad → Reserva → Pago (seña o total) → Confirmación
       → Modificación de fechas → Cancelación con reembolso → Reseña post-estadía
```

---

## Funcionalidades

### Flujos principales

| Flujo | Descripción |
|-------|-------------|
| **Consulta de disponibilidad** | El usuario ingresa fechas y cantidad de personas. El bot devuelve las cabañas disponibles con precio total desglosado (recargos y descuentos incluidos) |
| **Reserva completa** | Captura datos del huésped (nombre, DNI, teléfono), selección de cabaña, modalidad de pago (total o seña 50%) y recepción del comprobante de transferencia |
| **Modificación de fechas** | El huésped ingresa su código de reserva y nuevas fechas. El bot verifica disponibilidad y recalcula el precio automáticamente |
| **Cancelación con reembolso** | Aplicación automática de la política de reembolso según días de anticipación |

### Política de precios dinámica

| Condición | Ajuste |
|-----------|--------|
| Viernes o sábado | +15% por noche |
| Temporada alta (15 dic–31 ene y jul–ago) | +20% por noche |
| Estadía de 7 noches o más | −10% sobre el total |
| Pago en dos cuotas | 50% de seña al reservar, saldo al hacer check-in |

### Política de cancelaciones

| Anticipación al check-in | Reembolso |
|--------------------------|-----------|
| 7 días o más | 100% |
| Menos de 7 días | 50% |
| Menos de 48 horas | Sin reembolso — cancelación bloqueada |

### Features transversales

- **Máquina de estados** con 21 estados persistidos en base de datos
- **Keywords globales**: escribir `MENU`, `INICIO`, `HOLA`, `CANCELAR` o `SALIR` desde cualquier punto vuelve al menú principal
- **Timeout de sesión** a los 30 minutos de inactividad
- **Comando de administrador**: el dueño confirma pagos enviando `CONFIRMAR <codigo>` desde su número registrado
- **Solicitud de reseña automática**: el scheduler detecta checkouts vencidos y envía un mensaje al huésped con el link de Google Maps
- **Notificaciones al dueño**: email y WhatsApp ante cada nueva reserva, comprobante recibido, modificación y cancelación
- **Simulador CLI** para pruebas offline sin necesitar Twilio

---

## Stack tecnológico

| Componente | Tecnología |
|------------|------------|
| Lenguaje | Python 3.11+ |
| Framework web | Flask 3.0 |
| Base de datos | SQLite con WAL mode y foreign keys |
| ORM / acceso a datos | Capa de abstracción propia (`utils/json_db.py`) |
| Manejo de fechas | python-dateutil 2.8.2, pytz 2024.1 |
---

## Estructura del proyecto

```
chatbot-cabanas/
├── app.py                      # Webhook Flask — punto de entrada de producción
├── states.py                   # Constantes de la máquina de estados (21 estados)
├── whatsapp_client.py          # Cliente Twilio para envío de mensajes
├── scheduler.py                # Job: detecta checkouts vencidos y solicita reseñas
├── requirements.txt
├── handlers/                   # Lógica conversacional por flujo
│   ├── menu.py                 # Menú principal y textos generales
│   ├── disponibilidad.py       # Flujo de consulta de disponibilidad
│   ├── reserva.py              # Flujo de creación de reserva
│   ├── modificacion.py         # Flujo de modificación de fechas
│   └── cancelacion.py          # Flujo de cancelación con reembolso
├── services/                   # Lógica de negocio pura
│   ├── disponibilidad_service.py   # Motor de disponibilidad con overlap detection
│   ├── reservas_service.py         # CRUD de reservas y ciclo de vida
│   └── precio_service.py           # Cálculo de precios dinámicos
├── utils/                      # Utilidades transversales
│   ├── json_db.py              # Capa de acceso a SQLite
│   ├── validators.py           # Validación de fechas, DNI, teléfono, nombre
│   ├── date_utils.py           # Helpers de fecha/hora (check-in, checkout, noches)
│   └── notificaciones.py       # Plantillas de email al dueño
├── data/
│   └── laspircas.db            # Base de datos SQLite (5 tablas)
└── simulador/
    └── cli_simulator.py        # Demo offline — misma FSM sin Twilio
```

---

## Diagramas de base de datos

### Diagrama entidad-relación

```
┌──────────────────────┐         ┌──────────────────────────────────────┐
│        cabanas       │         │               reservas               │
├──────────────────────┤         ├──────────────────────────────────────┤
│ id          TEXT  PK │◄────────│ cabana_id           TEXT   FK        │
│ nombre      TEXT     │  1    N │ codigo_reserva       TEXT   PK        │
│ capacidad_max INT    │         │ checkin              TEXT   YYYY-MM-DD│
│ precio_base_ REAL    │         │ checkout             TEXT   YYYY-MM-DD│
│ descripcion TEXT     │         │ noches               INTEGER          │
│ amenities   TEXT JSON│         │ personas             INTEGER          │
│ activa      INTEGER  │         │ estado               TEXT             │
└──────────────────────┘         │ huesped_dni          TEXT   (índice) │
                                 │ huesped              TEXT   JSON      │
┌──────────────────────┐         │ precios              TEXT   JSON      │
│        sesiones      │         │ pago                 TEXT   JSON      │
├──────────────────────┤         │ resena_solicitada    INTEGER          │
│ chat_id     TEXT  PK │         │ historial_estados    TEXT   JSON      │
│ datos       TEXT JSON│         │ timestamps           TEXT   JSON      │
└──────────────────────┘         │ notas_admin          TEXT             │
                                 └──────────────────────────────────────┘
┌──────────────────────┐
│        config        │
├──────────────────────┤
│ clave       TEXT  PK │   (almacena tarifas, CBU/alias, política de
│ valor       TEXT JSON│    cancelación y recargos en formato JSON)
└──────────────────────┘

┌──────────────────────┐
│      secuencias      │
├──────────────────────┤
│ nombre      TEXT  PK │   (contador autoincremental para generar
│ valor       INTEGER  │    códigos de reserva: RES-YYYYMMDD-NNNN)
└──────────────────────┘
```

### Tabla `cabanas`

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `id` | TEXT PK | Identificador: CAB001, CAB002, … |
| `nombre` | TEXT | Nombre visible: "Cabaña Montaña" |
| `capacidad_max` | INTEGER | Número máximo de huéspedes |
| `precio_base_noche` | REAL | Precio sin recargos por noche |
| `descripcion` | TEXT | Descripción de la cabaña |
| `amenities` | TEXT (JSON) | Array de strings: `["WiFi", "TV", "Cocina"]` |
| `activa` | INTEGER | 1 = disponible para reservar, 0 = deshabilitada |

### Tabla `reservas`

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `codigo_reserva` | TEXT PK | Código único: `RES-20260617-0001` |
| `cabana_id` | TEXT FK | Referencia a `cabanas.id` |
| `checkin` | TEXT | Fecha de entrada (ISO: YYYY-MM-DD) |
| `checkout` | TEXT | Fecha de salida (ISO: YYYY-MM-DD) |
| `noches` | INTEGER | checkout − checkin en días |
| `personas` | INTEGER | Cantidad de huéspedes |
| `estado` | TEXT | Ver ciclo de vida abajo |
| `huesped_dni` | TEXT | DNI del titular (indexado para búsquedas) |
| `huesped` | TEXT (JSON) | `{nombre_completo, dni, telefono, whatsapp}` |
| `precios` | TEXT (JSON) | Desglose completo: base, recargos, descuento, total, seña |
| `pago` | TEXT (JSON) | `{modalidad, monto_pagado, monto_pendiente, comprobante}` |
| `resena_solicitada` | INTEGER | 1 si ya se envió el mensaje de reseña post-checkout |
| `historial_estados` | TEXT (JSON) | Array de `{estado, timestamp}` para auditoría |
| `timestamps` | TEXT (JSON) | `{creacion, ultima_modificacion}` |
| `notas_admin` | TEXT | Campo libre para el dueño |

**Ciclo de vida del campo `estado`:**

```
PENDIENTE_PAGO ──► CONFIRMADA ──► ACTIVA ──► FINALIZADA
      │                │
      └──► PAGO_PARCIAL┘
      
Desde PENDIENTE_PAGO / PAGO_PARCIAL / CONFIRMADA:
      ├──► MODIFICADA   (el huésped cambia fechas)
      └──► CANCELADA    (el huésped cancela)
```

### Tabla `sesiones`

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `chat_id` | TEXT PK | ID de WhatsApp del usuario: `whatsapp:+549123456789` |
| `datos` | TEXT (JSON) | `{estado, contexto, ultima_actividad}` — estado actual de la FSM |

### Tabla `config`

| Clave | Valor (JSON) | Descripción |
|-------|-------------|-------------|
| `tarifas` | Objeto complejo | Recargos (fin de semana, temporada alta), descuentos (estadía larga), política de cancelación, CBU/alias de pago |

### Tabla `secuencias`

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `nombre` | TEXT PK | Nombre del contador: `"reservas"` |
| `valor` | INTEGER | Último número usado; se incrementa al crear cada reserva |

---

## Máquina de estados

```
INICIO → MENU_PRINCIPAL
         ├─[1] Consulta ──► CONSULTA_FECHA_CHECKIN
         │                  → CONSULTA_FECHA_CHECKOUT
         │                  → CONSULTA_PERSONAS
         │                  → MOSTRANDO_DISPONIBILIDAD
         │
         ├─[2] Reserva ───► CONSULTA_FECHA_CHECKIN (si no hay fechas en contexto)
         │                  → SELECCION_CABANA
         │                  → CAPTURA_NOMBRE
         │                  → CAPTURA_DNI
         │                  → CAPTURA_TELEFONO
         │                  → SELECCION_MODALIDAD_PAGO
         │                  → CONFIRMACION_RESERVA
         │                  → ESPERA_COMPROBANTE
         │                  → COMPROBANTE_RECIBIDO
         │
         ├─[3] Modificar ──► MODIFICACION_PEDIR_CODIGO
         │                   → MODIFICACION_NUEVA_CHECKIN
         │                   → MODIFICACION_NUEVA_CHECKOUT
         │                   → MODIFICACION_CONFIRMACION
         │
         └─[4] Cancelar ───► CANCELACION_PEDIR_CODIGO
                             → CANCELACION_CONFIRMACION
```

Keywords globales desde cualquier estado: `MENU` · `INICIO` · `HOLA` · `CANCELAR` · `SALIR` → vuelven a `MENU_PRINCIPAL`.

---

## Instalación y ejecución

### Requisitos previos

- Python 3.11+

### Instalación

```bash
# 1. Clonar el repositorio
git clone https://github.com/usuario/chatbot-cabanas.git
cd chatbot-cabanas

pip install -r requirements.txt
```

### Ejecutar el prototipo

```bash
python simulador/cli_simulator.py
```

Ejecuta la misma máquina de estados y lógica de negocio desde la terminal. No requiere credenciales externas ni configuración adicional. Todos los flujos (consulta, reserva, modificación, cancelación) funcionan de forma completa.

### Confirmar pagos (comando de administrador)

El dueño confirma un pago enviando al bot:

```
CONFIRMAR RES-20260601-0001
```

Funciona tanto en el simulador CLI como en el modo producción. El bot cambia el estado de la reserva a `CONFIRMADA`.

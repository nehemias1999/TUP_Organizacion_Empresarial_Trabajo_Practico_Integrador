# Manual de Usuario
## Bot de Reservas — Las Pircas Cabañas (Prototipo Local)

Este es el manual del prototipo del bot de reservas para Las Pircas Cabañas. El prototipo corre en la terminal mediante un simulador CLI que reproduce la misma lógica de negocio del sistema final: consulta de disponibilidad, reservas, modificaciones y cancelaciones.

---

## ¿Cómo empezar?

Abrí una terminal, posicionarte en la carpeta `chatbot-cabanas` y ejecutá:

```bash
python simulador/cli_simulator.py
```

El simulador arranca y muestra el menú principal directamente. A partir de ahí, escribís tu respuesta y presionás Enter, igual que si chatearas con el bot.

---

## El menú principal

Cuando el bot arranca, te muestra estas opciones:

```
1 - Consultar disponibilidad
2 - Hacer una reserva
3 - Cambiar fechas de una reserva
4 - Cancelar una reserva
5 - Contacto
```

Solo tenés que responder con el **número** de la opción que querés.

---

## Opción 1 — Consultar disponibilidad

Usá esta opción si querés saber qué cabañas hay libres y cuánto costaría. No te compromete a nada.

**Pasos:**

1. Escribí `1` en el chat
2. El bot te pide la **fecha de llegada**. Respondé con el formato `DD/MM/AAAA`
   > Ejemplo: `25/07/2026`
3. El bot te pide la **fecha de salida**. Respondé igual
   > Ejemplo: `28/07/2026`
4. El bot te pregunta **cuántas personas** van. Respondé con un número
   > Ejemplo: `3`
5. El bot te muestra las cabañas disponibles con el precio total estimado y el monto de seña

Si te interesa reservar, podés escribir `2` ahí mismo para pasar directamente al proceso de reserva.

**Cosas a tener en cuenta:**
- La fecha de llegada tiene que ser con al menos **48 horas de anticipación** desde hoy
- El precio puede tener recargos si viajás en fin de semana o en temporada alta (julio, agosto, 15 de diciembre al 31 de enero)
- Si reservás 7 noches o más, el bot aplica un descuento automático del 10%

---

## Opción 2 — Hacer una reserva

**Pasos:**

1. Escribí `2` en el chat
2. Si todavía no consultaste disponibilidad, el bot te va a pedir las fechas y la cantidad de personas (igual que la opción 1)
3. El bot te muestra las cabañas disponibles. Respondé con el **número** de la cabaña que elegís
4. El bot te pide tus datos personales, uno por uno:
   - **Nombre completo** (nombre y apellido)
     > Ejemplo: `María López`
   - **DNI** (solo los números, sin puntos)
     > Ejemplo: `35123456`
   - **Teléfono** (con código de área, sin el 0 ni el 15)
     > Ejemplo: `3512345678`
5. El bot te pregunta cómo querés pagar:
   - `1` — **Pago total**: transferís el 100% ahora
   - `2` — **Seña**: transferís el 50% ahora y el resto lo pagás al llegar
6. El bot te muestra un **resumen completo** con todos los datos. Si todo está bien, escribí `SI` para confirmar (o `NO` para cancelar)
7. El bot te manda los datos bancarios (CBU y alias) con el monto exacto a transferir
8. Hacé la transferencia y **describí el pago** en el chat (escribí el monto, fecha y número de operación)
9. El bot le avisa al dueño. Cuando el dueño revise el pago, **te llega un mensaje de confirmación** con el código de tu reserva

> Guardá el código de reserva, lo vas a necesitar si querés modificar o cancelar.

---

## Opción 3 — Cambiar las fechas de mi reserva

Si ya tenés una reserva confirmada y necesitás cambiar las fechas, usá esta opción.

**Pasos:**

1. Escribí `3` en el chat
2. El bot te pide el **código de tu reserva**
   > Ejemplo: `RES-20260617-0001`
3. El bot te muestra las fechas actuales y te pide la **nueva fecha de llegada**
4. Ingresá la nueva fecha con el formato `DD/MM/AAAA`
5. El bot te pide la **nueva fecha de salida**. Ingresala igual
6. El bot verifica si la misma cabaña está libre en esas fechas y te muestra el **nuevo precio** calculado
7. Si estás de acuerdo, escribí `SI` para confirmar el cambio

Si la cabaña no está disponible en las nuevas fechas, el bot te avisa y volvés al menú.

---

## Opción 4 — Cancelar mi reserva

**Pasos:**

1. Escribí `4` en el chat
2. El bot te pide el **código de tu reserva**
   > Ejemplo: `RES-20260617-0001`
3. El bot calcula cuánto tiempo falta para tu llegada y te dice cuánto dinero te devuelven:

   - **7 días o más antes de la llegada** → te devuelven el **100%** de lo que pagaste
   - **Entre 2 y 7 días antes** → te devuelven el **50%** de lo que pagaste
   - **Menos de 48 horas antes** → no se puede cancelar

4. Si querés seguir con la cancelación, escribí `SI` para confirmar

El dueño recibe la notificación y te contacta para coordinar la devolución del dinero.

---

## Comandos que funcionan en cualquier momento

En cualquier punto de la conversación, podés escribir alguna de estas palabras y el bot te lleva de vuelta al menú principal:

| Lo que escribís | Qué hace |
|-----------------|----------|
| `MENU` | Vuelve al menú principal |
| `INICIO` | Vuelve al menú principal |
| `HOLA` | Vuelve al menú principal |
| `SALIR` | Vuelve al menú principal |
| `CANCELAR` | Cancela lo que estabas haciendo y vuelve al menú |

---

## ¿Qué pasa si no contestás un rato?

Si el bot te mandó un mensaje y vos no respondés en **30 minutos**, la conversación se reinicia automáticamente. La próxima vez que escribas, el bot arranca desde el menú principal. No se guarda ningún dato de lo que estabas cargando.

---

## Reseña después de tu estadía

En el sistema completo, unos días después del checkout el bot envía automáticamente un mensaje con un link para dejar una reseña en Google Maps. En el prototipo local esta notificación se simula pero no genera envíos reales.

---

## Para el dueño — Confirmar un pago

Cuando un cliente manda el comprobante de pago, vos recibís una notificación por WhatsApp con los datos de la reserva.

Para confirmar que el pago llegó, escribí este mensaje desde tu número:

```
CONFIRMAR RES-YYYYMMDD-NNNN
```

> Ejemplo: `CONFIRMAR RES-20260617-0001`

El bot cambia el estado de la reserva a confirmada y le avisa automáticamente al cliente.

Si el pago no llegó o hay algún problema, simplemente no confirmes y comunicate directamente con el cliente.

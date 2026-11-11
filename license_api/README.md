# Generador de licencias comercial — API REST

API FastAPI sin ventanas para FlutterFlow (llamada privada desde su backend), Make y n8n. El programa de escritorio comercial conserva sus pantallas y acepta las nuevas claves. La edición personal sigue funcionando sin activación.

La API firma JWT con Ed25519/EdDSA. **Firma no significa cifrado:** los datos del JWT son legibles; la firma impide cambiar aplicación, permisos, equipo o vencimiento sin la clave privada. No introduzca contraseñas ni datos escolares en la licencia.

## Archivos y dependencias

- `main.py`: rutas, autenticación y límites de la petición.
- `models.py`: JSON de entrada y salida.
- `config.py`: secretos y catálogo de aplicaciones.
- `signing.py`: fechas, firma y datos de emisión.
- `store.py`: Supabase o funcionamiento sin base remota.
- `supabase.sql`: tabla privada `public.licencias`.
- `../license_tokens.py`: validación compartida con el programa comercial.
- `../actualizaciones.py`: avisos firmados y verificación de instaladores.
- `../render.yaml`: despliegue en Render.

Desde la raíz del proyecto, con Python 3.12:

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
python -m pip install -r license_api/requirements.txt
```

Se instalan FastAPI, Uvicorn, HTTPX, PyJWT y Cryptography. No se requiere Tkinter, Flutter ni una interfaz gráfica en el servidor.

## Preparar los secretos con la clave original

Para los instaladores que ya vendió, use **su clave privada original y su contraseña**, correspondientes a `license_public_key.pem`. No genere otra clave al actualizar: las licencias anteriores siguen usando la misma pública.

```powershell
python tools/prepare_license_api.py --private C:\claves-privadas\registro_privada.pem --output C:\claves-privadas\secretos-api.json
```

El comando solicita la contraseña sin mostrarla, comprueba la pública y guarda tres valores: `API_KEY`, `LICENSE_PRIVATE_KEY_B64`, `LICENSE_PRIVATE_KEY_PASSWORD`. No imprime sus valores y rechaza un destino dentro del repositorio. Si aún no tiene claves para un producto nuevo, el repositorio completo incluye `tools/license_tool.py keygen`; no lo use para reemplazar las claves de clientes existentes.

Guarde estos valores en el gestor de secretos del alojamiento. La privada y `SUPABASE_SERVICE_ROLE_KEY` pertenecen exclusivamente al servidor. Ni el instalador, ni el cliente FlutterFlow, ni una URL pública deben contenerlas.

Para probar localmente en PowerShell:

```powershell
$configLicencias = Get-Content C:\claves-privadas\secretos-api.json | ConvertFrom-Json
$env:API_KEY = $configLicencias.API_KEY
$env:LICENSE_PRIVATE_KEY_B64 = $configLicencias.LICENSE_PRIVATE_KEY_B64
$env:LICENSE_PRIVATE_KEY_PASSWORD = $configLicencias.LICENSE_PRIVATE_KEY_PASSWORD
python -m uvicorn license_api.main:app --host 127.0.0.1 --port 8000 --no-access-log
```

Sin secretos válidos la API no inicia. `GET /health` devuelve `{"estado":"ok"}` cuando está preparada. `GET /openapi.json` requiere la misma autenticación que la emisión.

## Emitir una licencia

`POST /generar-licencia`

Headers:

```http
Content-Type: application/json
X-API-Key: TU_SECRETO_DEL_SERVIDOR
Idempotency-Key: pedido-00001234
```

También se admite `Authorization: Bearer TU_SECRETO_DEL_SERVIDOR`. El identificador de pedido es opcional; reutilice el mismo al reintentar una venta. Nunca reutilice ese identificador para otro producto o cliente.

```json
{
  "app_id": "registro",
  "tipo_licencia": "anual",
  "hwid": "ID_DEL_EQUIPO_DEL_CLIENTE"
}
```

`tipo_licencia` admite `mensual`, `anual` y `perpetua`. `hwid` puede omitirse o ser `null`; en ese caso la licencia no queda restringida a una computadora. Para Registro Docente copie el identificador **Equipo** de Licencia y cuenta. Enviar un texto inventado impedirá activarla en el equipo real.

Las fechas se calculan en UTC. Mensual añade un mes calendario y anual un año; un 31 de enero pasa al último día de febrero, y el 29 de febrero se ajusta cuando corresponde. La licencia vence en el instante indicado. Perpetua devuelve `null` y no incluye `exp`.

```json
{
  "licencia_key": "eyJhbGciOiJFZERTQSIs...",
  "fecha_expiracion": "2027-11-11T12:00:00+00:00",
  "estado": "exito"
}
```

En la aplicación comercial: **Licencia y cuenta → Pegar clave recibida por compra en línea**. También puede guardar el JSON de respuesta en un archivo `.licencia` e importarlo. Las `.licencia` antiguas siguen funcionando.

Errores: `401` autenticación, `404` aplicación desconocida, `409` pedido reutilizado con otros datos, `413` petición demasiado grande, `422` entrada incorrecta, `503` no se pudo confirmar la escritura en Supabase. Los errores devuelven `estado: error` y `detalle`, sin devolver una licencia ni datos del error interno del proveedor.

## Catálogo y permisos

`APPS_JSON` define qué productos puede vender la API; el comprador no puede enviar sus propios permisos:

```json
{
  "registro": {"product": "registro", "courses": ["*"]},
  "registro-matematica": {"product": "registro", "courses": ["secundaria:matematica"]},
  "otra-aplicacion": {"product": "otra-aplicacion", "courses": ["*"]}
}
```

El JWT lleva `aud` con el producto destino. Cada otra aplicación debe validar la firma y su propia audiencia. Registro Docente rechaza una licencia dirigida a otro producto. `schema` es la versión del protocolo de licencia, independiente de la versión del programa; actualizar el programa no vence ni reinicia la licencia.

## Supabase opcional

1. Cree su proyecto y abra SQL Editor.
2. Ejecute `license_api/supabase.sql`. Si ya tiene una tabla `licencias` con otro esquema, adapte sus columnas antes de conectar; el script no borra la tabla ni sus registros.
3. Configure `SUPABASE_URL=https://SU_PROYECTO.supabase.co` y `SUPABASE_SERVICE_ROLE_KEY` en los secretos del servidor. Admite service role JWT y las nuevas claves `sb_secret_...`.
4. Reinicie/despliegue la API. La licencia se inserta **antes** de devolver el resultado. Si Supabase falla, se devuelve `503`.
5. Compruebe una venta y repita su `Idempotency-Key`: obtendrá la misma clave, también después de reiniciar el servicio. Un índice único resuelve los reintentos concurrentes.

RLS está habilitado y se revoca el acceso de `anon` y `authenticated`. No dé acceso directo del navegador a las licencias completas o a la clave de servicio. Para el panel administrador use un backend autorizado que exponga solo los datos necesarios.

Sin Supabase la API puede emitir y firmar licencias; los reintentos se recuerdan únicamente en memoria mientras siga vivo ese proceso. No hay historial persistente ni coordinación entre varias instancias: use Supabase para ventas reales. El estado `revocada` en la tabla no invalida por sí solo un JWT ya importado sin conexión; la revocación inmediata requiere añadir una validación periódica en línea.

## FlutterFlow, Make y n8n

1. Verifique el pago en su backend o en el webhook del proveedor de pagos. El generador emite licencias; no confirma pagos.
2. Haga la llamada HTTP desde Make/n8n o una **API privada/backend** de FlutterFlow. No incruste `API_KEY` en la app web/móvil ni en variables públicas del proyecto.
3. Configure el header secreto en las credenciales del conector HTTP. Envíe el identificador del pago como `Idempotency-Key` y los tres campos JSON descritos arriba.
4. Continúe la entrega al cliente solo cuando haya un `200` con `estado: exito`. Ante tiempo de espera o `503`, reintente con el mismo identificador.
5. Entregue `licencia_key` al comprador. Este proyecto no envía automáticamente mensajes ni correos: su automatización decide el canal y el destinatario.

El Bearer de esta API es el secreto del servidor, no el token de inicio de sesión de cualquier usuario de Supabase. Un panel con cuentas de varios administradores necesitará validar sus roles en el backend antes de autorizar la llamada.

## Desplegar en Render

1. Suba el código sin secretos a su repositorio GitHub. Este proyecto incluye `render.yaml`.
2. En Render, **New → Blueprint**, conecte el repositorio y seleccione la rama con estos archivos. También puede crear un Web Service Python manualmente.
3. Build Command: `pip install -r license_api/requirements.txt`.
4. Start Command: `uvicorn license_api.main:app --host 0.0.0.0 --port $PORT --no-access-log`.
5. Añada en Environment los secretos del archivo que preparó. Si Blueprint generó `API_KEY`, puede conservarla y usar ese mismo valor en Make/n8n; no necesita sustituirla por la del archivo local.
6. Configure `APPS_JSON`, y opcionalmente los dos secretos de Supabase. Mantenga `UPDATES_JSON={}` hasta tener un instalador publicado.
7. Despliegue. Pruebe `https://SU-SERVICIO.onrender.com/health` y una emisión autenticada. Configure esa URL base en su automatización.

**Un plan gratuito no equivale a servicio activo garantizado 24/7.** Las instancias gratuitas de Render pueden suspenderse por inactividad y arrancar de nuevo al recibir una llamada; también tienen límites. Puede comenzar ahí y configurar tiempos de espera/reintentos, pero para disponibilidad continua elija un plan que no se suspenda. Vercel ejecuta funciones bajo demanda y su plan Hobby está orientado al uso personal/no comercial; para vender este servicio revise su plan comercial. Consulte las condiciones vigentes: https://render.com/docs/free y https://vercel.com/docs/plans/hobby.

No se ha creado un alojamiento ni conectado su proyecto real de Supabase: estos pasos se completan en sus propias cuentas, con sus secretos.

## Publicar actualizaciones sin borrar datos

Los binarios se instalan en `%LOCALAPPDATA%\Programs\RegistroDocente`; los registros permanecen en `%LOCALAPPDATA%\RegistroDocente`. El instalador conserva el mismo AppId y no desinstala ni sustituye las bases de datos.

1. Genere el instalador comercial de la nueva versión conservando `license_public_key.pem` y el AppId.
2. Publique el **EXE del instalador** en una URL HTTPS descargable sin iniciar sesión, por ejemplo un asset público de GitHub Releases o un objeto público de Supabase Storage. Un enlace a un artefacto privado de Actions no sirve para actualizar a los clientes.
3. Calcule los datos del EXE real:

```bash
python tools/make_update_manifest.py --installer RegistroDocente-Setup.exe --version 2.4.0 --url https://SU-DOMINIO/RegistroDocente-Setup.exe --output actualizacion.json
```

4. Copie el JSON generado a la variable **UPDATES_JSON** del servidor y despliegue. `GET /actualizaciones/registro` devolverá el aviso firmado con la clave del vendedor. La consulta es pública y no necesita la clave de generación de licencias.
5. En el programa comercial, **Actualizaciones → Configurar servidor de actualizaciones**, introduzca `https://SU-SERVICIO.onrender.com/actualizaciones/registro`. Para futuros instaladores puede incrustar la URL pública usando `REGISTRO_UPDATE_URL` al compilar (variable de repositorio en Actions).
6. Al iniciar, el programa comprueba en segundo plano si hay otra versión. Permite descargarla e instalarla; antes de reiniciar pide guardar las notas y exige que termine los formularios pendientes.
7. Comprueba la firma, edición comercial, plataforma, versión creciente, tamaño y SHA-256. Antes de ejecutar el instalador crea un respaldo de bases, biblioteca y cuenta. No ejecuta una descarga alterada ni instala una versión anterior.

Los respaldos quedan en `backups/antes-actualizar-VERSION-FECHA`. La nueva versión migra las bases existentes con los respaldos habituales, sin reiniciar alumnado, notas, colegios ni periodos. La instalación normal también conserva los datos aunque el cliente descargue e instale el EXE manualmente.

## Verificación

En el repositorio completo:

```bash
python -m unittest tests.test_license_api tests.test_actualizaciones tests.test_licencias
```

Las pruebas cubren el contrato HTTP, autenticación, vencimientos, firmas falsas, equipo incorrecto, paquetes, reintentos, Supabase simulado, compatibilidad anterior y conservación de notas/activación en un respaldo de actualización. La conexión real a su Supabase se comprueba después de configurar su proyecto.

# Guía de Verificación de Seguridad

Este documento describe las medidas de seguridad implementadas y cómo verificar que están funcionando correctamente.

## 🔒 Medidas de Seguridad Implementadas

### 1. HTTPS Enforcement (Forzado de HTTPS)

**¿Qué hace?**
- Redirige automáticamente todas las peticiones HTTP a HTTPS en producción
- Protege las credenciales durante la transmisión en la red

**Configuración:**
- Variable de entorno: `FORCE_HTTPS=true` (default: `true`)
- Se desactiva automáticamente para localhost/127.0.0.1 (desarrollo)

**Cómo verificar:**

1. **En producción:**
   ```bash
   # Intentar acceder vía HTTP
   curl -I http://tu-dominio.com/api/v1/health
   
   # Deberías recibir una redirección 301 a HTTPS
   HTTP/1.1 301 Moved Permanently
   Location: https://tu-dominio.com/api/v1/health
   ```

2. **En DevTools del navegador:**
   - Abre DevTools (F12) → pestaña **Network**
   - Haz una petición de login
   - Click en la petición `POST /api/v1/users/login`
   - Verifica en la pestaña **Headers**:
     ```
     ✅ Request URL: https://tu-dominio.com/api/v1/users/login
     ✅ Response Headers:
        strict-transport-security: max-age=31536000; includeSubDomains
     ```

### 2. Security Headers (Headers de Seguridad)

**¿Qué hacen?**
- `Strict-Transport-Security`: Fuerza HTTPS en navegadores
- `X-Content-Type-Options`: Previene MIME type sniffing
- `X-Frame-Options`: Previene clickjacking
- `X-XSS-Protection`: Protección básica contra XSS
- `Referrer-Policy`: Controla qué información se envía en el referrer
- `Permissions-Policy`: Controla qué APIs del navegador están disponibles

**Cómo verificar:**

```bash
# Verificar headers en cualquier endpoint
curl -I https://tu-dominio.com/api/v1/health

# Deberías ver:
Strict-Transport-Security: max-age=31536000; includeSubDomains
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy: geolocation=(), microphone=(), camera=()
```

**En DevTools:**
- Abre cualquier respuesta en la pestaña Network
- Ve a la pestaña **Headers** → **Response Headers**
- Verifica que todos los headers de seguridad estén presentes

### 3. Log Sanitization (Sanitización de Logs)

**¿Qué hace?**
- Elimina automáticamente campos sensibles de los logs
- Campos protegidos: `password`, `current_password`, `new_password`, `two_factor_code`, `secret`, `token`, etc.

**Cómo verificar:**

1. **Revisar logs del servidor:**
   ```bash
   # Buscar logs de login
   grep "Login attempt" logs/app.log
   
   # ✅ CORRECTO - No deberías ver passwords:
   Login attempt for user: johndoe from IP: 192.168.1.1
   
   # ❌ INCORRECTO - Si ves esto, hay un problema:
   Login attempt: {"username": "johndoe", "password": "123456"}
   ```

2. **Verificar en código:**
   - Los endpoints sensibles (`/login`, `/register`, `/me/password`, etc.) usan `sanitize_for_logging()`
   - Los logs solo muestran username/IP, nunca passwords

### 4. Security Monitoring (Monitoreo de Seguridad)

**¿Qué hace?**
- Rastrea intentos fallidos de login por IP
- Bloquea IPs después de 5 intentos fallidos en 15 minutos
- Bloqueo temporal de 30 minutos

**Configuración:**
- `SECURITY_MAX_LOGIN_ATTEMPTS=5` (default: 5)
- `SECURITY_LOGIN_WINDOW_MINUTES=15` (default: 15)
- `SECURITY_BLOCK_DURATION_MINUTES=30` (default: 30)

**Cómo verificar:**

1. **Probar rate limiting:**
   ```bash
   # Intentar login con credenciales incorrectas 6 veces
   for i in {1..6}; do
     curl -X POST https://tu-dominio.com/api/v1/users/login \
       -H "Content-Type: application/json" \
       -d '{"username": "test", "password": "wrong"}'
   done
   
   # En el intento 6, deberías recibir:
   HTTP/1.1 429 Too Many Requests
   {"detail": "Too many failed login attempts. Please try again in X minutes."}
   ```

2. **Revisar logs:**
   ```bash
   # Deberías ver advertencias después de varios intentos:
   WARNING: IP 192.168.1.1 has 4 failed login attempts for user 'test' (limit: 5)
   WARNING: IP 192.168.1.1 blocked due to 5 failed login attempts for user 'test'
   ```

### 5. Trusted Host Validation (Validación de Hosts Confiables)

**¿Qué hace?**
- Valida que las peticiones vengan de hosts permitidos
- Previene ataques de Host Header Injection

**Configuración:**
- Variable de entorno: `ALLOWED_HOSTS=example.com,*.example.com`
- Si no se configura, se permite cualquier host (solo se valida si está configurado)

**Cómo verificar:**

```bash
# Con ALLOWED_HOSTS configurado, peticiones con Host header incorrecto deberían fallar:
curl -H "Host: evil.com" https://tu-dominio.com/api/v1/health

# Deberías recibir:
HTTP/1.1 403 Forbidden
{"detail": "Forbidden: Host not allowed"}
```

## 🧪 Prueba Completa de Seguridad

### Paso 1: Verificar HTTPS

1. Abre tu aplicación en el navegador
2. Abre DevTools (F12) → pestaña **Network**
3. Haz login con tus credenciales
4. Click en la petición `POST /api/v1/users/login`
5. Verifica:
   - ✅ Request URL comienza con `https://`
   - ✅ Response Headers incluyen `strict-transport-security`

### Paso 2: Verificar que las Credenciales NO están en los Logs

1. Revisa los logs del servidor después de hacer login
2. Busca líneas que contengan "Login attempt"
3. Verifica:
   - ✅ Solo ves username e IP
   - ❌ NO ves passwords ni códigos 2FA

### Paso 3: Verificar Rate Limiting

1. Intenta hacer login con credenciales incorrectas 6 veces seguidas
2. Verifica:
   - ✅ Los primeros 5 intentos devuelven `401 Unauthorized`
   - ✅ El 6to intento devuelve `429 Too Many Requests`
   - ✅ Los logs muestran advertencias de bloqueo

### Paso 4: Verificar Security Headers

```bash
# Usa curl o cualquier herramienta HTTP
curl -I https://tu-dominio.com/api/v1/health

# Verifica que todos estos headers estén presentes:
Strict-Transport-Security: max-age=31536000; includeSubDomains
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Referrer-Policy: strict-origin-when-cross-origin
```

## ⚠️ Notas Importantes

### Desarrollo Local

- HTTPS enforcement está **deshabilitado** para localhost/127.0.0.1
- Esto permite desarrollo local sin certificados SSL
- **NUNCA** deshabilites HTTPS en producción

### Producción

- **SIEMPRE** usa HTTPS en producción
- Configura `FORCE_HTTPS=true` en producción
- Configura `ALLOWED_HOSTS` con tus dominios permitidos
- Revisa los logs regularmente para detectar intentos de ataque

### Datos en DevTools

**IMPORTANTE:** Los datos SIEMPRE serán visibles en DevTools ANTES de enviar la petición. Esto es normal y esperado. La protección real viene de:

1. **HTTPS** - Encripta los datos durante la transmisión
2. **Log Sanitization** - Previene que passwords aparezcan en logs del servidor
3. **Security Headers** - Previene ataques comunes del navegador

### ¿Por qué NO usar RSA?

RSA no resuelve el problema porque:
- Los datos seguirían siendo visibles en DevTools (antes de encriptar)
- Los datos seguirían siendo visibles en logs del servidor (después de desencriptar)
- HTTPS ya proporciona encriptación en la red
- RSA solo agregaría complejidad sin beneficio real

## 🔍 Troubleshooting

### Problema: Las peticiones HTTP no redirigen a HTTPS

**Solución:**
1. Verifica que `FORCE_HTTPS=true` en tu `.env`
2. Verifica que NO estás en localhost (el middleware se desactiva automáticamente)
3. Verifica que el middleware está registrado en `main.py`

### Problema: Los passwords aparecen en los logs

**Solución:**
1. Verifica que estás usando `sanitize_for_logging()` en todos los endpoints sensibles
2. Verifica que no estás logueando `request.body` directamente
3. Usa `safe_log_request()` o `sanitize_for_logging()` siempre

### Problema: El rate limiting no funciona

**Solución:**
1. Verifica que `security_monitoring` está importado correctamente
2. Verifica que estás pasando el `request` object a los endpoints
3. Revisa los logs para ver si hay errores en el tracking

## 📚 Referencias

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [Mozilla Security Guidelines](https://infosec.mozilla.org/guidelines/web_security)
- [FastAPI Security Best Practices](https://fastapi.tiangolo.com/tutorial/security/)

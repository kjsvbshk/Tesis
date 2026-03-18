# Frontend — Aplicación Web NBA Bets

Aplicación web SPA (Single Page Application) construida con **React 19 + TypeScript + Vite**. Provee la interfaz de usuario para visualizar predicciones ML, gestionar apuestas virtuales y administrar el perfil de cuenta.

---

## Stack Tecnológico

| Tecnología | Versión | Rol |
|-----------|---------|-----|
| React | 19.1.1 | Framework de UI |
| TypeScript | ~5.9.3 | Tipado estático |
| Vite | 7.1.7 | Build tool y dev server |
| React Router | 7.9.4 | Enrutamiento client-side |
| Zustand | 5.0.8 | Estado global (apuestas activas) |
| Tailwind CSS | 3.4.13 | Estilos utilitarios |
| Radix UI / shadcn/ui | — | Componentes accesibles |
| ESLint | — | Calidad de código |

---

## Estructura del Proyecto

```
Frontend/
├── src/
│   ├── main.tsx                    # Punto de entrada: React root, Router, AuthContext
│   ├── App.tsx                     # Árbol de rutas principal
│   │
│   ├── pages/                      # Componentes de página (uno por ruta)
│   │   ├── HomePage.tsx            # Dashboard: partidos del día, predicciones destacadas
│   │   ├── LoginPage.tsx           # Formulario de login, manejo de JWT
│   │   ├── RegisterPage.tsx        # Registro de usuario + flujo de verificación OTP
│   │   ├── MatchesPage.tsx         # Listado de partidos con filtros
│   │   ├── PredictionsPage.tsx     # Predicciones ML detalladas por partido
│   │   ├── BetsPage.tsx            # Apuestas activas y pendientes
│   │   ├── HistoryPage.tsx         # Historial completo de apuestas
│   │   └── ProfilePage.tsx         # Perfil, saldo de créditos, configuración
│   │
│   ├── components/
│   │   ├── MatchCard.tsx           # Tarjeta de partido con predicción integrada
│   │   ├── MatchList.tsx           # Contenedor de lista de partidos
│   │   ├── BetSlip.tsx             # Panel lateral para crear apuesta
│   │   ├── ProtectedRoute.tsx      # Guard: redirige a /login si no hay JWT
│   │   ├── RoleProtectedRoute.tsx  # Guard: verifica rol del usuario (RBAC)
│   │   ├── layout/
│   │   │   └── SidebarLayout.tsx   # Layout con sidebar de navegación
│   │   └── ui/                     # Componentes base (shadcn/ui)
│   │       ├── button.tsx
│   │       ├── card.tsx
│   │       ├── input.tsx
│   │       ├── toast.tsx
│   │       └── ...
│   │
│   ├── contexts/
│   │   └── AuthContext.tsx         # Contexto global de autenticación
│   │
│   ├── store/
│   │   └── bets.ts                 # Store Zustand: estado de apuestas activas
│   │
│   ├── services/                   # Capa de integración con la API
│   │   ├── api.ts                  # Cliente axios/fetch base con interceptores
│   │   ├── auth.service.ts         # Login, registro, verificación OTP
│   │   ├── matches.service.ts      # Consultas de partidos
│   │   ├── predictions.service.ts  # Solicitudes de predicción ML
│   │   └── bets.service.ts         # Creación y consulta de apuestas
│   │
│   ├── hooks/
│   │   ├── useAuth.ts              # Hook para consumir AuthContext
│   │   └── use-toast.ts            # Sistema de notificaciones (toasts)
│   │
│   └── lib/
│       └── utils.ts                # cn() para clases Tailwind, formatters
│
├── public/                         # Assets estáticos
├── vercel.json                     # Configuración de routing SPA para Vercel
├── vite.config.ts                  # Configuración de Vite y proxy de desarrollo
├── tailwind.config.js
├── tsconfig.json
└── package.json
```

---

## Arquitectura de la Aplicación

### Flujo de Autenticación

```
Usuario → LoginPage
  → auth.service.ts POST /api/v1/users/login
  → Recibe { access_token, token_type }
  → AuthContext.setToken(token)
    → localStorage.setItem("token", token)
    → Decodifica JWT → extrae user_id, role, exp
  → React Router navega a /home

En cada request:
  → api.ts interceptor agrega Header: Authorization: Bearer {token}
  → Si 401 → AuthContext.logout() → navega a /login
```

### Gestión de Estado

```
AuthContext (React Context)
  ├── token: string | null
  ├── user: { id, email, role, credits }
  ├── isAuthenticated: boolean
  ├── login(token) / logout()
  └── refreshUser()

Zustand Store (bets.ts)
  ├── activeBets: Bet[]
  ├── addBet(bet)
  ├── removeBet(betId)
  └── clearBets()
```

El estado de autenticación vive en `AuthContext` (React Context API). El estado de apuestas activas en el BetSlip vive en Zustand para permitir acceso desde cualquier componente sin prop drilling.

### Rutas y Guards

```
/ → redirige a /home

Rutas públicas:
  /login        → LoginPage
  /register     → RegisterPage

Rutas protegidas (ProtectedRoute — requieren JWT válido):
  /home         → HomePage
  /matches      → MatchesPage
  /predictions  → PredictionsPage
  /bets         → BetsPage
  /history      → HistoryPage
  /profile      → ProfilePage

Rutas con rol (RoleProtectedRoute):
  /admin        → Panel de administración (rol: admin)
```

### Capa de Servicios

Todos los módulos de `services/` usan el cliente base `api.ts` que:
1. Configura `baseURL` desde `VITE_API_BASE_URL`
2. Adjunta el JWT en el header `Authorization`
3. Maneja errores 401 (token expirado → logout automático)
4. Serializa/deserializa JSON

---

## Instalación y Configuración

### Requisitos
- Node.js 18+
- Backend corriendo y accesible

### Instalación

```bash
cd Frontend
npm install
```

### Variables de entorno

Crear archivo `.env` en `Frontend/`:
```bash
VITE_API_BASE_URL=http://localhost:8000/api/v1
```

Para producción, apuntar al backend en Render:
```bash
VITE_API_BASE_URL=https://tu-backend.onrender.com/api/v1
```

### Proxy de desarrollo

`vite.config.ts` puede configurar un proxy para evitar CORS durante desarrollo:
```ts
server: {
  proxy: {
    '/api': 'http://localhost:8000'
  }
}
```

---

## Comandos Disponibles

```bash
# Servidor de desarrollo con HMR (Hot Module Replacement)
npm run dev
# → http://localhost:5173

# Build de producción (output en dist/)
npm run build

# Preview del build de producción
npm run preview

# Linter
npm run lint
```

---

## Flujos de Usuario

### Registro y activación
1. `POST /users/register` — crea cuenta inactiva
2. Email con código OTP de 6 dígitos (TTL 15 min)
3. `POST /users/verify-email` — activa cuenta y asigna créditos iniciales
4. Login automático

### Ver predicción de un partido
1. Navegar a **Partidos** → seleccionar partido
2. `MatchCard` solicita `GET /predictions/game/{game_id}`
3. Backend consulta modelo ML → retorna probabilidades, scores esperados, confianza
4. Predicción visible en la tarjeta del partido

### Crear apuesta
1. En `MatchCard` → clic en equipo ganador → se abre `BetSlip`
2. Ingresar monto de créditos
3. `bets.service.ts POST /bets` — verifica saldo, crea apuesta, deduce créditos
4. Toast de confirmación
5. Apuesta visible en `/bets`

---

## Deployment en Vercel

1. **Framework Preset**: Vite
2. **Root Directory**: `Frontend`
3. **Build Command**: `npm run build`
4. **Output Directory**: `dist`
5. **Variable de entorno**: `VITE_API_BASE_URL=https://tu-backend.onrender.com/api/v1`

El archivo `vercel.json` configura rewrite de todas las rutas a `index.html` para que React Router funcione correctamente en producción:

```json
{
  "rewrites": [{ "source": "/(.*)", "destination": "/index.html" }]
}
```

---

## Solución de Problemas Comunes

| Problema | Causa probable | Solución |
|----------|---------------|---------|
| App no inicia | Dependencias no instaladas | `npm install` |
| Error 401 en todas las rutas | Token expirado o incorrecto | Cerrar sesión y volver a iniciar |
| Datos no cargan | Backend no accesible | Verificar `VITE_API_BASE_URL` y que el backend esté corriendo |
| Rutas 404 en producción | SPA routing no configurado | Verificar `vercel.json` |
| CORS error en desarrollo | Proxy no configurado | Verificar proxy en `vite.config.ts` |

---

## Notas de Diseño

- **Créditos virtuales**: El sistema no maneja dinero real. Los créditos son un mecanismo lúdico con propósito educativo.
- **Predicciones educativas**: Los outputs del modelo ML son probabilísticos y no constituyen asesoramiento de apuestas reales.
- **TypeScript estricto**: El proyecto usa `strict: true` en `tsconfig.json`. Todos los tipos de respuesta de la API están definidos en los archivos de servicios.

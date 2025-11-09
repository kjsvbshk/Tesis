# Aplicación Web de Predicciones y Apuestas Virtuales NBA

## ¿Qué es esta aplicación?

Esta es la aplicación web que los usuarios ven y usan. Es la "cara" del proyecto - una interfaz visual donde los usuarios pueden:

- **Ver partidos** de la NBA que están por jugarse
- **Obtener predicciones** sobre quién ganará usando inteligencia artificial
- **Hacer apuestas virtuales** usando créditos (no dinero real)
- **Ver su historial** de apuestas y resultados
- **Gestionar su perfil** y créditos

Piensa en esto como una aplicación web moderna y fácil de usar que se conecta con el backend para obtener predicciones y gestionar apuestas.

## ¿Qué hace la aplicación?

### 1. Página de Inicio (Home)
- Muestra los partidos más importantes del día
- Predicciones destacadas
- Resumen de tus apuestas activas

### 2. Partidos (Matches)
- Lista completa de todos los partidos disponibles
- Filtros para buscar partidos por fecha, equipo, etc.
- Información detallada de cada partido:
  - Equipos que juegan
  - Fecha y hora
  - Estadísticas de los equipos
  - Predicciones de IA

### 3. Apuestas (Bets)
- Ver todas tus apuestas activas
- Historial de apuestas pasadas
- Resultados de apuestas ganadas o perdidas
- Detalles de cada apuesta

### 4. Historial (History)
- Registro completo de todas tus actividades
- Apuestas realizadas
- Créditos ganados o perdidos
- Estadísticas de tu rendimiento

### 5. Perfil (Profile)
- Información de tu cuenta
- Saldo de créditos virtuales
- Configuración de perfil
- Estadísticas personales

## ¿Cómo funciona la aplicación?

La aplicación funciona así:

1. **El usuario abre la aplicación** en su navegador
2. **Se registra o inicia sesión** para crear una cuenta
3. **Navega por las diferentes páginas** para ver partidos, predicciones, etc.
4. **Hace una apuesta** seleccionando un partido y eligiendo quién cree que ganará
5. **El sistema procesa la apuesta** y deduce créditos de su cuenta
6. **Cuando termina el partido**, el sistema verifica si acertó
7. **Si acertó**, recibe créditos según las probabilidades

Todo esto sucede de forma visual e interactiva, sin necesidad de escribir código o usar comandos complicados.

## Tecnologías Utilizadas

Esta aplicación está construida con tecnologías modernas:

- **React**: Framework para crear interfaces de usuario interactivas
- **TypeScript**: Lenguaje que añade seguridad de tipos a JavaScript
- **Vite**: Herramienta rápida para desarrollar y construir la aplicación
- **Tailwind CSS**: Framework para diseñar la interfaz de forma rápida y consistente
- **React Router**: Para navegar entre diferentes páginas
- **Zustand**: Para gestionar el estado de la aplicación (como las apuestas activas)

## Estructura del Proyecto

```
Frontend/
├── src/
│   ├── pages/              # Páginas principales de la aplicación
│   │   ├── HomePage.tsx    # Página de inicio
│   │   ├── MatchesPage.tsx # Página de partidos
│   │   ├── BetsPage.tsx    # Página de apuestas
│   │   ├── HistoryPage.tsx # Página de historial
│   │   └── ProfilePage.tsx # Página de perfil
│   │
│   ├── components/          # Componentes reutilizables
│   │   ├── MatchCard.tsx   # Tarjeta que muestra un partido
│   │   ├── MatchList.tsx   # Lista de partidos
│   │   ├── BetSlip.tsx     # Panel de apuestas
│   │   ├── layout/         # Componentes de diseño
│   │   │   └── SidebarLayout.tsx  # Barra lateral de navegación
│   │   └── ui/             # Componentes de interfaz básicos
│   │       ├── button.tsx  # Botones
│   │       ├── card.tsx    # Tarjetas
│   │       ├── input.tsx   # Campos de entrada
│   │       └── ...         # Otros componentes
│   │
│   ├── store/              # Gestión de estado
│   │   └── bets.ts         # Estado de las apuestas
│   │
│   ├── hooks/              # Funciones reutilizables
│   │   └── use-toast.ts    # Para mostrar notificaciones
│   │
│   ├── lib/                # Utilidades
│   │   └── utils.ts        # Funciones útiles
│   │
│   ├── App.tsx             # Componente principal
│   └── main.tsx            # Punto de entrada
│
├── public/                 # Archivos públicos (imágenes, etc.)
├── package.json            # Dependencias del proyecto
└── vite.config.ts          # Configuración de Vite
```

## Instalación y Configuración

### Requisitos Previos

- Node.js 18 o superior
- npm o yarn

### Pasos de Instalación

1. **Instalar las dependencias:**
   ```bash
   cd Frontend
   npm install
   ```

2. **Configurar la conexión al backend:**
   - Asegúrate de que el backend esté corriendo en http://localhost:8000
   - Si el backend está en otra dirección, edita los archivos que hacen peticiones a la API

3. **Ejecutar la aplicación en modo desarrollo:**
   ```bash
   npm run dev
   ```

   La aplicación estará disponible en: http://localhost:5173

### Comandos Disponibles

```bash
# Ejecutar en modo desarrollo (con recarga automática)
npm run dev

# Construir la aplicación para producción
npm run build

# Previsualizar la versión de producción
npm run preview

# Verificar calidad del código
npm run lint
```

## Cómo Usar la Aplicación

### Primera Vez

1. **Abre la aplicación** en tu navegador (http://localhost:5173)
2. **Regístrate** creando una cuenta nueva
3. **Inicia sesión** con tus credenciales
4. **Recibirás créditos iniciales** para empezar a apostar

### Ver Partidos y Predicciones

1. **Ve a la página "Partidos"** desde el menú lateral
2. **Selecciona un partido** que te interese
3. **Verás la información del partido**:
   - Equipos que juegan
   - Fecha y hora
   - Estadísticas de los equipos
4. **Haz clic en "Ver Predicción"** para obtener la predicción de IA
5. **La predicción mostrará**:
   - Probabilidad de victoria de cada equipo
   - Puntuación esperada
   - Nivel de confianza

### Hacer una Apuesta

1. **Selecciona un partido** de la lista
2. **Elige quién crees que ganará** (equipo local o visitante)
3. **Ingresa la cantidad de créditos** que quieres apostar
4. **Haz clic en "Confirmar Apuesta"**
5. **Los créditos se deducirán** de tu cuenta
6. **La apuesta aparecerá** en tu página de apuestas

### Ver Mis Apuestas

1. **Ve a la página "Apuestas"** desde el menú
2. **Verás todas tus apuestas activas** y pasadas
3. **Cada apuesta muestra**:
   - Partido sobre el que apostaste
   - Tu predicción
   - Cantidad apostada
   - Estado (pendiente, ganada, perdida)
   - Créditos ganados o perdidos

### Ver Mi Historial

1. **Ve a la página "Historial"** desde el menú
2. **Verás un registro completo** de todas tus actividades
3. **Puedes filtrar** por fecha, tipo de apuesta, etc.

### Gestionar Mi Perfil

1. **Ve a la página "Perfil"** desde el menú
2. **Verás tu información**:
   - Nombre de usuario
   - Email
   - Saldo de créditos
   - Estadísticas de apuestas
3. **Puedes actualizar** tu información si es necesario

## Características de la Interfaz

### Diseño Moderno
- Interfaz limpia y fácil de usar
- Diseño responsivo (funciona en móviles y tablets)
- Animaciones suaves para mejor experiencia

### Navegación Intuitiva
- Menú lateral para navegar fácilmente
- Páginas claramente organizadas
- Búsqueda y filtros para encontrar información rápidamente

### Notificaciones
- Notificaciones cuando haces una apuesta
- Alertas cuando ganas o pierdes
- Confirmaciones para acciones importantes

### Actualización en Tiempo Real
- Los partidos se actualizan automáticamente
- Las predicciones se recalculan cuando hay nueva información
- El saldo de créditos se actualiza en tiempo real

## Desarrollo

### Estructura del Código

El código está organizado de forma clara:

- **pages/**: Cada página de la aplicación es un componente separado
- **components/**: Componentes que se reutilizan en múltiples páginas
- **store/**: Estado global de la aplicación (como las apuestas activas)
- **hooks/**: Funciones reutilizables que pueden usarse en cualquier componente

### Agregar una Nueva Página

1. Crea un nuevo archivo en `src/pages/`
2. Crea el componente de la página
3. Agrega la ruta en el router principal
4. Agrega un enlace en el menú de navegación

### Agregar un Nuevo Componente

1. Crea el componente en `src/components/`
2. Exporta el componente
3. Úsalo en las páginas que lo necesiten

## Solución de Problemas

### La aplicación no inicia
- Verifica que Node.js esté instalado: `node --version`
- Asegúrate de haber instalado las dependencias: `npm install`
- Revisa que el puerto 5173 no esté en uso

### No puedo conectarme al backend
- Verifica que el backend esté corriendo en http://localhost:8000
- Revisa la consola del navegador para ver errores específicos
- Asegúrate de que la URL de la API sea correcta

### Los datos no se cargan
- Verifica que el backend esté funcionando correctamente
- Revisa la consola del navegador para errores
- Asegúrate de estar autenticado si es necesario

### La aplicación se ve mal
- Limpia la caché del navegador
- Asegúrate de que todas las dependencias estén instaladas
- Verifica que Tailwind CSS esté configurado correctamente

## Notas Importantes

- **Créditos Virtuales**: Todo el sistema usa créditos virtuales, no dinero real. Es solo para fines educativos y de entretenimiento.

- **Predicciones Educativas**: Las predicciones son generadas por modelos de IA. No son garantía de resultados reales.

- **Desarrollo Local**: Esta aplicación está diseñada para conectarse con el backend local. En producción, necesitarías configurar las URLs correctas.

## Próximos Pasos

Esta aplicación se conecta con:
- **Backend API**: Para obtener predicciones y gestionar apuestas
- **Sistema de Scraping**: Que proporciona los datos para las predicciones

Juntos forman un sistema completo de predicciones y apuestas virtuales NBA.

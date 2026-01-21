# Migraciones de Base de Datos

Este directorio contiene todos los scripts y archivos relacionados con migraciones de base de datos e inicialización de datos.

## 📁 Estructura

```
migrations/
├── scripts/          # Scripts Python para ejecutar migraciones
├── init/             # Scripts de inicialización de datos
├── *.sql            # Archivos SQL de migración
└── README.md        # Este archivo
```

## 📂 Descripción de Carpetas

### `scripts/`
Scripts Python que ejecutan migraciones SQL o crean tablas:

- **`create_tables_neon.py`** - Crea todas las tablas del esquema usando SQLAlchemy
- **`run_2fa_migration.py`** - Ejecuta migración de 2FA, Avatar y Sesiones
- **`run_indexes_migration.py`** - Ejecuta migración de índices de rendimiento
- **`run_migrations.py`** - Ejecuta migraciones de normalización en orden
- **`verify_migration.py`** - Verifica que las migraciones se aplicaron correctamente
- **`migrate_to_neon.py`** - Script de migración a Neon PostgreSQL

### `init/`
Scripts de inicialización de datos (roles, permisos, datos de ejemplo):

- **`init_basic_data.py`** - Inicializa datos básicos del sistema
- **`init_rbac_data.py`** - Inicializa roles y permisos (RBAC)
- **`init_sample_data.py`** - Crea datos de ejemplo para desarrollo
- **`sync_legacy_roles.py`** - Sincroniza roles legacy con el nuevo sistema
- **`load_teams_and_stats.py`** - Carga equipos y estadísticas

### Archivos SQL
Archivos SQL de migración directamente en `migrations/`:

- **`add_2fa_avatar_sessions.sql`** - Migración para 2FA, avatar y sesiones
- **`add_performance_indexes.sql`** - Índices de rendimiento
- **`normalize_espn_schema_3nf.sql`** - Normalización del esquema ESPN a 3NF
- **`normalize_users_by_type.sql`** - Separación de usuarios por tipo
- **`remove_transactions_bet_id_fk.sql`** - Remueve FK de transactions
- **`remove_unused_team_stats_columns.sql`** - Limpia columnas no usadas
- **`init.sql`** - Script de inicialización general
- **`init-schemas.sql`** - Script de inicialización de esquemas

## 🚀 Uso

### Ejecutar desde la raíz del proyecto Backend

#### Crear tablas:
```bash
python migrations/scripts/create_tables_neon.py
```

#### Ejecutar migraciones específicas:
```bash
# Migración de 2FA, Avatar y Sesiones
python migrations/scripts/run_2fa_migration.py

# Migración de índices
python migrations/scripts/run_indexes_migration.py

# Migraciones de normalización
python migrations/scripts/run_migrations.py
```

#### Verificar migraciones:
```bash
python migrations/scripts/verify_migration.py
```

#### Inicializar datos:
```bash
# Datos básicos
python migrations/init/init_basic_data.py

# Roles y permisos (RBAC)
python migrations/init/init_rbac_data.py

# Datos de ejemplo
python migrations/init/init_sample_data.py

# Sincronizar roles legacy
python migrations/init/sync_legacy_roles.py

# Cargar equipos y estadísticas
python migrations/init/load_teams_and_stats.py
```

## 📋 Orden Recomendado de Ejecución

1. **Crear tablas:**
   ```bash
   python migrations/scripts/create_tables_neon.py
   ```

2. **Inicializar RBAC:**
   ```bash
   python migrations/init/init_rbac_data.py
   ```

3. **Ejecutar migraciones (si es necesario):**
   ```bash
   python migrations/scripts/run_migrations.py
   python migrations/scripts/run_2fa_migration.py
   python migrations/scripts/run_indexes_migration.py
   ```

4. **Inicializar datos básicos:**
   ```bash
   python migrations/init/init_basic_data.py
   ```

5. **Cargar datos de ejemplo (opcional, solo desarrollo):**
   ```bash
   python migrations/init/init_sample_data.py
   python migrations/init/load_teams_and_stats.py
   ```

## ⚠️ Notas Importantes

- **Siempre haz backup** de tu base de datos antes de ejecutar migraciones
- Las migraciones SQL son **idempotentes** (pueden ejecutarse múltiples veces)
- Los scripts de inicialización pueden **sobrescribir datos existentes**
- Ejecuta las migraciones en el **orden especificado** para evitar errores
- Verifica que las migraciones se aplicaron correctamente usando `verify_migration.py`

## 🔧 Desarrollo

Al crear nuevas migraciones:

1. Crea el archivo SQL en `migrations/`
2. Crea un script Python en `migrations/scripts/` si necesitas lógica adicional
3. Actualiza este README con la nueva migración
4. Asegúrate de que las rutas en los scripts sean relativas a su nueva ubicación

## 📝 Convenciones

- **Nombres de archivos SQL:** `descripcion_accion.sql` (snake_case)
- **Nombres de scripts Python:** `run_descripcion_migration.py` o `create_descripcion.py`
- **Rutas en scripts:** Usar `Path(__file__).parent.parent` para acceder a `migrations/` desde `scripts/`

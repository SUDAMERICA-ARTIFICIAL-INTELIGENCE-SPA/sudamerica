# Skill: DB Migrate — Sudamérica AI

## Trigger
Ejecutar SIEMPRE que se cree un modelo nuevo (tabla) o se agregue/modifique una columna en un modelo SQLAlchemy existente.

## Regla fundamental
**El ORM NO crea tablas automaticamente en produccion.** No hay Alembic ni auto-migrate. Cada cambio de schema requiere SQL manual en Cloud SQL.

## Procedimiento obligatorio

### 1. Detectar cambios de schema
Cuando se crea o modifica un archivo en `backend/*/app/models/`, verificar:
- Tabla nueva → necesita `CREATE TABLE`
- Columna nueva → necesita `ALTER TABLE ADD COLUMN`
- Columna renombrada → necesita `ALTER TABLE RENAME COLUMN`
- Columna eliminada → necesita `ALTER TABLE DROP COLUMN`

### 2. Actualizar init_db.sql
Asegurar que `backend/init_db.sql` refleje EXACTAMENTE los modelos ORM:
- Nombres de columnas deben coincidir con los `mapped_column` del modelo
- Tipos de datos deben ser compatibles (Float ↔ FLOAT, String(N) ↔ VARCHAR(N), etc.)

### 3. Ejecutar migracion en Cloud SQL
Conectar via Python asyncpg y ejecutar el DDL:

```python
import asyncio, asyncpg

async def migrate():
    conn = await asyncpg.connect(
        host='34.31.63.29', port=5432,
        user='postgres', password='SET_VIA_SECRET_MANAGER',
        database='sudamerica', timeout=10
    )

    # CREATE TABLE / ALTER TABLE aqui
    await conn.execute('''
        CREATE TABLE IF NOT EXISTS nueva_tabla (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            tenant_id UUID NOT NULL REFERENCES tenants(id),
            -- columnas del modelo --
            activo BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
    ''')
    # Indices
    await conn.execute('CREATE INDEX IF NOT EXISTS ix_nueva_tabla_tenant_id ON nueva_tabla(tenant_id);')

    await conn.close()
    print('Migration done!')

asyncio.run(migrate())
```

### 4. Verificar
Despues de migrar, hacer un request al endpoint afectado para confirmar que retorna 200.

## Checklist de validacion
- [ ] Modelo ORM y init_db.sql tienen las mismas columnas con los mismos nombres
- [ ] CREATE TABLE / ALTER TABLE ejecutado en Cloud SQL produccion
- [ ] Endpoint responde 200 (no 500)
- [ ] Indices creados para tenant_id y foreign keys

## Leccion aprendida
Incidente 2026-03-10: Tablas `smart_alerts` y `sales_targets` no existian en prod, columna `activo` faltaba en `revision_humana`. Resultado: 500 en dashboard + CORS errors (el browser reporta CORS cuando el servidor crashea con 500 sin headers).

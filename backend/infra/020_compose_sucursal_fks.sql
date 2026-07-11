-- 020_compose_sucursal_fks.sql
-- Harden sucursal_id references so child rows cannot point to another tenant's branch.

DO $$
BEGIN
    IF to_regclass('public.sucursales') IS NOT NULL
       AND NOT EXISTS (
           SELECT 1
           FROM pg_constraint
           WHERE conname = 'uq_sucursales_tenant_id_id'
       ) THEN
        ALTER TABLE sucursales
            ADD CONSTRAINT uq_sucursales_tenant_id_id UNIQUE (tenant_id, id);
    END IF;
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

DO $$
DECLARE
    _spec record;
    _fk record;
    _table_reg regclass;
    _sucursal_attnum smallint;
BEGIN
    FOR _spec IN
        SELECT *
        FROM (
            VALUES
                ('usuarios', 'fk_usuarios_sucursal_tenant', 'SET NULL'),
                ('leads', 'fk_leads_sucursal_tenant', 'RESTRICT'),
                ('sessions', 'fk_sessions_sucursal_tenant', 'RESTRICT'),
                ('evolution_instances', 'fk_evolution_instances_sucursal_tenant', 'RESTRICT'),
                ('agente_config', 'fk_agente_config_sucursal_tenant', 'RESTRICT'),
                ('ventas', 'fk_ventas_sucursal_tenant', 'RESTRICT'),
                ('comandas', 'fk_comandas_sucursal_tenant', 'RESTRICT'),
                ('mesas', 'fk_mesas_sucursal_tenant', 'RESTRICT'),
                ('reservaciones', 'fk_reservaciones_sucursal_tenant', 'RESTRICT'),
                ('repartidores', 'fk_repartidores_sucursal_tenant', 'RESTRICT'),
                ('delivery_assignments', 'fk_delivery_assignments_sucursal_tenant', 'RESTRICT')
        ) AS spec(table_name, constraint_name, on_delete)
    LOOP
        _table_reg := to_regclass(format('public.%s', _spec.table_name));
        IF _table_reg IS NULL THEN
            CONTINUE;
        END IF;

        SELECT attnum
        INTO _sucursal_attnum
        FROM pg_attribute
        WHERE attrelid = _table_reg
          AND attname = 'sucursal_id'
          AND NOT attisdropped;

        IF _sucursal_attnum IS NULL THEN
            CONTINUE;
        END IF;

        EXECUTE format(
            'UPDATE %1$I AS t
             SET sucursal_id = NULL
             WHERE sucursal_id IS NOT NULL
               AND NOT EXISTS (
                   SELECT 1
                   FROM sucursales s
                   WHERE s.id = t.sucursal_id
                     AND s.tenant_id = t.tenant_id
               )',
            _spec.table_name
        );

        FOR _fk IN
            SELECT conname
            FROM pg_constraint
            WHERE conrelid = _table_reg
              AND confrelid = 'public.sucursales'::regclass
              AND contype = 'f'
              AND array_length(conkey, 1) = 1
              AND conkey[1] = _sucursal_attnum
        LOOP
            EXECUTE format(
                'ALTER TABLE %1$I DROP CONSTRAINT %2$I',
                _spec.table_name,
                _fk.conname
            );
        END LOOP;

        IF NOT EXISTS (
            SELECT 1
            FROM pg_constraint
            WHERE conname = _spec.constraint_name
        ) THEN
            EXECUTE format(
                'ALTER TABLE %1$I
                 ADD CONSTRAINT %2$I
                 FOREIGN KEY (tenant_id, sucursal_id)
                 REFERENCES sucursales (tenant_id, id)
                 ON DELETE %3$s',
                _spec.table_name,
                _spec.constraint_name,
                _spec.on_delete
            );
        END IF;
    END LOOP;
END $$;

# Infra SQL

`001_schema.sql` es un snapshot historico del schema al `2026-03-15`. No debe ejecutarse sobre bases ya migradas.

La fuente de verdad actual para una base vacia es correr, en orden, todos los archivos `NNN_*.sql` de esta carpeta. Los archivos bajo `infra/sql/` quedan como legado/referencia y no reemplazan esta secuencia.

Orden actual:

1. `001_schema.sql`: snapshot base del modelo multi-tenant original.
2. `002_rls_policies.sql`: policies RLS base por `tenant_id`.
3. `003_indexes.sql`: indices principales de lectura y lookup.
4. `004_media_columns.sql`: columnas de media en `ai_conversations`.
5. `005_quality_indexes.sql`: indices de soporte agregados despues del snapshot.
6. `005_reservaciones.sql`: tabla y RLS para reservaciones.
7. `006_schema_catchup.sql`: catch-up historico para restaurant/KDS/admin.
8. `007_password_reset.sql`: reset de password y verificacion email.
9. `008_sucursales.sql`: soporte multi-sucursal y precios por sucursal.
10. `009_reservation_reminders.sql`: flag de recordatorio en reservaciones.
11. `010_suministros.sql`: inventario, suministros y recetas.
12. `011_user_sucursal_hierarchy.sql`: jerarquia usuario-sucursal y FK compuesta inicial.
13. `012_debounce_seconds.sql`: debounce de respuestas IA.
14. `013_mesa_qr.sql`: QR de mesas y lookup publico controlado.
15. `014_delivery_flow.sql`: datos delivery en sucursales y comandas.
16. `015_cloud_api_columns.sql`: soporte Cloud API en `evolution_instances`.
17. `016_delivery_enhancements.sql`: repartidores, assignments y prep time.
18. `017_menu_imports.sql`: importaciones de menu con versionado y RLS.
19. `018_fix_qr_public_rls.sql`: cierre del bypass publico de QR en RLS.
20. `019_rls_delivery.sql`: RLS para `repartidores` y `delivery_assignments`.
21. `020_compose_sucursal_fks.sql`: FKs compuestas `(tenant_id, sucursal_id)`.
22. `021_schema_reconcile.sql`: columnas faltantes para alinear snapshot y ORM.

TODO:

- Si en el futuro se agregan `UPDATE` por SQL puro fuera del ORM, crear triggers `BEFORE UPDATE` para mantener `updated_at = NOW()` a nivel base de datos.

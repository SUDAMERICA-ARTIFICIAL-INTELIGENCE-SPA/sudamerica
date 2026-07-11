# Documentación — Sudamérica AI MVP

Guía rápida para encontrar y mantener la documentación del proyecto.

## Estructura por categoría
- **00_overview**: visión general y estado del proyecto.
  - `AgentSync.md`: objetivos del MVP, criterios de aceptación y seguimiento de sprint.
- **01_architecture**: decisiones y operaciones sobre repositorios/servicios.
  - `microservice-repo-separation.md`: cómo dividir el monorepo en repos independientes con el script de bootstrap.
  - `conversation-flows.md`: diagrama de flujo end-to-end de conversaciones IA (canales, AI_dialer, frontend).
- **02_product**: estrategia de producto y requerimientos funcionales.
  - `sudamerica_resto.md`: plan de reestructuración de Sudamérica AI para el nicho gastronómico.
  - `sudamerica-admin-requirements.md`: especificación del panel interno (Sudamerica Admin).
- **03_integrations**: guías de configuración de proveedores externos.
  - `smtp-mail.md`: configuración de Resend para correo transaccional.
  - `whatsapp_cloud_api_setup.md`: pasos para migrar a WhatsApp Business Cloud API.
- **04_reports**: reportes, guías operativas y capturas de monitoreo/QAs.
  - Ejemplos: `backend_monitoring_critical_guide.md`, `IA_status.md`, `whatsapp_qr.png`.
- **99_archive**: materiales de referencia legados o pesados (PDFs, exportes, etc.).
  - `SUDAMERICA_AI_OFERTA_TECNICA_v3.pdf`, `temp_oferta.*`, `oferta_text.txt`.
  - `logs/`: `log*.txt`, `status*.txt`.
  - `CLAUDE.md`: notas del asistente previas.

## Convenciones rápidas
- Nombra nuevos archivos con prefijos numéricos para mantener el orden (ej. `04_data/`, `05_ops/`).
- Incluye fecha (YYYY-MM-DD) y estado en la cabecera de documentos largos.
- Usa este README para agregar nuevas secciones cuando crezca la documentación.

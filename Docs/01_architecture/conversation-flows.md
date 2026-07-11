# Flujos de Conversación — Sudamérica AI (Canal WhatsApp/Web/Email)

Diagrama de alto nivel para las conversaciones gestionadas por el módulo “Conversaciones IA”. Úsalo como mapa rápido para onboarding y debugging.

```mermaid
flowchart TD
    subgraph Cliente
      A[Mensaje entrante<br/>WhatsApp/Web/Email] -->|Webhook/API| B
    end

    subgraph Canales Service
      B[Ingesta canal<br/>/whatsapp/webhook] --> C[Normaliza mensaje<br/>lead_id, canal, media]
      C --> D{Auto-respuesta?}
      C --> E[Guarda en DB<br/>conversaciones]
      D -->|Sí| F[Encola solicitud a AI_dialer]
      D -->|No| G[Solo registra y notifica UI]
      E --> H[Dispara WebSocket<br/>/ws/{tenant}]
    end

    subgraph AI_dialer
      F --> I[Clasifica intención<br/>& contexto RAG]
      I --> J{Responde?}
      J -->|Sí| K[Genera respuesta<br/>LLM + tools]
      J -->|Escala| L[Marca como humana<br/>flag human_handoff]
      K --> M[Devuelve payload<br/>a Canales]
    end

    subgraph Canales Service Return
      M --> N[Envía reply a WhatsApp<br/>/whatsapp/reply]
      N --> O[Actualiza hilo y WS<br/>thread_update]
    end

    subgraph Frontend (Prospectos)
      H --> P[Lista hilos<br/>ConversationList]
      O --> Q[Chat tiempo real<br/>ConversationChat]
      P -->|Selecciona hilo| Q
      Q --> R[Reply manual<br/>/whatsapp/reply]
      Q --> S[Outbound proactivo<br/>/whatsapp/send-outbound]
      R --> H
      S --> H
    end
```

Notas rápidas
- Auto-respuesta y outbound proactivo se controlan con `/config` (flags `auto_respuesta_whatsapp`, `outbound_proactivo`).
- Los archivos/media viajan por Canales; la UI los muestra con previsualización (imagen/audio/video/documento).
- WebSocket (`/ws/{tenant}?token=...`) mantiene lista y chat en tiempo real; hay reintentos exponenciales si se cae.
- Si el usuario desconecta WhatsApp, el flujo inbound sigue registrando mensajes pero sin respuesta automática hasta reconectar.

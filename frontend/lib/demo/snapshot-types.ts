// Tipos compartidos por el store de snapshots generado (`store.generated.ts`) y
// el resolver. Separado para que el barrel generado importe un tipo estable.

export interface SnapshotEntry {
  /** Ruta RELATIVA que empareja el resolver (puede llevar `{id}` para detalles). */
  serve: string;
  /** Querystring con el que se capturó (informativo; el resolver re-pagina). */
  query: string | null;
  /** Respuesta cruda del backend seedeado (sobre `{data, meta}`, objeto o array). */
  data: unknown;
}

# Decisiones de arquitectura (ADR)

Registro de las decisiones técnicas relevantes de Katea. Cada ADR explica el
contexto, la decisión tomada, las alternativas consideradas y sus consecuencias.

| ADR | Título | Estado |
| --- | --- | --- |
| [ADR-001](ADR-001-persistencia-mysql-pymysql.md) | Persistencia en MySQL 8 con PyMySQL | Aceptada |
| [ADR-002](ADR-002-autenticacion-jwt-bcrypt.md) | Autenticación sin estado con JWT HS256 y bcrypt | Aceptada |

## Convenciones

- Un archivo por decisión, numerado como `ADR-NNN-titulo-corto.md`.
- Los ADR aceptados no se reescriben para cambiar la decisión: si cambia, se
  crea uno nuevo que reemplace al anterior.
- El catálogo de errores de la API está en [errores.md](../errores.md).

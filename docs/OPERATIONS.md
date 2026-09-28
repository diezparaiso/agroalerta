# Operación del ciclo agroclimático

El ciclo completo se ejecuta con:

```bash
PYTHONPATH=backend python -m app.jobs.agroclimatic_cycle
```

También existe `scripts/run_agroclimatic_cycle.sh` como envoltorio para schedulers del sistema.

## Programación con cron

En un servidor donde exista `flock`, una configuración inicial puede ser:

```cron
0 * * * * cd /opt/agroalerta && flock -n /var/run/agroalerta-cycle.lock timeout 15m env PYTHONPATH=backend python -m app.jobs.agroclimatic_cycle >> /var/log/agroalerta-cycle.log 2>&1
```

- Frecuencia: cada hora.
- `flock`: impide ciclos simultáneos en el mismo host.
- `timeout`: evita tareas colgadas indefinidamente.
- El intervalo debe ajustarse a los límites y frecuencia real de las fuentes oficiales.

## Cloud Run Jobs / otros schedulers

El mismo módulo puede ser el comando de un Job gestionado. El scheduler debe proporcionar:

1. ejecución única por intervalo;
2. timeout;
3. reintentos limitados;
4. logs centralizados;
5. secreto/configuración de AEMET, RIA, RAIF y Firebase;
6. persistencia compartida con la API;
7. mecanismo de exclusión si el proveedor permite ejecuciones solapadas.

**Importante:** no debe ejecutarse contra una SQLite efímera de un runner CI. El ciclo necesita la misma base de datos persistente utilizada por la API.

## Orden operativo

`agroclimatic_cycle` mantiene el orden:

**RIA station catalog → RAIF → weather → risk/alerts**

Si una fuente auxiliar falla, el ciclo registra el error y continúa cuando es seguro hacerlo. La meteorología sin evidencia reciente no debe convertirse en riesgo válido.

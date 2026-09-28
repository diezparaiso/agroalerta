# Fuentes oficiales para la capa de datos de AgroAlerta

Fecha de revision: 28/09/2026.

## Objetivo

AgroAlerta no debe calcular el riesgo directamente contra AEMET, RIA, RAIF o MAPA. Las fuentes externas se ingieren y normalizan en una capa de datos interna. El motor agronomico consume solamente contratos internos.

## Flujo

FUENTES OFICIALES -> NORMALIZACION -> CONTEXTO DE PARCELA -> MOTOR DE RIESGO -> ALERTA PARCELA

## 1. RAIF fitosanitario — prioridad alta

La Junta publica un conjunto de datos con el seguimiento de plagas, enfermedades y tratamientos realizado en parcelas de seguimiento. El conjunto tiene licencia CC BY 4.0.

El dataset indica que los datos se remiten semanalmente a RAIF y que, para olivar, la actualizacion publicada es semanal. Los ficheros se distribuyen por cultivo en ZIP/XML y relacionan parcelas y muestreos mediante PROVINCIA, MUNICIPIO y PARCELA.

Cultivos publicados actualmente en el conjunto revisado: algodon, almendro, arroz, cereales de invierno, citricos, fresa, horticolas, olivar, remolacha y vid.

Decisión de arquitectura: RAIF sera una fuente de observaciones de campo. No se debe interpretar automaticamente una observacion RAIF como riesgo de una parcela de cliente sin una regla espacial/territorial explicita.

## 2. RAIF clima — prioridad alta

La Junta publica los datos climaticos de su Red de Estaciones Agroclimaticas. El conjunto revisado indica 79 estaciones, cobertura Andalucia, licencia CC BY 4.0 y variables relacionadas con temperatura, lluvia, humedad, radiacion y viento.

Hay que distinguir datos operativos de estacion y dataset historico/publicado para explotacion masiva.

Decisión de arquitectura: usar la estacion mas adecuada para el contexto de parcela, conservando station_id, distancia a parcela, fecha/hora y calidad/origen.

## 3. RIA / IFAPA — prioridad alta

IFAPA dispone de un servicio REST para consultar la informacion de sus estaciones agroclimaticas, incluyendo identificacion, coordenadas, ultimos datos e historicos.

El repositorio ya contiene RiaIfapaClient.

Pendiente: validar el contrato real de cada endpoint y normalizar sus variables a nuestro modelo meteorologico comun. No duplicar logica en el motor de enfermedad.

## 4. AEMET — prioridad media/alta

AEMET OpenData ofrece prediccion municipal diaria y horaria, ademas de otros productos meteorologicos. El repositorio ya dispone de AemetClient.

Pendiente: mantener la API key fuera del repositorio y adaptar el conector a los productos realmente necesarios para cada regla.

Importante: AEMET anuncio que las API keys sin fecha de expiracion dejaran de ser validas a partir del 15/10/2026. La gestion de secretos debe contemplar renovacion.

## 5. SIGPAC — prioridad critica para la geolocalizacion agricola

SIGPAC es la referencia administrativa para identificar parcelas y recintos agricolas. Andalucia publico el SIGPAC correspondiente a 2026.

Objetivo en AgroAlerta:
1. El usuario introduce o selecciona la ubicacion de su finca.
2. AgroAlerta intenta identificar el recinto agricola correspondiente.
3. Se guarda el identificador geoespacial estable disponible.
4. Las fuentes territoriales se relacionan con la parcela.

Esto es mas robusto que trabajar indefinidamente con latitud/longitud + municipio.

Pendiente: validar el servicio geoespacial de consulta/descarga que utilizaremos y sus condiciones de uso antes de incorporarlo al codigo.

## 6. IDEAndalucia / DERA / OGC — prioridad media

La infraestructura geografica de Andalucia ofrece servicios interoperables WMS y WFS. DERA mantiene capas geograficas de referencia y REDIAM dispone tambien de servicios OGC.

Uso previsto: contexto espacial, no calculo fitosanitario directo. Ejemplos: hidrografia, relieve, limites administrativos y otras capas ambientales relevantes.

La aplicacion debe evitar descargar capas enormes si basta con una consulta espacial sobre el area de interes.

## 7. MAPA — productos fitosanitarios

El catalogo de productos debe mantenerse separado del motor de riesgo.

Flujo correcto: RIESGO -> ENFERMEDAD/PLAGA -> CATALOGO OFICIAL VIGENTE -> PRODUCTOS AUTORIZADOS -> INFORMACION ORIENTATIVA -> CONSULTAR SIEMPRE LA ETIQUETA OFICIAL.

No debemos recomendar un producto unicamente porque aparezca en una base historica.

## Modelo de datos interno

Todas las fuentes meteorologicas y fitosanitarias deben converger en contratos internos similares a:

- WeatherObservation
- WeatherForecast
- PestObservation
- DiseaseObservation
- AgroclimaticStation
- ParcelGeography
- SourceRecord

Cada registro debe conservar fuente, identificador externo, fecha/hora de observacion, fecha/hora de ingestion, geometria o referencia espacial cuando exista, calidad/estado del dato y version o fecha del dataset.

## Regla fundamental para el motor

El motor no debe preguntar que dice una fuente concreta. Debe preguntar que evidencia disponible afecta a esta parcela y con que distancia, fecha, calidad y confianza.

Combinacion prevista: meteorologia observada + prediccion + observaciones RAIF + telemetria propia + contexto espacial + reglas agronomicas = riesgo contextual de parcela.

## Orden de implementacion

### Fase A — ahora
- catalogo de fuentes;
- contratos internos;
- correccion de la ingesta meteorologica;
- trazabilidad de fuente;
- seleccion de estacion cercana.

### Fase B
- ingestion real RAIF;
- normalizacion de observaciones;
- asociacion territorial;
- historico de evidencias.

### Fase C
- SIGPAC/parcela geografica;
- consultas espaciales;
- alertas por proximidad/zona;
- mapa de incidencia.

### Fase D
- modelos agronomicos por cultivo/enfermedad;
- combinacion de observaciones + meteorologia + telemetria;
- calibracion de confianza.

## Fuentes verificadas en la revision

- RAIF: datos de seguimiento fitosanitario.
- RAIF: datos climaticos de estaciones agroclimaticas.
- IFAPA RIA: datos abiertos y API REST.
- AEMET OpenData.
- IDEAndalucia / DERA / servicios OGC.
- SIGPAC 2026.

Las URL y endpoints concretos de descarga/consulta deben permanecer centralizados en los conectores y no repartidos por el dominio.

## Implementacion realizada: RAIF

El conector `backend/app/connectors/raif_client.py` descarga el recurso ZIP configurado para cada cultivo, abre sus XML y normaliza registros a un contrato interno.

La primera fuente configurada es **RAIF Olivar**. El recurso oficial publicado por la Junta se actualiza semanalmente para olivar y relaciona parcelas y muestreos mediante PROVINCIA, MUNICIPIO y PARCELA.

Las evidencias se almacenan en `source_records`, conservando:

- fuente;
- identificador externo;
- fecha de observacion cuando puede interpretarse;
- provincia;
- municipio;
- referencia de parcela;
- payload original normalizado;
- fecha de ingesta.

La descarga queda parametrizada mediante `RAIF_OLIVAR_URL`, de modo que si la Junta cambia el recurso no hay que modificar el dominio.

La ingesta se ejecuta como job externo mediante `ingest_raif("olivar")`. No se expone como endpoint publico para evitar que una peticion HTTP pueda disparar descargas masivas.

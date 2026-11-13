# Portafolios de inversión — Django

Implementación de la prueba técnica de Abaqus. Modela dos portafolios con 17 activos, importa el Excel original, expone consultas REST y compara gráficamente su evolución. Desarrollo con asistencia de IA; las decisiones, supuestos y validaciones se documentan para su revisión.

## Ejecución local en Windows

Python 3.12 o superior; probado con Python 3.14.7. Django 5.2.19 y openpyxl 3.1.5.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py import_portfolios data/datos.xlsx
.\.venv\Scripts\python.exe manage.py test -v 2
.\.venv\Scripts\python.exe verify_real_data.py
.\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000 --noreload
```

Abrir http://127.0.0.1:8000/ . No requiere Node, servicios externos ni bibliotecas de gráficos descargadas desde CDN. SQLite queda en `db.sqlite3`, recreable con migraciones e importación. En macOS/Linux usar `.venv/bin/python` en lugar del ejecutable de Windows.

## Respuestas y trazabilidad del enunciado

| Punto | Implementación |
|---|---|
| 1. Modelar activos, portafolios, precios y posiciones | `portfolios/models.py` y migración versionada |
| 2. ETL desde Excel a base de datos | `services.parse_workbook`, `services.import_workbook`, comando `import_portfolios` |
| 3. Cantidades iniciales | `Position.quantity`; API `/api/portfolios/<id>/initial/`; `outputs/cantidades_iniciales.csv` |
| 4. Valores y pesos entre fechas usando ORM | `selectors.portfolio_evolution`; API `/api/evolution/` |
| 5. Vista consumiendo API y gráficos | `views.py`, template y `static/portfolios/dashboard.js`: líneas de valor y áreas apiladas de pesos |
| 6. Bonus de organización | Separación de modelos, servicios de escritura, selectores de lectura, API y vista, inspirada en HackSoft |

## API

Solo lectura, JSON, fechas inclusivas. Los importes y pesos se transmiten como cadenas decimales para evitar conversión implícita a float; el navegador convierte a Number únicamente para dibujar.

- `GET /api/portfolios/`: IDs, nombres, fecha y valor inicial.
- `GET /api/portfolios/1/initial/`: 17 cantidades y pesos iniciales.
- `GET /api/evolution/?fecha_inicio=2022-02-15&fecha_fin=2023-02-16`: ambos portafolios, un punto por fecha disponible con `date`, `value` y diccionario `weights`.
- Agregar `&portfolio_id=1` para filtrar uno.
- Fechas inválidas, orden invertido, inicio anterior a constitución o datos diarios incompletos: HTTP 400 con mensaje.
- Portafolio inexistente: 404. Método POST: 405. Rango sin observaciones: 200 con listas vacías, nunca un valor ficticio cero.

Los IDs de una base nueva son 1 y 2, pero un cliente debe obtenerlos del listado. Las consultas de evolución son tres, independientemente del número de fechas: portafolios, posiciones con activos y precios. Los cálculos usan registros ORM; la API no lee el Excel.

## Modelo y supuestos

`Asset` tiene muchos `Price` (únicos por activo/fecha). `Portfolio` tiene muchas `Position` (únicas por portafolio/activo). Una posición conserva peso inicial y cantidad. Valor por activo, peso vigente y valor total se derivan; no se persisten copias que puedan desincronizarse.

1. Inicio 15/02/2022, USD 1.000.000.000 en cada portafolio, según el enunciado.
2. `cantidad = peso_inicial × valor_inicial / precio_inicial`. Se permiten fracciones y posiciones cero.
3. Cantidades constantes: **no** se rebalancea diariamente para recuperar el peso inicial.
4. `monto = cantidad × precio`; `valor = suma(montos)`; `peso = monto / valor`.
5. Se utilizan los precios entregados sin inferir ajustes por dividendos, comisiones, tipo de cambio o aportes/retiros. No se rellena una celda faltante. Una fecha completamente ausente no se inventa: se devuelven las observaciones disponibles.
6. Se enlazan activos **por nombre**, no por posición de columnas: las hojas originales tienen órdenes distintos. Se ignoran filas totalmente vacías, incluso con formato.
7. Pesos iniciales redondeados a 12 decimales para eliminar residuos binarios de Excel, verificados en [0,1] y sumando 1 por portafolio. Precios positivos con hasta 8 decimales; cantidades guardadas a 12.
8. La carga valida el archivo completo antes de escribir; las escrituras son atómicas. Reimportar reemplaza precios del universo importado y actualiza las dos carteras gestionadas, sin duplicados. No es un importador general multiusuario o multifuente.

## Verificación y límites

`manage.py test` incluye casos de cálculo manual con dos activos de peso no nulo, columnas desordenadas, importación repetida, rollback, datos inválidos, validaciones HTTP, rangos y número de consultas. `verify_real_data.py` compara todas las fechas de ambos portafolios con un cálculo independiente desde Excel y exporta respuestas. Consultar el informe JSON generado para resultados y tolerancias reales.

SQLite no representa los decimales con la misma exactitud que PostgreSQL NUMERIC: aunque se usa `Decimal` en Python y `DecimalField`, hay conversión numérica en SQLite. La comparación independiente admite menos de USD 0,001 de diferencia en valores cercanos a mil millones. No confundir esa tolerancia con una garantía de precisión monetaria en producción. Para producción se migraría a PostgreSQL, se probaría nuevamente la exactitud y se agregarían autenticación, autorización, configuración segura y límites operacionales.

El servidor de desarrollo, la clave local y `DEBUG` son exclusivamente para demo local. No publicar así. El código y sus resultados se publican para revisión técnica. La configuración incluida es de desarrollo local.

## Fuentes

- Enunciado: https://abaquscl.notion.site/Pregunta-t-cnica-Python-d00b3f926b0845edaec7f198919c83d4
- Guía sugerida: https://github.com/HackSoftware/Django-Styleguide
- DecimalField: https://docs.djangoproject.com/en/5.2/ref/models/fields/#decimalfield
- Transacciones: https://docs.djangoproject.com/en/5.2/topics/db/transactions/

La guía sugerida se adopta en su separación de responsabilidades; no se afirma implementar todas sus convenciones ni se incorpora DRF innecesariamente para estos tres endpoints GET.

La serie completa outputs/evolucion.json se genera al ejecutar verify_real_data.py y no se versiona. Los datos originales y el informe compacto de validacion permiten reproducirla. El workflow Django checks ejecuta pruebas e importacion en Python3.12 y3.14; su resultado debe consultarse en GitHub Actions.

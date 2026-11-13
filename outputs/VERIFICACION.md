# Verificación ejecutada el 12/11/2026

- Python 3.14.7, Django 5.2.19, openpyxl 3.1.5, SQLite local.
- Migración inicial aplicada; `manage.py check` sin incidencias y `makemigrations --check --dry-run` sin cambios pendientes.
- 14 tests Django aprobados, incluyendo cálculo manual, persistencia, rollback, importación repetida, validación de datos, fechas y estados HTTP, y tres consultas ORM por evolución.
- Excel real cargado: 17 activos, 2 portafolios, 34 posiciones, 367 fechas y 6.239 precios.
- Cálculo independiente desde el Excel comparado con API para 734 combinaciones de portafolio/fecha y sus 17 pesos. Diferencia máxima de valor: 0,00000090004354545669181748564 USD; de peso: aproximadamente 0,0000000000005. Ver informe JSON reproducible.
- Vista comprobada en navegador: carga completa de 367 fechas, líneas de ambos valores y composición apilada; rango de dos días; un solo día; error visible al invertir fechas. Se restauró el rango completo.
- Captura real: `demo_verificada.png`. Servidor de desarrollo local iniciado en 127.0.0.1:8000; su continuidad depende del proceso y del equipo.
- No se realizaron pruebas de despliegue, carga, auditoría de accesibilidad completa, PostgreSQL o seguridad de producción. La primera entrega se realizó por enlace privado de Drive; este repositorio facilita la revisión solicitada.

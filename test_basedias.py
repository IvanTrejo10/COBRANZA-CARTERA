# -*- coding: utf-8 -*-
"""Pruebas del comparativo y del motor de Base Días (sin conexión a BD)."""
import io
import sys
sys.path.insert(0, '/root/proyecto')
import pandas as pd
import procesos_basedias as pb

ok = True
def check(cond, msg):
    global ok
    print(('  OK   ' if cond else '  FALLA') + ' ' + msg)
    if not cond:
        ok = False

# ---------- Caso 1: archivos con diferencias conocidas ----------
# "Página": headers con acentos, números con comas, fechas dd/mm/yyyy, un registro extra (1004)
csv_pagina = (
    "Sucursal,Numero,Nombre,Categoría,Vencido,Total,Fecha Activación\n"
    "CENTRO,1001,MARIA LOPEZ,Oro,\"1,250.50\",\"10,000.00\",01/02/2024\n"
    "CENTRO,1002,JUAN PEREZ,Plata,0.00,\"5,500.25\",15/03/2024\n"
    "NORTE,1003,ANA RUIZ,Bronce,300.00,\"2,000.00\",20/04/2024\n"
    "NORTE,1004,SOLO PAGINA,Oro,10.00,100.00,01/01/2024\n"
).encode('utf-8-sig')

# "Base de datos": sin acentos en headers, números float, 1005 solo aquí, 1002 con Total diferente
df_bd = pd.DataFrame({
    "Sucursal": ["CENTRO", "CENTRO", "NORTE", "SUR"],
    "Numero": [1001, 1002, 1003, 1005],
    "Nombre": ["MARIA LOPEZ", "JUAN PEREZ", "ANA RUIZ", "SOLO BD"],
    "Categoria": ["Oro", "Plata", "Bronce", "Plata"],
    "Vencido": [1250.5, 0.0, 300.0, 77.0],
    "Total": [10000.0, 5999.99, 2000.0, 500.0],
    "Fecha Activación": ["01/02/2024", "15/03/2024", "20/04/2024", "05/05/2024"],
})

class ArchivoFalso(io.BytesIO):
    def __init__(self, data, name):
        super().__init__(data)
        self.name = name

df_pagina = pb.leer_archivo_tabla(ArchivoFalso(csv_pagina, "pagina.csv"))
check(len(df_pagina) == 4, "lee CSV de la página (utf-8-sig, comas de miles)")

r = pb.comparar_tablas(df_pagina, df_bd, etiqueta_a="Página", etiqueta_b="Base de datos")
check(r["llave_usada"].lower() == "numero", f"detecta la llave sola ({r['llave_usada']})")
check(r["resumen"]["Registros en común"] == 3, "3 registros en común")
check(r["resumen"]["Solo en Página"] == 1 and r["solo_a"]["Numero"].tolist() == ['1004'], "detecta el registro que solo está en la página (1004)")
check(r["resumen"]["Solo en Base de datos"] == 1 and str(r["solo_b"]["Numero"].tolist()[0]) == '1005', "detecta el registro que solo está en la BD (1005)")
difs = r["diferencias"]
check(len(difs) == 1 and difs.iloc[0]["Columna"] == "Total" and difs.iloc[0]["Llave"] == '1002',
      f"detecta la única celda diferente (1002 · Total): {difs.to_dict('records')}")
check(not r["identicos"], "marca que NO son idénticos")
check("Categoría" not in r["columnas_solo_a"], "empareja Categoría vs Categoria (acentos)")

# ---------- Caso 2: mismos datos con formato distinto -> idénticos ----------
df_bd2 = df_bd[df_bd["Numero"] != 1005].copy()
df_pag2 = df_pagina[df_pagina["Numero"] != '1004'].copy()
df_bd2.loc[df_bd2["Numero"] == 1002, "Total"] = 5500.25
r2 = pb.comparar_tablas(df_pag2, df_bd2, etiqueta_a="Página", etiqueta_b="BD")
check(r2["identicos"], "mismos datos con distinto formato (1,250.50 vs 1250.5, 1001 vs '1001') -> idénticos")

# ---------- Caso 3: llave repetida ----------
df_dup_a = pd.DataFrame({"Numero": [1, 1, 2], "Total": [10, 20, 30]})
df_dup_b = pd.DataFrame({"Numero": [1, 1, 2], "Total": [10, 25, 30]})
r3 = pb.comparar_tablas(df_dup_a, df_dup_b)
check(len(r3["avisos"]) >= 1 and len(r3["diferencias"]) == 1, "llaves repetidas: avisa y aun así compara en orden")

# ---------- Caso 4: tolerancia ----------
r4 = pb.comparar_tablas(pd.DataFrame({"Numero": [1], "Total": [100.004]}),
                        pd.DataFrame({"Numero": [1], "Total": [100.0]}))
check(r4["identicos"], "diferencia de 0.004 dentro de la tolerancia 0.01")

# ---------- Reporte Excel ----------
datos_xlsx = pb.reporte_comparativo_bytes(r)
check(datos_xlsx[:2] == b'PK' and len(datos_xlsx) > 3000, "reporte Excel del comparativo se genera")
hojas = pd.ExcelFile(io.BytesIO(datos_xlsx)).sheet_names
check(hojas[0] == "Resumen" and "Diferencias" in hojas, f"hojas del reporte: {hojas}")

# ---------- csv_bytes y kpis ----------
check(pb.csv_bytes(df_bd)[:3] == b'\xef\xbb\xbf', "CSV con BOM para Excel")
k = pb.kpis_base_dias(df_bd)
check(round(k.get("💰 Total"), 2) == 18499.99 and round(k.get("🔴 Vencido"), 2) == 1627.5, f"KPIs correctos: {k}")

# ---------- Servidores pendientes no truenan el proceso ----------
import datos_basedias as d
srv_falso = {'nombre': 'MARCA DE PRUEBA', 'motor': 'mysql', 'host': 'PENDIENTE_HOST',
             'db': 'PENDIENTE_BD', 'query': 'NV_VALE', 'archivo': 'prueba_{fecha}'}
d.SERVIDORES_BASE_DIAS.append(srv_falso)
try:
    logs = []
    res, conteos = pb.proceso_base_dias("2026-07-16", ["MARCA DE PRUEBA"], "u", "p", log=logs.append)
    check(res == {} and "⚠️" in conteos[0]["Estado"], "marca sin servidor configurado: avisa sin tronar")
finally:
    d.SERVIDORES_BASE_DIAS.remove(srv_falso)
check(all(pb.servidor_configurado(s) for s in d.SERVIDORES_BASE_DIAS),
      "las 4 marcas reales ya tienen servidor configurado")

print()
print('RESULTADO FINAL:', 'TODO OK' if ok else 'HAY FALLAS')
sys.exit(0 if ok else 1)

from django.shortcuts import render, redirect
from django.core.files.storage import default_storage
from django.http import HttpResponse
import pandas as pd
import os
import tempfile
import traceback
import xlsxwriter

def extraer_numero(texto):
    try:
        return int(''.join([c for c in str(texto) if c.isdigit()]))
    except:
        return 0

def detectar_solapamientos(diseño):
    conflictos = []
    for i in range(len(diseño)):
        try:
            inicio_i = int(diseño[i]['inicio'])
            longitud_i = int(diseño[i]['longitud'])
            fin_i = inicio_i + longitud_i - 1
            nombre_i = str(diseño[i]['nombre']).strip()
        except:
            continue
        for j in range(i + 1, len(diseño)):
            try:
                inicio_j = int(diseño[j]['inicio'])
                longitud_j = int(diseño[j]['longitud'])
                fin_j = inicio_j + longitud_j - 1
                nombre_j = str(diseño[j]['nombre']).strip()
            except:
                continue
            if max(inicio_i, inicio_j) <= min(fin_i, fin_j):
                conflictos.append(f'"{nombre_i}" se superpone con "{nombre_j}" 🔴')
    return conflictos

def home(request):
    mensaje = None
    preview = []
    conflictos = []
    request.session["bloques_xlsx"] = []
    request.session["rutas_excel"] = []
    request.session["nombre_base"] = None
    request.session["diseño"] = []

    if request.method == 'POST' and request.FILES.get('archivo'):
        archivo = request.FILES['archivo']
        path = default_storage.save(archivo.name, archivo)
        full_path = default_storage.path(path)
        request.session["nombre_base"] = os.path.splitext(archivo.name)[0]

        diseño = []
        excel = request.FILES.get('excel_diseno')

        if excel:
            try:
                df_diseño = pd.read_excel(excel)
                columnas = df_diseño.columns.str.lower()
                if {"campo", "posicion", "caracter"}.issubset(set(columnas)):
                    for _, fila in df_diseño.iterrows():
                        nombre = str(fila.get("campo", "")).strip()
                        inicio = extraer_numero(fila.get("posicion"))
                        longitud = extraer_numero(fila.get("caracter"))
                        if nombre and longitud > 0:
                            diseño.append({"nombre": nombre, "inicio": inicio, "longitud": longitud})
                else:
                    mensaje = "⚠️ El Excel no contiene las columnas necesarias."
                    return render(request, 'home.html', {"mensaje": mensaje})
            except Exception as e:
                mensaje = f"⚠️ Error al leer Excel: {str(e)}"
                return render(request, 'home.html', {"mensaje": mensaje})
        else:
            mensaje = "⚠️ No se adjuntó Excel de diseño."
            return render(request, 'home.html', {"mensaje": mensaje})

        conflictos = detectar_solapamientos(diseño)
        if conflictos:
            resumen = conflictos[:5]
            if len(conflictos) > 5:
                resumen.append(f"...y {len(conflictos) - 5} más.")
            mensaje = "⚠️ Superposición de campos detectada."
            return render(request, 'home.html', {"mensaje": mensaje, "conflictos": resumen})

        request.session["diseño"] = diseño
        bloques = []
        rutas_excel = []
        total_lineas = 0

        with open(full_path, "r", encoding="utf-8") as f:
            lineas = f.readlines()
            total_lineas = len(lineas)

        BLOQUE_SIZE = 20000
        total_bloques = (total_lineas + BLOQUE_SIZE - 1) // BLOQUE_SIZE

        for b in range(total_bloques):
            nombre = f"{request.session['nombre_base']}_bloque{b+1}.xlsx"
            bloques.append((b+1, nombre))

            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=f"_bloque{b+1}.xlsx")
            workbook = xlsxwriter.Workbook(tmp.name, {'constant_memory': True})
            worksheet = workbook.add_worksheet()

            for col_index, campo in enumerate(diseño):
                worksheet.write(0, col_index, campo["nombre"])

            inicio = b * BLOQUE_SIZE
            fin = min(inicio + BLOQUE_SIZE, total_lineas)

            for fila_excel, i in enumerate(range(inicio, fin), start=1):
                linea = lineas[i].rstrip('\n')
                largo = len(linea)
                valores = []
                for campo in diseño:
                    ini = campo["inicio"]
                    fin_campo = ini + campo["longitud"]
                    valor = linea[ini:fin_campo].strip() if fin_campo <= largo else ""
                    valores.append(valor)
                for col_index, val in enumerate(valores):
                    worksheet.write(fila_excel, col_index, val)

            workbook.close()
            rutas_excel.append(tmp.name)

            if b < 1:
                fila_preview = []
                for campo in diseño:
                    ini = campo["inicio"]
                    fin_campo = ini + campo["longitud"]
                    valor = lineas[inicio][ini:fin_campo].strip() if fin_campo <= len(lineas[inicio]) else ""
                    fila_preview.append(valor)
                preview.append(dict(zip([c["nombre"] for c in diseño], fila_preview)))

        request.session["bloques_xlsx"] = bloques
        request.session["rutas_excel"] = rutas_excel

        mensaje = f"✅ {total_lineas:,} líneas procesadas. Archivos generados en {total_bloques} bloques."

        return render(request, 'home.html', {
            "mensaje": mensaje,
            "preview": preview,
            "bloques": bloques
        })

    return render(request, 'home.html')

from django.http import FileResponse

def descargar_directo(request, bloque_id):
    rutas = request.session.get("rutas_excel")
    bloques = request.session.get("bloques_xlsx")

    try:
        bloque_id = int(bloque_id)
    except:
        return HttpResponse("⚠️ Bloque inválido.")

    if not rutas or bloque_id < 1 or bloque_id > len(rutas):
        return HttpResponse("⚠️ Archivo no disponible.")

    ruta = rutas[bloque_id - 1]
    nombre = bloques[bloque_id - 1][1] if bloques else f"bloque{bloque_id}.xlsx"
    return FileResponse(open(ruta, "rb"), as_attachment=True, filename=nombre)

def eliminar_preview(request):
    request.session["bloques_xlsx"] = []
    request.session["rutas_excel"] = []
    request.session["nombre_base"] = None
    request.session["diseño"] = []
    return redirect('home')


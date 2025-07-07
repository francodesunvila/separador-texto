from django.shortcuts import render, redirect
from django.core.files.storage import default_storage
from django.http import HttpResponse, FileResponse
import pandas as pd
import os
import tempfile
import traceback
import csv

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
    request.session["bloques_csv"] = []

    if request.method == 'POST' and request.FILES.get('archivo'):
        archivo = request.FILES['archivo']
        path = default_storage.save(archivo.name, archivo)
        full_path = default_storage.path(path)

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
                    mensaje = "✅ Diseño importado desde Excel correctamente."
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

        # Procesar por bloques
        BLOCK_SIZE = 100000
        block_num = 1
        line_count = 0
        writers = {}
        archivos = []
        headers = [campo["nombre"] for campo in diseño]

        with open(full_path, "r", encoding="utf-8") as f:
            for linea in f:
                if line_count % BLOCK_SIZE == 0:
                    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=f"_part{block_num}.csv", mode="w", encoding="utf-8", newline="")
                    writer = csv.writer(tmp)
                    writer.writerow(headers)
                    writers[block_num] = writer
                    archivos.append((block_num, tmp.name, os.path.splitext(archivo.name)[0] + f"_bloque{block_num}.csv"))
                    if block_num == 1:
                        preview = []
                    block_num += 1
                    file_obj = tmp
                linea = linea.rstrip('\n')
                largo = len(linea)
                fila = []
                for campo in diseño:
                    ini = campo["inicio"]
                    fin = ini + campo["longitud"]
                    valor = linea[ini:fin].strip() if fin <= largo else ""
                    fila.append(valor)
                writers[block_num - 1].writerow(fila)
                if line_count < 20:
                    preview.append(dict(zip(headers, fila)))
                line_count += 1

        for _, path, _ in archivos:
            try:
                open(path).close()
            except:
                pass

        request.session["bloques_csv"] = archivos
        mensaje = f"✅ {line_count:,} líneas procesadas en {len(archivos)} bloques CSV."

    return render(request, 'home.html', {"mensaje": mensaje, "preview": preview, "bloques": request.session.get("bloques_csv", [])})

def descargar_excel(request):
    bloque_id = request.GET.get("bloque")
    archivos = request.session.get("bloques_csv", [])
    for b, path, nombre in archivos:
        if str(b) == str(bloque_id):
            if not os.path.exists(path):
                return HttpResponse("⚠️ No se encontró el archivo para descargar.")
            return FileResponse(open(path, "rb"), as_attachment=True, filename=nombre)
    return HttpResponse("⚠️ Bloque no encontrado.")

def eliminar_preview(request):
    request.session["bloques_csv"] = []
    return redirect('home')
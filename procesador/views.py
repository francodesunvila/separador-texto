from django.shortcuts import render, redirect
from django.core.files.storage import default_storage
from django.http import HttpResponse, FileResponse
import pandas as pd
import os
import tempfile
import traceback
from openpyxl import Workbook

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
    request.session["ruta_excel"] = None
    request.session["nombre_excel"] = None

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

        # Crear Excel línea por línea
        wb = Workbook()
        ws = wb.active
        ws.append([campo["nombre"] for campo in diseño])

        count = 0
        with open(full_path, "r", encoding="utf-8") as f:
            for linea in f:
                linea = linea.rstrip('\n')
                largo = len(linea)
                fila = []
                for campo in diseño:
                    ini = campo["inicio"]
                    fin = ini + campo["longitud"]
                    valor = linea[ini:fin].strip() if fin <= largo else ""
                    fila.append(valor)
                ws.append(fila)

                if count < 20:
                    preview.append(dict(zip([c["nombre"] for c in diseño], fila)))
                count += 1

        # Guardar Excel final
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
        wb.save(tmp.name)
        request.session["ruta_excel"] = tmp.name
        request.session["nombre_excel"] = os.path.splitext(archivo.name)[0] + ".xlsx"

        mensaje = f"✅ {count:,} líneas procesadas correctamente."

    return render(request, 'home.html', {"mensaje": mensaje, "preview": preview})

def descargar_excel(request):
    import traceback
    try:
        ruta = request.session.get("ruta_excel")
        nombre = request.session.get("nombre_excel", "resultado.xlsx")

        if not ruta or not os.path.exists(ruta):
            print(f"⚠️ Archivo no encontrado: {ruta}")
            return HttpResponse("⚠️ No se encontró el archivo para descargar.")

        return FileResponse(open(ruta, "rb"), as_attachment=True, filename=nombre)

    except Exception as e:
        print("⚠️ Error en descarga_excel:", traceback.format_exc())
        return HttpResponse("⚠️ No se pudo generar el archivo Excel.")

def eliminar_preview(request):
    request.session["ruta_excel"] = None
    request.session["nombre_excel"] = None
    return redirect('home')
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
    request.session["bloques_xlsx"] = []
    request.session["ruta_txt"] = None
    request.session["nombre_base"] = None
    request.session["diseño"] = []

    if request.method == 'POST' and request.FILES.get('archivo'):
        archivo = request.FILES['archivo']
        path = default_storage.save(archivo.name, archivo)
        full_path = default_storage.path(path)
        request.session["ruta_txt"] = full_path
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
        total_lineas = 0

        with open(full_path, "r", encoding="utf-8") as f:
            for i, linea in enumerate(f):
                if i < 20:
                    fila = []
                    largo = len(linea.rstrip('\n'))
                    for campo in diseño:
                        ini = campo["inicio"]
                        fin = ini + campo["longitud"]
                        valor = linea[ini:fin].strip() if fin <= largo else ""
                        fila.append(valor)
                    preview.append(dict(zip([c["nombre"] for c in diseño], fila)))
                total_lineas += 1

        BLOQUE_SIZE = 50000
        total_bloques = (total_lineas + BLOQUE_SIZE - 1) // BLOQUE_SIZE

        for b in range(total_bloques):
            nombre = f"{request.session['nombre_base']}_bloque{b+1}.xlsx"
            bloques.append((b+1, nombre))

        request.session["bloques_xlsx"] = bloques

        mensaje = f"✅ {total_lineas:,} líneas detectadas. División en {total_bloques} bloques."

        return render(request, 'home.html', {
            "mensaje": mensaje,
            "preview": preview,
            "bloques": bloques
        })

    return render(request, 'home.html')
def descargar_excel(request):
    bloque_id = request.GET.get("bloque")
    ruta = request.session.get("ruta_txt")
    diseño = request.session.get("diseño")
    nombre_base = request.session.get("nombre_base", "resultado")

    if not ruta or not os.path.exists(ruta):
        return HttpResponse("⚠️ Archivo TXT no encontrado.")
    if not diseño:
        return HttpResponse("⚠️ Diseño no disponible.")
    if not bloque_id:
        return HttpResponse("⚠️ Bloque no especificado.")

    try:
        bloque = int(bloque_id)
    except:
        return HttpResponse("⚠️ Bloque inválido.")

    BLOQUE_SIZE = 100000
    inicio = (bloque - 1) * BLOQUE_SIZE
    fin = inicio + BLOQUE_SIZE

    try:
        wb = Workbook(write_only=True)
        ws = wb.create_sheet()
        ws.append([campo["nombre"] for campo in diseño])

        with open(ruta, "r", encoding="utf-8") as f:
            for i, linea in enumerate(f):
                if i < inicio:
                    continue
                if i >= fin:
                    break
                linea = linea.rstrip('\n')
                largo = len(linea)
                fila = []
                for campo in diseño:
                    ini = campo["inicio"]
                    fin_campo = ini + campo["longitud"]
                    valor = linea[ini:fin_campo].strip() if fin_campo <= largo else ""
                    fila.append(valor)
                ws.append(fila)

        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=f"_bloque{bloque}.xlsx")
        wb.save(tmp.name)
        nombre_archivo = f"{nombre_base}_bloque{bloque}.xlsx"
        return FileResponse(open(tmp.name, "rb"), as_attachment=True, filename=nombre_archivo)

    except Exception as e:
        print("⚠️ Error generando Excel:", traceback.format_exc())
        return HttpResponse("⚠️ No se pudo generar el archivo Excel.")

def eliminar_preview(request):
    request.session["bloques_xlsx"] = []
    request.session["ruta_txt"] = None
    request.session["nombre_base"] = None
    request.session["diseño"] = []
    return redirect('home')
from django.shortcuts import render, redirect
from django.core.files.storage import default_storage
from django.http import HttpResponse, FileResponse
import pandas as pd
import os
import tempfile
import traceback
import xlsxwriter
import re  # Para limpiar caracteres invisibles

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

def limpiar_valor(val):
    return re.sub(r'[\x00-\x08\x0B-\x1F\x7F]', '', val)
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

        # ✅ Leer preview + contar todas las líneas correctamente
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
            total_lineas = i + 1

        BLOQUE_SIZE = 5000
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
def descargar_directo(request, bloque_id):
    import re

    ruta = request.session.get("ruta_txt")
    diseño = request.session.get("diseño")
    nombre_base = request.session.get("nombre_base", "resultado")
    bloques = request.session.get("bloques_xlsx")

    try:
        bloque_id = int(bloque_id)
    except:
        return HttpResponse("⚠️ Bloque inválido.")

    if not ruta or not os.path.exists(ruta):
        return HttpResponse("⚠️ Archivo TXT no encontrado.")
    if not diseño or not bloques or bloque_id < 1 or bloque_id > len(bloques):
        return HttpResponse("⚠️ Información de bloque no disponible.")

    BLOQUE_SIZE = 5000
    inicio = (bloque_id - 1) * BLOQUE_SIZE
    fin = inicio + BLOQUE_SIZE

    try:
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=f"_bloque{bloque_id}.xlsx")
        workbook = xlsxwriter.Workbook(tmp.name, {'constant_memory': True})
        worksheet = workbook.add_worksheet()

        # Escribir encabezados
        for col_index, campo in enumerate(diseño):
            worksheet.write(0, col_index, campo["nombre"])

        with open(ruta, "r", encoding="utf-8") as f:
            fila_excel = 1
            for i, linea in enumerate(f):
                if i < inicio:
                    continue
                if i >= fin:
                    break
                largo = len(linea.rstrip('\n'))
                for col_index, campo in enumerate(diseño):
                    ini = campo["inicio"]
                    fin_campo = ini + campo["longitud"]
                    valor = linea[ini:fin_campo].strip() if fin_campo <= largo else ""
                    valor = limpiar_valor(valor)
                    worksheet.write(fila_excel, col_index, valor)
                fila_excel += 1

        workbook.close()
        nombre_archivo = f"{nombre_base}_bloque{bloque_id}.xlsx"
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
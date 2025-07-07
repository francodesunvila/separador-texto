from django.shortcuts import render, redirect
from django.core.files.storage import default_storage
from django.http import HttpResponse, FileResponse
import pandas as pd
import os
import tempfile
import traceback

def extraer_numero(texto):
    try:
        match = str(texto).strip()
        numbers = [int(s) for s in match.split() if s.isdigit()]
        return numbers[0] if numbers else 0
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
    preview = None
    mensaje = None
    conflictos = []

    if request.method == 'GET':
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
                else:
                    mensaje = "⚠️ El Excel no contiene las columnas necesarias: campo, posicion, caracter."
                    return render(request, 'home.html', {"mensaje": mensaje})
            except Exception as e:
                mensaje = f"⚠️ No se pudo leer el Excel: {str(e)}"
                return render(request, 'home.html', {"mensaje": mensaje})
        else:
            nombres = request.POST.getlist('nombre[]')
            inicios = request.POST.getlist('inicio[]')
            longitudes = request.POST.getlist('longitud[]')
            for i in range(len(nombres)):
                try:
                    nombre = str(nombres[i]).strip()
                    inicio = extraer_numero(inicios[i])
                    longitud = extraer_numero(longitudes[i])
                    if nombre and longitud > 0:
                        diseño.append({"nombre": nombre, "inicio": inicio, "longitud": longitud})
                except:
                    continue

        conflictos = detectar_solapamientos(diseño)
        if conflictos:
            resumen = conflictos[:5]
            if len(conflictos) > 5:
                resumen.append(f"...y {len(conflictos) - 5} conflictos más.")
            mensaje = "⚠️ Se detectaron superposiciones en el diseño."
            return render(request, 'home.html', {
                "mensaje": mensaje,
                "conflictos": resumen
            })

        datos = []
        with open(full_path, "r", encoding="utf-8") as f:
            for linea in f:
                linea = linea.rstrip('\n')
                largo_linea = len(linea)
                registro = {}
                ultimo_final = 0

                for campo in diseño:
                    inicio = campo["inicio"]
                    fin = inicio + campo["longitud"]
                    registro[campo["nombre"]] = linea[inicio:fin].strip() if fin <= largo_linea else ""
                    if fin > ultimo_final:
                        ultimo_final = fin

                if ultimo_final < largo_linea:
                    registro["Sin definir"] = linea[ultimo_final:].strip()
                datos.append(registro)

        # ✅ Guardar Excel completo en archivo temporal
        df = pd.DataFrame(datos)
        df.fillna("", inplace=True)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
            ruta_excel = tmp.name
            df.to_excel(ruta_excel, index=False)

        preview = df.head(20).to_dict(orient="records")
        request.session["ruta_excel"] = ruta_excel
        request.session["nombre_excel"] = os.path.splitext(archivo.name)[0] + ".xlsx"
        mensaje = "✅ Vista previa generada con éxito."

    return render(request, 'home.html', {
        "mensaje": mensaje,
        "preview": preview
    })

def descargar_excel(request):
    try:
        ruta = request.session.get("ruta_excel")
        nombre = request.session.get("nombre_excel", "resultado.xlsx")

        if not ruta or not os.path.isfile(ruta):
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
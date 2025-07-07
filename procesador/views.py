from django.shortcuts import render, redirect
from django.core.files.storage import default_storage
from django.http import HttpResponse, FileResponse
import pandas as pd
import os
import tempfile
import traceback

def extraer_numero(texto):
    try:
        return int(str(texto).strip())
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
        request.session["datos"] = None
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
                    # ✅ Convertir columnas a enteros
                    df_diseño["posicion"] = df_diseño["posicion"].astype(int)
                    df_diseño["caracter"] = df_diseño["caracter"].astype(int)

                    for _, fila in df_diseño.iterrows():
                        nombre = str(fila.get("campo", "")).strip()
                        inicio = int(fila.get("posicion"))
                        longitud = int(fila.get("caracter"))
                        if nombre and longitud > 0:
                            diseño.append({"nombre": nombre, "inicio": inicio, "longitud": longitud})
                    mensaje = "✅ Diseño importado desde Excel correctamente."
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

        df = pd.DataFrame(datos)
        preview = df.head().to_dict(orient="records")
        request.session["datos"] = df.to_dict(orient="records")
        request.session["nombre_excel"] = os.path.splitext(archivo.name)[0] + ".xlsx"

    return render(request, 'home.html', {
        "mensaje": mensaje,
        "preview": preview
    })

def descargar_excel(request):
    import traceback

    try:
        datos = request.session.get("datos")
        nombre_excel = request.session.get("nombre_excel", "salida.xlsx")

        if not datos or not isinstance(datos, list) or len(datos) == 0:
            return HttpResponse("⚠️ No hay datos disponibles para descargar.")

        df = pd.DataFrame(datos)
        df.fillna("", inplace=True)  # ✅ Evita NaN que rompen to_excel

        with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
            ruta = tmp.name
            try:
                df.to_excel(ruta, index=False)
            except Exception as e:
                print("⚠️ Error al escribir Excel:", traceback.format_exc())
                return HttpResponse("⚠️ No se pudo generar el archivo Excel.")

        response = FileResponse(open(ruta, "rb"), as_attachment=True, filename=nombre_excel)

        def borrar(r):
            try:
                os.remove(ruta)
            except Exception as e:
                print(f"⚠️ Error al borrar archivo: {e}")
            return r

        response.add_post_render_callback(borrar)
        return response

    except Exception as e:
        print("⚠️ Error general en descarga_excel():", traceback.format_exc())
        return HttpResponse("⚠️ Error interno al generar el archivo Excel.")

def eliminar_preview(request):
    request.session["datos"] = None
    request.session["nombre_excel"] = None
    return redirect('home')
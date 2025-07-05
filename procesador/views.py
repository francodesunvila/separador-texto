from django.shortcuts import render, redirect
from django.core.files.storage import default_storage
from django.http import HttpResponse, FileResponse
import pandas as pd
import os
import io
import re
import tempfile

def extraer_numero(texto):
    match = re.search(r'\d+', str(texto))
    return int(match.group()) if match else 0

def home(request):
    preview = None
    mensaje = None

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
                    for _, fila in df_diseño.iterrows():
                        try:
                            nombre = str(fila.get("campo", "")).strip()
                            inicio = extraer_numero(fila.get("posicion"))
                            longitud = extraer_numero(fila.get("caracter"))
                            diseño.append({"nombre": nombre, "inicio": inicio, "longitud": longitud})
                        except:
                            continue
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
                    campo = {
                        "nombre": nombres[i],
                        "inicio": int(inicios[i]),
                        "longitud": int(longitudes[i])
                    }
                    diseño.append(campo)
                except:
                    continue

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
    datos = request.session.get("datos")
    nombre_excel = request.session.get("nombre_excel", "salida.xlsx")

    if not datos:
        return HttpResponse("No hay datos procesados.")

    df = pd.DataFrame(datos)

    # ✅ Usar archivo temporal
    with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
        ruta = tmp.name
        df.to_excel(ruta, index=False)

    # 📦 Descargar archivo
    response = FileResponse(open(ruta, "rb"), as_attachment=True, filename=nombre_excel)

    # 🧹 Borrarlo automáticamente después
    def borrar(r):
        try:
            os.remove(ruta)
        except Exception as e:
            print(f"⚠️ Error al borrar archivo: {e}")
        return r

    response.add_post_render_callback(borrar)
    return response

def eliminar_preview(request):
    request.session["datos"] = None
    request.session["nombre_excel"] = None
    return redirect('home')
from flask import Flask, render_template, jsonify, request
import requests
import json
from bs4 import BeautifulSoup

app = Flask(__name__)

def obtener_token(session):
    url = 'https://sistemas.cepreuna.edu.pe/login'
    respuesta = session.get(url)
    if respuesta.status_code != 200:
        print('Error al obtener el token CSRF.')
        return None

    soup = BeautifulSoup(respuesta.text, 'html.parser')
    token = soup.find('input', {'name': '_token'})['value']
    return token

def iniciar_sesion(session, email, password):
    """
    Inicia sesión en la plataforma CEPREUNA.
    Devuelve True si el login es exitoso, False en caso contrario.
    """
    token = obtener_token(session)
    if not token:
        return False

    url = 'https://sistemas.cepreuna.edu.pe/login'
    datos = {
        '_token': token,
        'email': email,
        'password': password
    }

    respuesta = session.post(url, data=datos)
    if respuesta.ok and respuesta.url != url:
        print('Inicio de sesión exitoso.')
        return True
    else:
        print('Error al iniciar sesión.')
        return False

def obtener_datos(session):
    """
    Descarga todos los registros paginados de la plataforma CEPREUNA
    y los retorna en forma de lista de diccionarios.
    """
    todos_los_datos = []
    pagina = 1

    while True:
        url = (f'https://sistemas.cepreuna.edu.pe/intranet/inscripcion/estudiante'
               f'/lista/data?query=%7B%7D&limit=1000&ascending=1&page={pagina}&byColumn=1')
        respuesta = session.get(url)

        if respuesta.status_code != 200:
            print(f'Error al obtener datos de la página {pagina}.')
            break

        datos_json = respuesta.json()

        if not datos_json.get('data'):
            # Si 'data' está vacío, significa que no hay más páginas
            break

        todos_los_datos.extend(datos_json['data'])
        pagina += 1

    return todos_los_datos

@app.route('/')
def index():
    """
    Ruta principal. Renderiza la plantilla 'Index.html'
    que incluye el código para mostrar el gráfico.
    """
    return render_template('Index.html')

@app.route('/obtener_sedes', methods=['GET'])
def obtener_datos_endpoint():
    """
    Endpoint que hace:
      - Iniciar sesión con credenciales fijas (puedes cambiarlas).
      - Descarga de datos paginados.
      - Filtra opcionalmente por sede (si ?sede=xxx está en la URL).
      - Retorna el resultado en formato JSON (que luego usa tu front-end con Axios/Chart.js).
    """
    email = "esflores@cepreuna.edu.pe"  # << Ajusta según sea necesario
    password = "46386459"              # << Ajusta según sea necesario

    # Sede opcional. Ejemplo: /obtener_datos?sede=3
    sede_filtro = request.args.get('sede', None)

    with requests.Session() as session:
        if iniciar_sesion(session, email, password):
            datos = obtener_datos(session)
            # Filtrar y preparar la estructura final
            datos_procesados = []
            for registro in datos:
                # Verificar si cumple el filtro (si no se especifica, se incluyen todos)
                if sede_filtro and str(registro['sedes_id']) != sede_filtro:
                    continue

                programa = registro.get('programa', 'Sin Programa')
                datos_procesados.append({
                    'sede': registro['sedes_id'],
                    'programa': registro['sede']['denominacion']
                })

            return jsonify(datos_procesados)
        else:
            return jsonify({'error': 'No se pudo iniciar sesión'}), 401

if __name__ == '__main__':
    app.run(debug=True)

import os
import io
from flask import Flask, request, jsonify, send_file, send_from_directory
from flask_cors import CORS
import yt_dlp

# Le decimos a Flask que los archivos visuales están en la carpeta 'dist'
app = Flask(__name__, static_folder='dist', static_url_path='/')
CORS(app)

# --- 1. RUTAS DEL FRONTEND (LA INTERFAZ GRÁFICA) ---

@app.route('/')
def index():
    """Sirve la página principal de la aplicación"""
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/<path:path>')
def static_proxy(path):
    """
    Atrapa-todo: Permite que React cargue sus estilos (CSS), imágenes
    y maneje la navegación interna sin que Flask arroje error 404.
    """
    # Si el archivo que pide el navegador existe en 'dist', lo entrega
    if os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    # Si no existe, asume que es una ruta interna de React y recarga index.html
    return send_from_directory(app.static_folder, 'index.html')


# --- 2. RUTAS DEL BACKEND (LA LÓGICA DE YOUTUBE) ---

@app.route('/api/info', methods=['GET'])
def get_info():
    video_url = request.args.get('url')
    if not video_url:
        return jsonify({"error": "URL no proporcionada"}), 400

    try:
        ydl_opts = {'quiet': True, 'extract_flat': True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
            return jsonify({
                "title": info.get('title', 'Video sin título'),
                "author": info.get('uploader', 'Autor desconocido'),
                "thumbnail": info.get('thumbnail', '')
            })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/audio', methods=['GET'])
def get_audio():
    video_url = request.args.get('url')
    if not video_url:
        return jsonify({"error": "URL no proporcionada"}), 400

    audio_filename = "temp_audio"
    try:
        ydl_opts = {
    'format': 'bestaudio/best',
    'cookiefile': 'cookies.txt',  # <-- La llave maestra
    'postprocessors': [{
# ... (resto de tu código)
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '128',
            }],
            'quiet': True
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])

        with open(f"{audio_filename}.mp3", "rb") as f:
            data = io.BytesIO(f.read())
        os.remove(f"{audio_filename}.mp3")

        return send_file(data, mimetype="audio/mpeg", as_attachment=True, download_name="audio.mp3")

    except Exception as e:
        if os.path.exists(f"{audio_filename}.mp3"):
            os.remove(f"{audio_filename}.mp3")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # El puerto 10000 es el que configuramos en Docker
    app.run(host='0.0.0.0', port=10000)
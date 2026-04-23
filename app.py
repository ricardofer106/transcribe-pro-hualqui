import os
import io
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import yt_dlp

app = Flask(__name__)
CORS(app) # Permite que React hable con Flask

# 1. Ruta para obtener la información del video
@app.route('/')
def index():
    return app.send_static_file('index.html')

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

# 2. Ruta para descargar el audio y enviarlo a la interfaz
@app.route('/api/audio', methods=['GET'])
def get_audio():
    video_url = request.args.get('url')
    if not video_url:
        return jsonify({"error": "URL no proporcionada"}), 400

    audio_filename = "temp_audio"
    try:
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': audio_filename,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '128',
            }],
            'quiet': True
        }
        
        # Descargamos el audio usando yt-dlp
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])

        # Leemos el archivo a la memoria y lo borramos del disco para no acumular basura
        with open(f"{audio_filename}.mp3", "rb") as f:
            data = io.BytesIO(f.read())
        os.remove(f"{audio_filename}.mp3")

        # Enviamos el archivo de vuelta a React
        return send_file(data, mimetype="audio/mpeg", as_attachment=True, download_name="audio.mp3")

    except Exception as e:
        # Limpieza de emergencia si algo falla
        if os.path.exists(f"{audio_filename}.mp3"):
            os.remove(f"{audio_filename}.mp3")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
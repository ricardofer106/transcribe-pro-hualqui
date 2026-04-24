import os
import re
import time
import subprocess
from flask import Flask, request, jsonify
from flask_cors import CORS
import yt_dlp
from google import genai
from google.genai import types
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, storage

# Cargar variables de entorno
load_dotenv()

app = Flask(__name__, static_folder='dist', static_url_path='/')
CORS(app)

# Servir el Frontend (React) en producción
@app.route('/')
def serve_index():
    return app.send_static_file('index.html')

@app.errorhandler(404)
def handle_404(e):
    # Esto ayuda a que el routing de React funcione si refrescas la página
    return app.send_static_file('index.html')

# Configurar ruta de ffmpeg si existe en el directorio actual (para Windows local)
current_dir = os.path.dirname(os.path.abspath(__file__))
if os.path.exists(os.path.join(current_dir, "ffmpeg.exe")):
    os.environ["PATH"] += os.pathsep + current_dir

# Configuración de Firebase
firebase_enabled = False
try:
    if not firebase_admin._apps:
        service_account_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
        bucket_name = os.environ.get("FIREBASE_STORAGE_BUCKET", "turbotranscribir-rfh.firebasestorage.app")
        
        if service_account_path and os.path.exists(service_account_path):
            cred = credentials.Certificate(service_account_path)
            firebase_admin.initialize_app(cred, {
                'storageBucket': bucket_name
            })
            firebase_enabled = True
        else:
            # Intento de inicialización por defecto (útil en entornos con ADC o GAE)
            try:
                firebase_admin.initialize_app(options={
                    'storageBucket': bucket_name
                })
                firebase_enabled = True
            except Exception:
                print("Firebase: No se encontraron credenciales válidas. El almacenamiento en la nube estará desactivado.")
except Exception as e:
    print(f"Firebase initialization warning: {e}")

# Configuración de Gemini (Nuevo SDK google-genai)
api_key = os.environ.get("VITE_GEMINI_API_KEY")
client = None
if api_key:
    client = genai.Client(api_key=api_key)

@app.route('/api/info', methods=['GET'])
def get_video_info():
    video_url = request.args.get('url')
    if not video_url:
        return jsonify({"error": "URL requerida"}), 400
    try:
        ydl_opts = {'quiet': True, 'no_warnings': True, 'skip_download': True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
            return jsonify({
                "title": info.get('title', 'Video sin título'),
                "thumbnail": info.get('thumbnail'),
                "duration": info.get('duration')
            })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def clean_transcription_text(text):
    """
    Filtro crítico: Elimina marcas de tiempo, etiquetas de hablante y metadatos técnicos.
    Retorna texto puro y fluido.
    """
    if not text:
        return ""
        
    # 1. Eliminar bloques JSON y Markdown
    text = re.sub(r'```(?:json)?.*?```', '', text, flags=re.DOTALL)
    text = re.sub(r'\{.*?"fullText".*?\}', '', text, flags=re.DOTALL)
    
    # 2. Eliminar marcas de tiempo (formatos [00:00], (00:00:00), etc.)
    time_patterns = [
        r'\[\d{1,2}:\d{2}(:\d{2})?\]',
        r'\(\d{1,2}:\d{2}(:\d{2})?\)',
        r'\d{1,2}:\d{2}(:\d{2})?',
        r'\d{1,2}:\d{2}'
    ]
    for pattern in time_patterns:
        text = re.sub(pattern, '', text)
    
    # 3. Eliminar etiquetas de hablante (Ej: "Hablante 1:", "Speaker A:", "Alcalde:")
    text = re.sub(r'^(?:[A-Za-z\s]+|Hablante\s\d+|Speaker\s[A-Z]):', '', text, flags=re.MULTILINE)
    
    # 4. Limpieza final de espacios
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = text.strip()
    
    return text

@app.route('/api/transcribe', methods=['GET'])
def transcribe_video():
    video_url = request.args.get('url')
    if not video_url:
        return jsonify({"error": "URL de video requerida"}), 400

    if not client:
        return jsonify({"error": "Gemini API Key no configurada"}), 500

    request_id = int(time.time())
    audio_path = f"temp_audio_{request_id}.mp3"
    audio_base = f"temp_audio_{request_id}"
    
    try:
        # 1. Descarga de Audio
        print(f"Descargando audio para {video_url}...")
        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '128',
            }],
            'outtmpl': audio_base,
            'quiet': True,
            'no_warnings': True
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])
        
        # yt-dlp con FFmpegExtractAudio añade .mp3 automáticamente al outtmpl
        if not os.path.exists(audio_path):
            if os.path.exists(audio_base):
                os.rename(audio_base, audio_path)
            else:
                return jsonify({"error": "Error al extraer audio: archivo no encontrado"}), 500

        # 2. Subida a Firebase (Opcional, para redundancia)
        firebase_url = None
        if firebase_enabled:
            try:
                print("Subiendo a Firebase Storage...")
                bucket = storage.bucket()
                blob = bucket.blob(f"audio_{request_id}.mp3")
                blob.upload_from_filename(audio_path)
                blob.make_public()
                firebase_url = blob.public_url
            except Exception as fe:
                print(f"Error subiendo a Firebase: {fe}")
                # No detenemos el proceso si Firebase falla

        # 3. Procesamiento con Gemini File API (Nuevo SDK)
        print("Enviando a Gemini File API...")
        
        # Subir archivo directamente con el nuevo SDK
        uploaded_file = client.files.upload(file=audio_path)
        
        # Esperar a que el archivo sea procesado por la infraestructura de Google
        while uploaded_file.state.name == "PROCESSING":
            time.sleep(5)
            uploaded_file = client.files.get(name=uploaded_file.name)
            
        if uploaded_file.state.name == "FAILED":
            raise Exception("Gemini File API processing failed")

        # Generar contenido (Transcripción)
        # Usamos gemini-1.5-flash que es más estable en cuota gratuita para archivos largos
        prompt = """
        Eres un transcriptor profesional de actas municipales. 
        Genera una transcripción íntegra, fluida y exacta del audio proporcionado.
        
        REGLAS CRÍTICAS:
        1. NO incluyas marcas de tiempo.
        2. NO incluyas etiquetas de 'Speaker' o 'Hablante'.
        3. NO incluyas metadatos técnicos o JSON.
        4. Entrega solo el texto narrativo y fluido de la sesión.
        """
        
        # Lógica de reintento para cuota (429) y saturación (503)
        max_retries = 3
        wait_time = 10
        for i in range(max_retries):
            try:
                response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=[uploaded_file, prompt]
                )
                raw_text = response.text
                break
            except Exception as e:
                error_msg = str(e)
                if ("429" in error_msg or "503" in error_msg) and i < max_retries - 1:
                    print(f"Gemini ocupado o cuota excedida, reintentando en {wait_time}s... (Intento {i + 1}/{max_retries})")
                    time.sleep(wait_time)
                    wait_time *= 2
                    continue
                else:
                    print(f"Error crítico en Gemini: {error_msg}")
                    return jsonify({"error": error_msg}), 500
        
        # 4. Limpieza de Texto (Filtro Crítico)
        clean_text = clean_transcription_text(raw_text)
        
        # Limpiar archivos temporales
        if os.path.exists(audio_path):
            os.remove(audio_path)
        try:
            client.files.delete(name=uploaded_file.name)
        except:
            pass

        return jsonify({
            "transcription": clean_text,
            "status": "success"
        })

    except Exception as e:
        print(f"Error general: {e}")
        if os.path.exists(audio_path):
            os.remove(audio_path)
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # Configuración para producción básica (puerto 10000)
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
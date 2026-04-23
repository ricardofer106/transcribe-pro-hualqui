# Etapa 1: Compilar el Frontend (React)
FROM node:20 as frontend-builder
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build

# Etapa 2: Configurar el Backend (Python)
FROM python:3.11-slim
WORKDIR /app

# Instalar FFmpeg (vital para YouTube)
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

# Copiar dependencias de Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el ejecutable de Flask y la carpeta 'dist' compilada
COPY --from=frontend-builder /app/dist ./dist
COPY app.py .

# Comando para iniciar la aplicación con Gunicorn (más estable que Flask puro)
CMD ["gunicorn", "--bind", "0.0.0.0:10000", "app:app"]
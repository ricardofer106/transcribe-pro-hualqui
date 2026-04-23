import express from "express";
import { createServer as createViteServer } from "vite";
import ytdl from "@distube/ytdl-core";
import path from "path";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

async function startServer() {
  const app = express();
  const PORT = 3000;

  // Simple endpoint to proxy YouTube audio stream
  app.get("/api/audio", async (req, res) => {
    const videoUrl = req.query.url as string;

    if (!videoUrl || !ytdl.validateURL(videoUrl)) {
      return res.status(400).json({ error: "URL de YouTube no válida" });
    }

    try {
      res.setHeader("Content-Type", "audio/mpeg");
      
      // Get audio only stream with highest performance (usually m4a or webm audio)
      // We'll let Gemini handle the format, its very flexible
      ytdl(videoUrl, {
        filter: "audioonly",
        quality: "highestaudio",
      })
        .on("error", (err) => {
          console.error("YTDL Error:", err);
          if (!res.headersSent) {
            res.status(500).json({ error: "Error al extraer el audio del video" });
          }
        })
        .pipe(res);

    } catch (error) {
      console.error("Server Error:", error);
      res.status(500).json({ error: "Error interno del servidor" });
    }
  });

  // Get video metadata
  app.get("/api/info", async (req, res) => {
    const videoUrl = req.query.url as string;
    if (!videoUrl || !ytdl.validateURL(videoUrl)) {
      return res.status(400).json({ error: "URL de YouTube no válida" });
    }
    try {
      const info = await ytdl.getBasicInfo(videoUrl);
      res.json({
        title: info.videoDetails.title,
        author: info.videoDetails.author.name,
        thumbnail: info.videoDetails.thumbnails[0].url,
        lengthSeconds: info.videoDetails.lengthSeconds,
      });
    } catch (error) {
      res.status(500).json({ error: "No se pudo obtener la información del video" });
    }
  });

  // Vite middleware for development
  if (process.env.NODE_ENV !== "production") {
    const vite = await createViteServer({
      server: { middlewareMode: true },
      appType: "spa",
    });
    app.use(vite.middlewares);
  } else {
    const distPath = path.join(process.cwd(), "dist");
    app.use(express.static(distPath));
    app.get("*", (req, res) => {
      res.sendFile(path.join(distPath, "index.html"));
    });
  }

  app.listen(PORT, "0.0.0.0", () => {
    console.log(`Servidor iniciado en http://0.0.0.0:${PORT}`);
  });
}

startServer();

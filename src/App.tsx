import React, { useState } from "react";
import { Youtube, FileText, Download, Loader2, AlertCircle, ArrowRight, Sparkles, CheckCircle2 } from "lucide-react";
import axios from "axios";
import * as FileSaver from "file-saver";
import { Document, Packer, Paragraph, TextRun, AlignmentType } from "docx";

export default function App() {
  const [url, setUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [loadingStage, setLoadingStage] = useState("");
  const [info, setInfo] = useState<any>(null);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  const handleProcess = async () => {
    if (!url) return;
    setLoading(true);
    setError(null);
    setResult(null);
    setInfo(null);

    try {
      setLoadingStage("Obteniendo información del video...");
      const infoRes = await axios.get(`/api/info?url=${encodeURIComponent(url)}`);
      setInfo(infoRes.data);

      setLoadingStage("Extrayendo audio y procesando con Gemini (esto puede tardar varios minutos)...");
      const res = await axios.get(`/api/transcribe?url=${encodeURIComponent(url)}`, {
        timeout: 0 // Sin timeout para procesos largos
      });

      if (res.data && res.data.transcription) {
        setResult(res.data);
      } else {
        throw new Error("El servidor no devolvió una transcripción válida.");
      }
    } catch (err: any) {
      console.error(err);
      setError(err.response?.data?.error || err.message || "Error de conexión con el servidor.");
    } finally {
      setLoading(false);
      setLoadingStage("");
    }
  };

  const exportDocx = async () => {
    if (!result || !result.transcription || !info) {
      alert("Error: No hay datos de transcripción para generar el archivo.");
      return;
    }

    try {
      const doc = new Document({
        sections: [{
          properties: {
            page: {
              margin: { top: 1440, bottom: 1440, left: 1440, right: 1440 },
            },
          },
          children: [
            new Paragraph({
              children: [
                new TextRun({
                  text: "I. MUNICIPALIDAD DE HUALQUI",
                  bold: true,
                  size: 20,
                  font: "Calibri",
                }),
              ],
            }),
            new Paragraph({
              children: [
                new TextRun({
                  text: "ACTA DE TRANSCRIPCIÓN MUNICIPAL",
                  bold: true,
                  size: 28,
                  font: "Arial",
                }),
              ],
              alignment: AlignmentType.CENTER,
              spacing: { before: 400, after: 200 },
            }),
            new Paragraph({
              children: [
                new TextRun({
                  text: info.title.toUpperCase(),
                  bold: true,
                  size: 22,
                  font: "Arial",
                  color: "475569",
                }),
              ],
              alignment: AlignmentType.CENTER,
              spacing: { after: 600 },
            }),

            ...(result.transcription || "").split("\n\n").map((text: string) =>
              new Paragraph({
                children: [
                  new TextRun({
                    text: text,
                    size: 22,
                    font: "Arial",
                  }),
                ],
                alignment: AlignmentType.JUSTIFIED,
                spacing: { before: 120, after: 120, line: 360 },
              })
            ),

          ],
        }],
      });

      const blob = await Packer.toBlob(doc);
      const fileName = `Acta_${(info.title || "Sesion").replace(/[^a-z0-9]/gi, '_').substring(0, 50)}.docx`;
      FileSaver.saveAs(blob, fileName);
    } catch (err) {
      console.error("Error DOCX:", err);
      alert("Error al generar el documento Word.");
    }
  };

  return (
    <div className="min-h-screen bg-[#f8fafc] text-slate-900 font-sans selection:bg-orange-100 selection:text-orange-900">
      <div className="max-w-5xl mx-auto px-6 py-12">
        {/* Header */}
        <header className="text-center mb-16 space-y-4">
          <div className="inline-flex items-center justify-center p-3 bg-gradient-to-br from-orange-500 to-orange-600 rounded-3xl shadow-xl shadow-orange-200 mb-4 animate-bounce-subtle">
            <Sparkles className="text-white" size={32} />
          </div>
          <h1 className="text-5xl font-black tracking-tight text-slate-900">
            Transcribe Pro <span className="text-orange-500">Hualqui</span>
          </h1>
          <p className="text-slate-500 font-medium text-lg">
            Sistema Profesional de Transcripción de Sesiones Municipales
          </p>
        </header>

        {/* Input Card */}
        <div className="bg-white p-2 rounded-[2.5rem] shadow-2xl shadow-slate-200/60 border border-white">
          <div className="bg-slate-50/50 p-8 rounded-[2.2rem] border border-slate-100">
            <div className="max-w-2xl mx-auto space-y-6">
              <div className="space-y-2">
                <label className="text-xs font-bold text-slate-400 uppercase tracking-widest ml-1">Enlace de YouTube</label>
                <div className="relative group">
                  <div className="absolute inset-y-0 left-5 flex items-center pointer-events-none transition-colors group-focus-within:text-orange-500 text-slate-400">
                    <Youtube size={20} />
                  </div>
                  <input
                    type="text"
                    value={url}
                    onChange={(e) => setUrl(e.target.value)}
                    placeholder="https://www.youtube.com/watch?v=..."
                    className="w-full bg-white border-2 border-slate-100 rounded-2xl py-4 pl-14 pr-6 focus:ring-4 focus:ring-orange-500/10 focus:border-orange-500 outline-none transition-all text-slate-700 font-medium placeholder:text-slate-300"
                  />
                </div>
              </div>

              <button
                onClick={handleProcess}
                disabled={loading || !url}
                className={`w-full group relative overflow-hidden rounded-2xl py-5 font-bold text-white transition-all transform active:scale-[0.98] ${loading ? 'bg-slate-400 cursor-not-allowed' : 'bg-[#0f172a] hover:bg-slate-800 shadow-xl shadow-slate-200'
                  }`}
              >
                <div className="relative flex items-center justify-center gap-3">
                  {loading ? (
                    <>
                      <Loader2 className="animate-spin" size={20} />
                      <span>{loadingStage}</span>
                    </>
                  ) : (
                    <>
                      <ArrowRight className="group-hover:translate-x-1 transition-transform" size={20} />
                      <span>Generar Transcripción Limpia</span>
                    </>
                  )}
                </div>
              </button>
            </div>
          </div>
        </div>

        {/* Error Section */}
        {error && (
          <div className="mt-8 bg-red-50 border border-red-100 text-red-600 p-6 rounded-3xl flex items-center gap-4 animate-shake">
            <AlertCircle className="shrink-0" size={24} />
            <div>
              <p className="font-bold text-lg">Hubo un problema</p>
              <p className="opacity-90">{error}</p>
            </div>
          </div>
        )}

        {/* Success Section */}
        {result && (
          <div className="mt-12 space-y-6">
            <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 px-4">
              <div className="flex items-center gap-3">
                <div className="bg-green-100 p-2 rounded-full">
                  <CheckCircle2 className="text-green-600" size={24} />
                </div>
                <h2 className="text-2xl font-bold text-slate-800">Acta Lista para Descarga</h2>
              </div>
              <button
                onClick={exportDocx}
                className="w-full md:w-auto bg-blue-600 hover:bg-blue-700 text-white px-8 py-4 rounded-2xl font-bold flex gap-3 items-center justify-center shadow-lg shadow-blue-600/30 transition-all"
              >
                <FileText size={20} /> Descargar Acta (.docx)
              </button>
            </div>

            <div className="bg-white p-10 rounded-[3rem] border border-slate-100 shadow-xl shadow-slate-200/50">
              <div className="flex items-center gap-4 mb-8 pb-6 border-b border-slate-50">
                {info?.thumbnail && <img src={info.thumbnail} className="w-24 h-16 object-cover rounded-lg" alt="Thumbnail" />}
                <div>
                  <h3 className="font-bold text-slate-500 text-xs uppercase tracking-widest">Documento Generado</h3>
                  <p className="font-bold text-slate-900 text-lg line-clamp-1">{info?.title}</p>
                </div>
              </div>

              <div className="max-h-[500px] overflow-y-auto pr-4 scrollbar-thin scrollbar-thumb-slate-200">
                <p className="whitespace-pre-wrap text-slate-600 leading-[1.8] text-lg font-medium">
                  {result.transcription}
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Info Grid */}
        {!result && !loading && (
          <div className="mt-12 grid grid-cols-1 md:grid-cols-3 gap-6">
            {[
              { icon: Sparkles, title: "IA de Vanguardia", desc: "Uso de Gemini 1.5 Flash para transcripciones precisas." },
              { icon: FileText, title: "Formato Oficial", desc: "Generación de documentos Word para la Municipalidad." },
              { icon: CheckCircle2, title: "Filtro Inteligente", desc: "Elimina marcas de tiempo y etiquetas automáticamente." },
            ].map((item, i) => (
              <div key={i} className="p-6 bg-white rounded-[2rem] border border-slate-100 text-center space-y-3">
                <div className="mx-auto w-10 h-10 bg-orange-50 rounded-full flex items-center justify-center">
                  <item.icon className="text-orange-500" size={20} />
                </div>
                <h4 className="font-bold text-slate-800">{item.title}</h4>
                <p className="text-slate-500 text-sm leading-relaxed">{item.desc}</p>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
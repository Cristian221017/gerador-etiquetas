from flask import Flask, request, send_file
from fpdf import FPDF
import io

app = Flask(__name__)

@app.route("/", methods=["GET"])
def home():
    return "API de geração de etiquetas está rodando!"

@app.route("/gerar_etiqueta", methods=["POST"])
def gerar_etiqueta():
    data = request.json
    remetente = data.get("remetente", "Remetente Padrão")
    destinatario = data.get("destinatario", "Destinatário Padrão")
    cte = data.get("cte", "000000")
    nfs = data.get("nfs", "NF Padrão")
    obs = data.get("obs", "Sem observação")
    total_volumes = int(data.get("total_volumes", 1))
    largura_cm = float(data.get("largura", 10))
    altura_cm = float(data.get("altura", 5))

    pdf = EtiquetaPDF(largura_cm, altura_cm)

    for volume in range(1, total_volumes + 1):
        pdf.add_page()
        pdf.add_etiqueta(remetente, destinatario, cte, nfs, obs, volume, total_volumes)

    pdf_output = io.BytesIO()
    pdf.output(pdf_output)
    pdf_output.seek(0)

    return send_file(pdf_output, download_name="etiqueta.pdf", as_attachment=True)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

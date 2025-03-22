from flask import Flask, request, send_file, jsonify, render_template
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import io

app = Flask(__name__)

def gerar_pdf(remetente, destinatario, cte, nfs, obs, total_volumes, largura_cm, altura_cm):
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=(largura_cm * 28.35, altura_cm * 28.35))  # 1 cm = 28.35 pts
    pdf.setFont("Helvetica", 10)

    # Adiciona os detalhes ao PDF
    pdf.drawString(20, altura_cm * 28, f"Remetente: {remetente}")
    pdf.drawString(20, altura_cm * 26, f"Destinatário: {destinatario}")
    pdf.drawString(20, altura_cm * 24, f"CTE: {cte}")
    pdf.drawString(20, altura_cm * 22, f"Volumes: {total_volumes}")
    pdf.drawString(20, altura_cm * 20, f"Notas Fiscais: {nfs}")
    pdf.drawString(20, altura_cm * 18, f"Observação: {obs}")

    pdf.showPage()
    pdf.save()

    buffer.seek(0)
    return buffer

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/gerar_etiqueta", methods=["POST"])
def gerar_etiqueta():
    if not request.is_json:
        return jsonify({"erro": "O Content-Type deve ser application/json"}), 400

    try:
        data = request.get_json()
        remetente = data.get("remetente", "Remetente Padrão")
        destinatario = data.get("destinatario", "Destinatário Padrão")
        cte = data.get("cte", "000000")
        nfs = data.get("nfs", "NF Padrão")
        obs = data.get("obs", "Sem observação")
        total_volumes = int(data.get("total_volumes", 1))
        largura_cm = float(data.get("largura", 10))
        altura_cm = float(data.get("altura", 5))

        pdf_buffer = gerar_pdf(remetente, destinatario, cte, nfs, obs, total_volumes, largura_cm, altura_cm)

        return send_file(pdf_buffer, mimetype="application/pdf", as_attachment=True, download_name="etiqueta.pdf")

    except ValueError as ve:
        return jsonify({"erro": f"Valor inválido: {str(ve)}"}), 400
    except Exception as e:
        return jsonify({"erro": f"Erro interno do servidor: {str(e)}"}), 500

@app.route("/test_pdf", methods=["GET"])
def test_pdf():
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    pdf.setFont("Helvetica", 12)
    pdf.drawString(100, 750, "Teste de PDF Gerado com ReportLab!")
    pdf.showPage()
    pdf.save()

    buffer.seek(0)
    return send_file(buffer, mimetype="application/pdf", as_attachment=True, download_name="test.pdf")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

from flask import Flask, request, send_file, jsonify, render_template
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import io

app = Flask(__name__)

def gerar_pdf(remetente, destinatario, cte, nfs, obs, total_volumes, largura_cm, altura_cm):
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=(largura_cm * 28.35, altura_cm * 28.35))  # Convertendo cm para pontos

    # Configurações de fonte e margens
    margem = 10  # Margem interna
    fonte_titulo = 10
    fonte_texto = 8
    linha_atual = altura_cm * 28 - margem  # Define a linha inicial do texto

    for volume in range(1, total_volumes + 1):
        pdf.setFont("Helvetica-Bold", fonte_titulo)
        pdf.drawString(margem, linha_atual, f"Remetente:")
        pdf.setFont("Helvetica", fonte_texto)
        pdf.drawString(margem + 60, linha_atual, remetente)

        linha_atual -= 15
        pdf.setFont("Helvetica-Bold", fonte_titulo)
        pdf.drawString(margem, linha_atual, "Destinatário:")
        pdf.setFont("Helvetica", fonte_texto)
        pdf.drawString(margem + 60, linha_atual, destinatario)

        linha_atual -= 15
        pdf.setFont("Helvetica-Bold", fonte_titulo)
        pdf.drawString(margem, linha_atual, "CTE:")
        pdf.setFont("Helvetica", fonte_texto)
        pdf.drawString(margem + 40, linha_atual, cte)

        linha_atual -= 15
        pdf.setFont("Helvetica-Bold", fonte_titulo)
        pdf.drawString(margem, linha_atual, "Volumes:")
        pdf.setFont("Helvetica", fonte_texto)
        pdf.drawString(margem + 50, linha_atual, f"{volume}/{total_volumes}")

        linha_atual -= 15
        pdf.setFont("Helvetica-Bold", fonte_titulo)
        pdf.drawString(margem, linha_atual, "Notas Fiscais:")
        pdf.setFont("Helvetica", fonte_texto)
        pdf.drawString(margem + 80, linha_atual, nfs)

        linha_atual -= 15
        pdf.setFont("Helvetica-Bold", fonte_titulo)
        pdf.drawString(margem, linha_atual, "Observação:")
        pdf.setFont("Helvetica", fonte_texto)
        pdf.drawString(margem + 80, linha_atual, obs)

        pdf.showPage()  # Adiciona uma nova página para a próxima etiqueta

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

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

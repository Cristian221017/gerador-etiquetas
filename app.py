from flask import Flask, request, send_file, render_template, jsonify
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import io

app = Flask(__name__, template_folder="templates")

def criar_pdf(remetente, destinatario, cte, nfs, obs, volume_atual, total_volumes):
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    pdf.setFont("Helvetica", 12)
    
    pdf.drawString(50, height - 50, f"Remetente: {remetente}")
    pdf.drawString(50, height - 70, f"Destinatário: {destinatario}")
    pdf.drawString(50, height - 90, f"CTE: {cte}")
    pdf.drawString(50, height - 110, f"Volumes: {volume_atual}/{total_volumes}")
    
    pdf.drawString(50, height - 140, "Notas Fiscais:")
    text_object = pdf.beginText(50, height - 160)
    text_object.setFont("Helvetica", 10)
    for line in nfs.split("\n"):
        text_object.textLine(line)
    pdf.drawText(text_object)
    
    pdf.drawString(50, height - 200, "Observações:")
    text_object = pdf.beginText(50, height - 220)
    text_object.setFont("Helvetica", 10)
    for line in obs.split("\n"):
        text_object.textLine(line)
    pdf.drawText(text_object)
    
    pdf.save()
    buffer.seek(0)
    return buffer

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/gerar_etiqueta", methods=["POST"])
def gerar_etiqueta():
    try:
        if request.content_type != "application/json":
            return jsonify({"erro": "O Content-Type deve ser application/json"}), 400

        data = request.get_json()
        if not data:
            return jsonify({"erro": "Requisição inválida, JSON não encontrado"}), 400

        remetente = data.get("remetente", "Remetente Padrão")
        destinatario = data.get("destinatario", "Destinatário Padrão")
        cte = data.get("cte", "000000")
        nfs = data.get("nfs", "NF Padrão")
        obs = data.get("obs", "Sem observação")
        total_volumes = int(data.get("total_volumes", 1))

        pdf_buffer = criar_pdf(remetente, destinatario, cte, nfs, obs, 1, total_volumes)

        return send_file(
            pdf_buffer,
            mimetype="application/pdf",
            as_attachment=True,
            download_name="etiqueta.pdf"
        )

    except ValueError as ve:
        return jsonify({"erro": f"Valor inválido: {str(ve)}"}), 400
    except Exception as e:
        return jsonify({"erro": f"Erro interno do servidor: {str(e)}"}), 500

@app.route("/test_pdf", methods=["GET"])
def test_pdf():
    pdf_buffer = criar_pdf("Teste", "Destino Teste", "123456", "NF123", "Teste de PDF", 1, 1)

    return send_file(
        pdf_buffer,
        mimetype="application/pdf",
        as_attachment=True,
        download_name="teste.pdf"
    )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

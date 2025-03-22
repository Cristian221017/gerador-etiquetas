from flask import Flask, request, send_file, jsonify, render_template
from fpdf import FPDF
import io

app = Flask(__name__)

class EtiquetaPDF(FPDF):
    def __init__(self, largura_cm, altura_cm):
        largura_mm = largura_cm * 10
        altura_mm = altura_cm * 10
        super().__init__(orientation='P', unit='mm', format=(largura_mm, altura_mm))

    def add_etiqueta(self, remetente, destinatario, cte, nfs, obs, volume_atual, total_volumes):
        self.set_margins(5, 5, 5)
        self.set_auto_page_break(auto=False, margin=5)

        self.set_font("Arial", size=8, style='B')
        self.cell(20, 5, "Remetente:", ln=False)
        self.set_font("Arial", size=8)
        self.cell(0, 5, remetente.strip(), ln=True)

        self.set_font("Arial", size=8, style='B')
        self.cell(20, 5, "Destinatário:", ln=False)
        self.set_font("Arial", size=8)
        self.cell(0, 5, destinatario.strip(), ln=True)

        self.set_font("Arial", size=12, style='B')
        self.cell(15, 5, "CTE:", ln=False)
        self.set_font("Arial", size=12)
        self.cell(50, 5, cte.strip(), ln=False)

        self.set_font("Arial", size=12, style='B')
        self.cell(20, 5, "Volumes:", ln=False)
        self.set_font("Arial", size=12)
        self.cell(0, 5, f"{volume_atual}/{total_volumes}", ln=True)

        self.set_font("Arial", size=8, style='B')
        self.cell(0, 5, "Notas Fiscais:", ln=True)
        self.set_font("Arial", size=8)
        self.multi_cell(0, 5, nfs.strip())

        self.set_font("Arial", size=8, style='B')
        self.cell(0, 5, "Observação:", ln=True)
        self.set_font("Arial", size=8)
        self.multi_cell(0, 5, obs.strip())

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/gerar_etiqueta", methods=["POST"])
def gerar_etiqueta():
    try:
        if request.is_json:
            data = request.get_json()
        else:
            data = request.form

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

        # Correção: Salvar o PDF no objeto BytesIO corretamente
        pdf_output = io.BytesIO()
        pdf.output(pdf_output, dest='F')
        pdf_output.seek(0)

        return send_file(
            io.BytesIO(pdf_output.getvalue()),  # Corrigido para passar os dados corretamente
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
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="Test PDF", ln=1, align="C")

    pdf_output = io.BytesIO()
    pdf.output(pdf_output, dest='F')
    pdf_output.seek(0)

    return send_file(
        io.BytesIO(pdf_output.getvalue()),  # Corrigido para passar os dados corretamente
        mimetype="application/pdf",
        as_attachment=True,
        download_name="test.pdf"
    )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

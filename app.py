from flask import Flask, request, send_file, jsonify, render_template
from fpdf import FPDF
import io

app = Flask(__name__)

class EtiquetaPDF(FPDF):
    def __init__(self, largura_cm, altura_cm):
        largura_mm = largura_cm * 10
        altura_mm = altura_cm * 10
        super().__init__(orientation='P', unit='mm', format=(largura_mm, altura_mm))
        self.largura_mm = largura_mm
        self.altura_mm = altura_mm
        self.set_margins(5, 2, 5)  # Margem superior reduzida
        self.set_auto_page_break(auto=False, margin=2)

    def header(self):
        pass

    def add_etiqueta(self, origem, destino, remetente, destinatario, cte, nfs, obs, volume_atual, total_volumes):
        largura_texto = self.largura_mm - 10  # Largura útil da etiqueta

        def adicionar_campo(titulo, conteudo, fonte=9):
            self.set_font("Arial", style='B', size=fonte)
            self.cell(25, 5, f"{titulo}:", ln=False)
            self.cell(1)  # espaçamento após os dois pontos
            self.multi_cell(largura_texto - 25, 5, conteudo.strip().upper(), align='L')
            self.ln(1)

        # ORIGEM x DESTINO no topo em caixa preta com texto branco
        self.set_fill_color(0, 0, 0)
        self.set_text_color(255, 255, 255)
        self.set_font("Arial", style='B', size=12)
        self.cell(0, 7, f"{origem.upper()} x {destino.upper()}", ln=True, align='C', fill=True)
        self.set_text_color(0, 0, 0)
        self.ln(2)

        # Campos principais (com fonte aumentada em 2 px)
        adicionar_campo("Remetente", remetente, fonte=9)
        adicionar_campo("Destinatário", destinatario, fonte=9)

        # CTE e Volume em caixa preta com texto branco
        self.set_fill_color(0, 0, 0)
        self.set_text_color(255, 255, 255)
        self.set_font("Arial", style='B', size=12)
        self.cell(self.largura_mm / 2 - 5, 6, f"CTE: {cte.upper()}", ln=False, align='C', fill=True)
        self.cell(self.largura_mm / 2 - 5, 6, f"Volumes: {volume_atual}/{total_volumes}", ln=True, align='C', fill=True)
        self.set_text_color(0, 0, 0)
        self.ln(2)

        # Notas Fiscais
        adicionar_campo("Notas Fiscais", nfs, fonte=9)

        # Observação com fonte menor
        adicionar_campo("Observação", obs, fonte=7)

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/gerar_etiqueta", methods=["POST"])
def gerar_etiqueta():
    if not request.is_json:
        return jsonify({"erro": "O Content-Type deve ser application/json"}), 400

    try:
        data = request.get_json()
        origem = data.get("origem", "Origem Padrão")
        destino = data.get("destino", "Destino Padrão")
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
            pdf.add_etiqueta(origem, destino, remetente, destinatario, cte, nfs, obs, volume, total_volumes)

        # Gera saída do PDF e garante que esteja em bytes
        pdf_output_bytes = pdf.output(dest='S')
        if isinstance(pdf_output_bytes, str):
            pdf_output_bytes = pdf_output_bytes.encode('latin-1')

        pdf_output = io.BytesIO(pdf_output_bytes)
        pdf_output.seek(0)

        if len(pdf_output_bytes) == 0:
            return jsonify({"erro": "Erro ao gerar PDF: Arquivo vazio"}), 500

        return send_file(
            pdf_output,
            mimetype="application/pdf",
            as_attachment=True,
            download_name="etiqueta.pdf"
        )

    except ValueError as ve:
        return jsonify({"erro": f"Valor inválido: {str(ve)}"}), 400
    except Exception as e:
        return jsonify({"erro": f"Erro interno do servidor: {str(e)}"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

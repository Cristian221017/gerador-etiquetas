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
        self.set_margins(2, 2, 2)  # Bordas reduzidas para 2px
        self.set_auto_page_break(auto=False, margin=2)

    def header(self):
        pass  # Remove o cabeçalho padrão

    def add_etiqueta(self, origem, destino, remetente, destinatario, cte, nfs, obs, volume_atual, total_volumes):
        largura_texto = self.largura_mm - 10  # Espaço disponível

        # 📌 Origem e Destino (Centralizados)
        self.set_xy(2, 2)
        self.set_font("Arial", style='B', size=10)
        self.cell(0, 5, f"{origem} x {destino}", ln=True, align='C')

        # 📌 Caixa preta com CTE e Volume
        self.set_fill_color(0, 0, 0)
        self.set_text_color(255, 255, 255)
        self.set_font("Arial", style='B', size=10)
        self.cell(self.largura_mm / 2, 7, f"CTE: {cte}", ln=False, align='C', fill=True)
        self.cell(self.largura_mm / 2, 7, f"Volumes: {volume_atual}/{total_volumes}", ln=True, align='C', fill=True)

        # 📌 Resetando cor do texto
        self.set_text_color(0, 0, 0)

        # 📌 Remetente
        self.set_font("Arial", style='B', size=7)
        self.cell(20, 4, "Remetente:", ln=False)
        self.set_font("Arial", size=7)
        self.multi_cell(largura_texto - 20, 4, remetente.strip())

        # 📌 Destinatário
        self.set_font("Arial", style='B', size=7)
        self.cell(20, 4, "Destinatário:", ln=False)
        self.set_font("Arial", size=7)
        self.multi_cell(largura_texto - 20, 4, destinatario.strip())

        # 📌 Notas Fiscais
        self.set_font("Arial", style='B', size=7)
        self.cell(20, 4, "Notas Fiscais:", ln=False)
        self.set_font("Arial", size=7)
        self.multi_cell(largura_texto - 20, 4, nfs.strip())

        # 📌 Observação (Corrigida para posição correta)
        self.set_font("Arial", style='B', size=7)
        self.cell(20, 4, "Observação:", ln=False)
        self.set_font("Arial", size=7)
        self.multi_cell(largura_texto - 20, 4, obs.strip())

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

        pdf_output = io.BytesIO()
        pdf_output.write(pdf.output(dest='S').encode('latin1'))  # Convertendo para binário corretamente
        pdf_output.seek(0)

        return send_file(
            pdf_output,
            mimetype="application/pdf",
            as_attachment=True,
            download_name="etiqueta.pdf"
        )

    except Exception as e:
        return jsonify({"erro": f"Erro interno do servidor: {str(e)}"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

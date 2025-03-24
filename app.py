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
        self.set_margins(2, 2, 2)  # Margens reduzidas para otimização
        self.set_auto_page_break(auto=False, margin=2)

    def header(self):
        pass  # Removendo cabeçalho

    def add_etiqueta(self, origem_destino, remetente, destinatario, cte, nfs, obs, volume_atual, total_volumes):
        largura_texto = self.largura_mm - 4  # Ajuste para alinhar os textos corretamente

        # Origem x Destino no topo
        self.set_font("Arial", style='B', size=9)
        self.cell(0, 6, origem_destino, ln=True, align='C')

        # CTE e Volume dentro de uma caixa preta com letras brancas
        self.set_fill_color(0, 0, 0)  # Cor preta
        self.set_text_color(255, 255, 255)  # Texto branco
        self.set_font("Arial", style='B', size=9)

        self.cell(largura_texto / 2, 6, f"CTE: {cte}", border=1, fill=True, ln=False)
        self.cell(largura_texto / 2, 6, f"Volumes: {volume_atual}/{total_volumes}", border=1, fill=True, ln=True)

        # Restaurando cor preta do texto para as informações abaixo
        self.set_text_color(0, 0, 0)
        self.set_font("Arial", size=7)

        # Remetente
        self.set_font("Arial", style='B', size=7)
        self.cell(20, 5, "Remetente:", ln=False)
        self.set_font("Arial", size=7)
        self.multi_cell(largura_texto - 20, 5, remetente.strip())

        # Destinatário
        self.set_font("Arial", style='B', size=7)
        self.cell(20, 5, "Destinatário:", ln=False)
        self.set_font("Arial", size=7)
        self.multi_cell(largura_texto - 20, 5, destinatario.strip())

        # Notas Fiscais
        self.set_font("Arial", style='B', size=7)
        self.cell(0, 5, "Notas Fiscais:", ln=True)
        self.set_font("Arial", size=7)
        self.multi_cell(largura_texto, 5, nfs.strip())

        # Observação corrigida para se alinhar corretamente
        self.set_font("Arial", style='B', size=7)
        self.cell(0, 5, "Observação:", ln=True)
        self.set_font("Arial", size=7)
        self.multi_cell(largura_texto, 5, obs.strip())

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/gerar_etiqueta", methods=["POST"])
def gerar_etiqueta():
    if not request.is_json:
        return jsonify({"erro": "O Content-Type deve ser application/json"}), 400

    try:
        data = request.get_json()
        origem_destino = data.get("origem_destino", "Origem x Destino")
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
            pdf.add_etiqueta(origem_destino, remetente, destinatario, cte, nfs, obs, volume, total_volumes)

        # Criando buffer de memória
        pdf_output = io.BytesIO()
        pdf.output(pdf_output)
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

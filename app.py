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
        self.set_margins(5, 5, 5)
        self.set_auto_page_break(auto=False, margin=5)

    def header(self):
        pass  # Removendo cabeçalho para evitar sobreposição

    def add_etiqueta(self, origem, destino, remetente, destinatario, cte, nfs, obs, volume_atual, total_volumes):
        largura_texto = self.largura_mm - 10  # Largura útil da etiqueta

        def adicionar_campo(titulo, conteudo):
            self.set_font("Arial", style='B', size=9)
            self.cell(30, 5, f"{titulo}:", ln=False)
            self.set_font("Arial", size=9)
            self.multi_cell(largura_texto - 30, 5, conteudo.strip(), align='L')
            self.ln(1)  # Pequeno espaçamento entre os campos

        # Adicionando ORIGEM e DESTINO (sem título, apenas os valores)
        self.set_font("Arial", size=12, style='B')
        self.cell(0, 8, f"{origem} x {destino}", ln=True, align='C')
        self.ln(3)

        # Adicionando os campos padrão
        adicionar_campo("Remetente", remetente)
        adicionar_campo("Destinatário", destinatario)

        # CTE e Volumes dentro de uma caixa preta com texto branco
        self.set_fill_color(0, 0, 0)  # Define a cor de fundo como preta
        self.set_text_color(255, 255, 255)  # Define o texto como branco
        self.set_font("Arial", style='B', size=10)
        self.cell(self.largura_mm / 2 - 5, 7, f"CTE: {cte}", ln=False, align='C', fill=True)
        self.cell(self.largura_mm / 2 - 5, 7, f"Volumes: {volume_atual}/{total_volumes}", ln=True, align='C', fill=True)
        self.set_text_color(0, 0, 0)  # Retorna o texto para preto
        self.ln(3)

        # Notas Fiscais e Observação
        adicionar_campo("Notas Fiscais", nfs)
        adicionar_campo("Observação", obs)

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

        # Criando buffer de memória para armazenar o PDF
        pdf_output = io.BytesIO()
        pdf_output.write(pdf.output(dest='S'))
        pdf_output.seek(0)

        # 🚨 Verificação extra para evitar arquivos vazios
        if pdf_output.getbuffer().nbytes == 0:
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

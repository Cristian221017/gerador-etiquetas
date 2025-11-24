from flask import Flask, request, send_file, jsonify, render_template
from fpdf import FPDF
import io

app = Flask(__name__)

class EtiquetaPDF(FPDF):
    """
    Classe de geração de etiqueta com layout 'responsivo' em relação ao tamanho da etiqueta.
    A ideia é ajustar automaticamente:
      - tamanhos de fonte
      - espaçamentos
      - nível de detalhes exibidos
    de acordo com largura/altura informados em cm.
    """
    def __init__(self, largura_cm, altura_cm):
        largura_mm = largura_cm * 10
        altura_mm = altura_cm * 10
        super().__init__(orientation='P', unit='mm', format=(largura_mm, altura_mm))
        self.largura_mm = largura_mm
        self.altura_mm = altura_mm

        # Margens base (serão ajustadas em função do tamanho da etiqueta)
        self.set_margins(5, 3, 5)
        self.set_auto_page_break(auto=False, margin=2)

        # Estilos calculados dinamicamente
        self.estilos = self._calcular_estilos_responsivos()

    def _calcular_estilos_responsivos(self):
        """
        Define tamanhos de fonte e opções de compactação conforme o tamanho da etiqueta.
        Regra simples, mas eficaz:
          - Etiquetas muito pequenas: fontes menores, menos campos, observação mais compacta.
          - Etiquetas médias: fontes padrão.
          - Etiquetas grandes: fontes maiores e mais espaçamento.
        """
        area = self.largura_mm * self.altura_mm

        # Valores padrão (etiqueta média, ex: 100 x 50 mm)
        estilos = {
            "fonte_topo": 12,
            "fonte_campos": 9,
            "fonte_obs": 7,
            "altura_linha": 5,
            "mostrar_obs": True,
            "mostrar_nfs": True,
        }

        # Etiqueta muito pequena (ex: menor que ~80 x 40 = 3200 mm²)
        if area < 3200:
            estilos.update({
                "fonte_topo": 10,
                "fonte_campos": 7,
                "fonte_obs": 6,
                "altura_linha": 4,
                "mostrar_obs": False,   # esconder observação se ficar apertado
            })
        # Etiqueta pequena/média
        elif area < 6000:
            estilos.update({
                "fonte_topo": 11,
                "fonte_campos": 8,
                "fonte_obs": 7,
                "altura_linha": 4.5,
            })
        # Etiquetas grandes: pode “aparecer” mais
        elif area > 9000:
            estilos.update({
                "fonte_topo": 14,
                "fonte_campos": 11,
                "fonte_obs": 9,
                "altura_linha": 5.5,
            })

        return estilos

    def _truncar_se_necessario(self, texto: str, max_chars: int) -> str:
        texto = (texto or "").strip()
        if len(texto) <= max_chars:
            return texto
        # Mantém começo e final, corta o meio
        return texto[: max_chars - 3] + "..."

    def add_etiqueta(self, origem, destino, remetente, destinatario, cte, nfs, obs, volume_atual, total_volumes):
        largura_texto = self.largura_mm - 10  # largura útil da etiqueta
        alt_linha = self.estilos["altura_linha"]

        def adicionar_campo(titulo, conteudo, fonte=None, max_chars=None):
            """Adiciona um campo título + conteúdo, respeitando largura e tamanho da etiqueta."""
            if not conteudo:
                return

            if max_chars is not None:
                conteudo = self._truncar_se_necessario(conteudo.upper(), max_chars)
            else:
                conteudo = conteudo.upper().strip()

            fonte = fonte or self.estilos["fonte_campos"]

            self.set_font("Arial", style='B', size=fonte)
            # largura reservada para o título
            largura_titulo = 25
            self.cell(largura_titulo, alt_linha, f"{titulo}:", ln=False)
            self.cell(1)  # pequeno espaçamento
            # texto do conteúdo
            self.set_font("Arial", style='', size=fonte)
            self.multi_cell(largura_texto - largura_titulo, alt_linha, conteudo, align='L')
            self.ln(0.5)

        # -------- TOPO: ORIGEM x DESTINO --------
        self.set_fill_color(0, 0, 0)
        self.set_text_color(255, 255, 255)
        self.set_font("Arial", style='B', size=self.estilos["fonte_topo"])

        topo_texto = f"{(origem or '').upper()} x {(destino or '').upper()}"
        # Se a etiqueta for bem estreita, corta o texto de topo também
        if self.largura_mm < 60:
            topo_texto = self._truncar_se_necessario(topo_texto, 20)

        self.cell(0, alt_linha + 2, topo_texto, ln=True, align='C', fill=True)
        self.set_text_color(0, 0, 0)
        self.ln(2)

        # -------- CAMPOS PRINCIPAIS --------
        # Em etiquetas muito pequenas, priorizamos DESTINATÁRIO e VOLUMES
        area_pequena = self.largura_mm * self.altura_mm < 3200

        if not area_pequena:
            adicionar_campo("Remetente", remetente, max_chars=70)
        adicionar_campo("Destinatário", destinatario, max_chars=70)

        # -------- CTE e VOLUMES em destaque --------
        self.set_fill_color(0, 0, 0)
        self.set_text_color(255, 255, 255)
        self.set_font("Arial", style='B', size=self.estilos["fonte_campos"] + 1)

        largura_meio = self.largura_mm / 2 - 5
        cte_label = f"CTE: {(cte or '').upper()}"
        vol_label = f"Vol: {volume_atual}/{total_volumes}"

        # Trunca se a etiqueta for estreita
        if self.largura_mm < 60:
            cte_label = self._truncar_se_necessario(cte_label, 18)
            vol_label = self._truncar_se_necessario(vol_label, 16)

        self.cell(largura_meio, alt_linha + 1, cte_label, ln=False, align='C', fill=True)
        self.cell(largura_meio, alt_linha + 1, vol_label, ln=True, align='C', fill=True)
        self.set_text_color(0, 0, 0)
        self.ln(2)

        # -------- NOTAS FISCAIS --------
        if self.estilos["mostrar_nfs"] and nfs:
            adicionar_campo("Notas Fiscais", nfs, max_chars=120 if not area_pequena else 60)

        # -------- OBSERVAÇÃO (OPCIONAL) --------
        if self.estilos["mostrar_obs"] and obs:
            adicionar_campo("Observação", obs, fonte=self.estilos["fonte_obs"], max_chars=160 if not area_pequena else 80)


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
        obs = data.get("obs", "")
        total_volumes = int(data.get("total_volumes", 1))
        largura_cm = float(data.get("largura", 10))
        altura_cm = float(data.get("altura", 5))

        # Garantias básicas
        if total_volumes < 1:
            total_volumes = 1
        if largura_cm <= 0 or altura_cm <= 0:
            return jsonify({"erro": "Largura e altura devem ser maiores que zero."}), 400

        pdf = EtiquetaPDF(largura_cm, altura_cm)

        for volume in range(1, total_volumes + 1):
            pdf.add_page()
            pdf.add_etiqueta(
                origem=origem,
                destino=destino,
                remetente=remetente,
                destinatario=destinatario,
                cte=cte,
                nfs=nfs,
                obs=obs,
                volume_atual=volume,
                total_volumes=total_volumes,
            )

        # Saída do PDF em bytes (tratamento robusto)
        pdf_output_bytes = pdf.output(dest='S')
        if isinstance(pdf_output_bytes, str):
            pdf_output_bytes = pdf_output_bytes.encode('latin-1')

        if len(pdf_output_bytes) == 0:
            return jsonify({"erro": "Erro ao gerar PDF: arquivo vazio."}), 500

        pdf_output = io.BytesIO(pdf_output_bytes)
        pdf_output.seek(0)

        return send_file(
            pdf_output,
            mimetype="application/pdf",
            as_attachment=True,
            download_name="etiqueta.pdf"
        )

    except ValueError as ve:
        return jsonify({"erro": f"Valor inválido: {str(ve)}"}), 400
    except Exception as e:
        # Em produção, ideal seria logar o erro em vez de expor tudo
        return jsonify({"erro": f"Erro interno do servidor: {str(e)}"}), 500


if __name__ == "__main__":
    # Em produção (Render, etc.), geralmente não se usa debug=True
    app.run(host="0.0.0.0", port=5000)

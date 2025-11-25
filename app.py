from flask import Flask, request, send_file, jsonify, render_template
from fpdf import FPDF
import io
import xml.etree.ElementTree as ET

app = Flask(__name__)

# -----------------------------
# PDF "RESPONSIVO" POR TAMANHO
# -----------------------------


class EtiquetaPDF(FPDF):
    """
    Classe de geração de etiqueta com layout 'responsivo' em relação ao tamanho da etiqueta.
    Ajusta automaticamente:
      - tamanhos de fonte
      - espaçamentos
      - nível de detalhes exibidos
    de acordo com largura/altura informados em cm.
    """

    def __init__(self, largura_cm, altura_cm):
        largura_mm = largura_cm * 10
        altura_mm = altura_cm * 10
        super().__init__(orientation="P", unit="mm", format=(largura_mm, altura_mm))
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
            estilos.update(
                {
                    "fonte_topo": 10,
                    "fonte_campos": 7,
                    "fonte_obs": 6,
                    "altura_linha": 4,
                    "mostrar_obs": False,  # esconder observação se ficar apertado
                }
            )
        # Etiqueta pequena/média
        elif area < 6000:
            estilos.update(
                {
                    "fonte_topo": 11,
                    "fonte_campos": 8,
                    "fonte_obs": 7,
                    "altura_linha": 4.5,
                }
            )
        # Etiquetas grandes: pode “aparecer” mais
        elif area > 9000:
            estilos.update(
                {
                    "fonte_topo": 14,
                    "fonte_campos": 11,
                    "fonte_obs": 9,
                    "altura_linha": 5.5,
                }
            )

        return estilos

    def _truncar_se_necessario(self, texto: str, max_chars: int) -> str:
        texto = (texto or "").strip()
        if len(texto) <= max_chars:
            return texto
        # Mantém começo e final, corta o meio
        return texto[: max_chars - 3] + "..."

    def add_etiqueta(
        self,
        origem,
        destino,
        remetente,
        destinatario,
        cte,
        nfs,
        obs,
        volume_atual,
        total_volumes,
    ):
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

            self.set_font("Arial", style="B", size=fonte)
            # largura reservada para o título
            largura_titulo = 25
            self.cell(largura_titulo, alt_linha, f"{titulo}:", ln=False)
            self.cell(1)  # pequeno espaçamento
            # texto do conteúdo
            self.set_font("Arial", style="", size=fonte)
            self.multi_cell(
                largura_texto - largura_titulo, alt_linha, conteudo, align="L"
            )
            self.ln(0.5)

        # -------- TOPO: ORIGEM x DESTINO --------
        self.set_fill_color(0, 0, 0)
        self.set_text_color(255, 255, 255)
        self.set_font("Arial", style="B", size=self.estilos["fonte_topo"])

        topo_texto = f"{(origem or '').upper()} x {(destino or '').upper()}"
        # Se a etiqueta for bem estreita, corta o texto de topo também
        if self.largura_mm < 60:
            topo_texto = self._truncar_se_necessario(topo_texto, 20)

        self.cell(0, alt_linha + 2, topo_texto, ln=True, align="C", fill=True)
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
        self.set_font("Arial", style="B", size=self.estilos["fonte_campos"] + 1)

        largura_meio = self.largura_mm / 2 - 5
        cte_label = f"CTE: {(cte or '').upper()}"
        vol_label = f"Vol: {volume_atual}/{total_volumes}"

        # Trunca se a etiqueta for estreita
        if self.largura_mm < 60:
            cte_label = self._truncar_se_necessario(cte_label, 18)
            vol_label = self._truncar_se_necessario(vol_label, 16)

        self.cell(
            largura_meio, alt_linha + 1, cte_label, ln=False, align="C", fill=True
        )
        self.cell(
            largura_meio, alt_linha + 1, vol_label, ln=True, align="C", fill=True
        )
        self.set_text_color(0, 0, 0)
        self.ln(2)

        # -------- NOTAS FISCAIS --------
        if self.estilos["mostrar_nfs"] and nfs:
            adicionar_campo(
                "Notas Fiscais",
                nfs,
                max_chars=120 if not area_pequena else 60,
            )

        # -------- OBSERVAÇÃO (OPCIONAL) --------
        if self.estilos["mostrar_obs"] and obs:
            adicionar_campo(
                "Observação",
                obs,
                fonte=self.estilos["fonte_obs"],
                max_chars=160 if not area_pequena else 80,
            )


# -----------------------------
# PARSER DE XML (CT-e / NF-e)
# -----------------------------


def _strip_ns(tag: str) -> str:
    """Remove namespace de uma tag XML (ex: '{http://...}ide' -> 'ide')."""
    if "}" in tag:
        return tag.split("}", 1)[1]
    return tag


def _find_first_by_tag(root, tag_names):
    """
    Procura o primeiro elemento cujo nome (sem namespace) seja um dos informados em tag_names.
    tag_names pode ser string ou lista.
    """
    if isinstance(tag_names, str):
        tag_names = [tag_names]

    wanted = set(tag_names)
    for elem in root.iter():
        if _strip_ns(elem.tag) in wanted:
            return elem
    return None


def numero_nf_da_chave(chave: str):
    """
    Extrai o número da NF (nNF) a partir da chave de NF-e (44 dígitos).
    nNF ocupa as posições 26 a 34 (índices 25 a 34 em Python).
    """
    if not chave:
        return None
    apenas_digitos = "".join(filter(str.isdigit, chave))
    if len(apenas_digitos) != 44:
        return None
    nNF = apenas_digitos[25:34]
    try:
        return str(int(nNF))  # remove zeros à esquerda
    except ValueError:
        return None


def parse_xml_cte_nfe(xml_content: str):
    """
    Faz uma interpretação 'genérica' de XML de CT-e ou NF-e para extrair:
      - origem (cidade/UF do remetente)
      - destino (cidade/UF do destinatário)
      - remetente (xNome)
      - destinatario (xNome)
      - cte (nCT ou chave)
      - nfs (lista de números de NF ou chaves, concatenados)
      - obs (xObs, obsCont etc. se houver)
      - total_volumes (CT-e: tpMed/qCarga; NF-e: qVol)
    """
    try:
        root = ET.fromstring(xml_content)
    except Exception as e:
        raise ValueError(f"XML inválido: {e}")

    # Alguns XMLs vêm como cteProc/nfeProc, então tentamos achar o "miolo"
    # infCte ou infNFe se existirem
    infcte = _find_first_by_tag(root, ["infCte", "InfCte"])
    infnfe = _find_first_by_tag(root, ["infNFe", "InfNFe"])

    origem = ""
    destino = ""
    remetente = ""
    destinatario = ""
    cte_numero = ""
    nfs_list = []
    obs = ""
    total_volumes = None  # será preenchido se acharmos no XML

    # ------------- CT-e -------------
    if infcte is not None:
        # REMETENTE
        rem = _find_first_by_tag(infcte, ["rem"])
        if rem is not None:
            xNome_rem = _find_first_by_tag(rem, ["xNome"])
            remetente = (xNome_rem.text or "").strip() if xNome_rem is not None else ""

            ender = _find_first_by_tag(rem, ["enderReme", "enderRem", "enderEmit"])
            if ender is not None:
                xMun = _find_first_by_tag(ender, ["xMun"])
                UF = _find_first_by_tag(ender, ["UF"])
                cidade = (xMun.text or "").strip() if xMun is not None else ""
                uf = (UF.text or "").strip() if UF is not None else ""
                origem = f"{cidade} - {uf}".strip(" -")

        # DESTINATÁRIO
        dest = _find_first_by_tag(infcte, ["dest"])
        if dest is not None:
            xNome_dest = _find_first_by_tag(dest, ["xNome"])
            destinatario = (
                (xNome_dest.text or "").strip() if xNome_dest is not None else ""
            )

            ender_d = _find_first_by_tag(dest, ["enderDest", "enderReceb"])
            if ender_d is not None:
                xMun = _find_first_by_tag(ender_d, ["xMun"])
                UF = _find_first_by_tag(ender_d, ["UF"])
                cidade = (xMun.text or "").strip() if xMun is not None else ""
                uf = (UF.text or "").strip() if UF is not None else ""
                destino = f"{cidade} - {uf}".strip(" -")

        # IDE (nCT, etc.)
        ide = _find_first_by_tag(infcte, ["ide"])
        if ide is not None:
            nCT = _find_first_by_tag(ide, ["nCT"])
            if nCT is not None and nCT.text:
                cte_numero = nCT.text.strip()

        # NF-es vinculadas (infDoc / infNFe / chave)
        infDoc = _find_first_by_tag(infcte, ["infDoc"])
        if infDoc is not None:
            for child in infDoc:
                tag = _strip_ns(child.tag)

                # NF-e
                if tag == "infNFe":
                    chave_el = _find_first_by_tag(child, ["chave", "chNFe"])
                    if chave_el is not None and chave_el.text:
                        chave = chave_el.text.strip()
                        numero_nf = numero_nf_da_chave(chave)
                        if numero_nf:
                            nfs_list.append(numero_nf)
                        else:
                            nfs_list.append(chave)

                # NF modelo 1/1A (papel)
                if tag == "infNF":
                    nDoc_el = _find_first_by_tag(child, ["nDoc"])
                    if nDoc_el is not None and nDoc_el.text:
                        nfs_list.append(nDoc_el.text.strip())

        # Observações (xObs, obsCont, obsFisco)
        compl = _find_first_by_tag(infcte, ["compl"])
        if compl is not None:
            xObs = _find_first_by_tag(compl, ["xObs"])
            if xObs is not None and xObs.text:
                obs = xObs.text.strip()
            else:
                # tentar obsCont/obsFisco
                txts = []
                for elem in compl.iter():
                    if _strip_ns(elem.tag) in ("obsCont", "obsFisco") and elem.text:
                        txts.append(elem.text.strip())
                if txts:
                    obs = " | ".join(txts)

        # QTDE VOLUMES a partir de tpMed/qCarga
        # Estrutura típica:
        # <infQ>
        #   <tpMed>QTDE VOLUMES</tpMed>
        #   <qCarga>126.0000</qCarga>
        # </infQ>
        for infQ in infcte.iter():
            if _strip_ns(infQ.tag) not in ("infQ", "infCarga", "infQuant"):
                continue
            tpMed_el = _find_first_by_tag(infQ, ["tpMed"])
            if tpMed_el is None or not tpMed_el.text:
                continue
            if tpMed_el.text.strip().upper() != "QTDE VOLUMES":
                continue
            qCarga_el = _find_first_by_tag(infQ, ["qCarga"])
            if qCarga_el is not None and qCarga_el.text:
                try:
                    total_volumes = int(float(qCarga_el.text.strip()))
                except ValueError:
                    pass

    # ------------- NF-e (se enviada isolada, sem CT-e) -------------
    if infnfe is not None and not remetente and not destinatario:
        emit = _find_first_by_tag(infnfe, ["emit"])
        if emit is not None:
            xNome_emit = _find_first_by_tag(emit, ["xNome"])
            remetente = (
                (xNome_emit.text or "").strip() if xNome_emit is not None else ""
            )
            ender_emit = _find_first_by_tag(emit, ["enderEmit"])
            if ender_emit is not None:
                xMun = _find_first_by_tag(ender_emit, ["xMun"])
                UF = _find_first_by_tag(ender_emit, ["UF"])
                cidade = (xMun.text or "").strip() if xMun is not None else ""
                uf = (UF.text or "").strip() if UF is not None else ""
                origem = f"{cidade} - {uf}".strip(" -")

        dest_nfe = _find_first_by_tag(infnfe, ["dest"])
        if dest_nfe is not None:
            xNome_dest = _find_first_by_tag(dest_nfe, ["xNome"])
            destinatario = (
                (xNome_dest.text or "").strip() if xNome_dest is not None else ""
            )
            ender_dest = _find_first_by_tag(dest_nfe, ["enderDest"])
            if ender_dest is not None:
                xMun = _find_first_by_tag(ender_dest, ["xMun"])
                UF = _find_first_by_tag(ender_dest, ["UF"])
                cidade = (xMun.text or "").strip() if xMun is not None else ""
                uf = (UF.text or "").strip() if UF is not None else ""
                destino = f"{cidade} - {uf}".strip(" -")

        # VOLUMES na NF-e: transp/vol/qVol
        if total_volumes is None:
            transp = _find_first_by_tag(infnfe, ["transp"])
            if transp is not None:
                for vol in transp.iter():
                    if _strip_ns(vol.tag) == "vol":
                        qVol_el = _find_first_by_tag(vol, ["qVol"])
                        if qVol_el is not None and qVol_el.text:
                            try:
                                total_volumes = int(float(qVol_el.text.strip()))
                            except ValueError:
                                pass
                            break  # pega só o primeiro vol

        # Número da NF (nNF) na própria NF-e
        ide_nf = _find_first_by_tag(infnfe, ["ide"])
        if ide_nf is not None:
            nNF = _find_first_by_tag(ide_nf, ["nNF"])
            if nNF is not None and nNF.text:
                nfs_list.append(nNF.text.strip())

    # Consolida NFs (remove duplicadas mantendo ordem)
    if nfs_list:
        nfs_str = ", ".join(dict.fromkeys(nfs_list))
    else:
        nfs_str = ""

    # Monta payload padrão do sistema
    payload = {
        "origem": origem or "",
        "destino": destino or "",
        "remetente": remetente or "",
        "destinatario": destinatario or "",
        "cte": cte_numero or "",
        "nfs": nfs_str or "",
        "obs": obs or "",
    }

    if total_volumes is not None and total_volumes > 0:
        payload["total_volumes"] = total_volumes

    return payload


# -----------------------------
# ROTAS FLASK
# -----------------------------


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/parse_xml", methods=["POST"])
def parse_xml_route():
    """
    Endpoint para interpretar XML de CT-e ou NF-e.
    Aceita:
      - multipart/form-data com arquivo (campo 'xml_file')
      - application/json com campo 'xml'
    Retorna JSON com campos já no padrão do formulário de etiqueta.
    """
    xml_content = None

    # Upload via arquivo
    if "xml_file" in request.files:
        file = request.files["xml_file"]
        if not file.filename:
            return jsonify({"erro": "Nenhum arquivo selecionado."}), 400
        xml_content = file.read().decode("utf-8", errors="ignore")

    # Via JSON (xml como string)
    if xml_content is None and request.is_json:
        data = request.get_json(silent=True) or {}
        xml_content = data.get("xml")

    if not xml_content:
        return jsonify({"erro": "Nenhum conteúdo XML recebido."}), 400

    try:
        parsed = parse_xml_cte_nfe(xml_content)
        # Defaults se não vierem do XML
        parsed.setdefault("total_volumes", 1)
        parsed.setdefault("largura", 10)
        parsed.setdefault("altura", 5)
        return jsonify(parsed)
    except ValueError as ve:
        return jsonify({"erro": str(ve)}), 400
    except Exception as e:
        return jsonify({"erro": f"Falha ao interpretar XML: {e}"}), 500


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
            return (
                jsonify({"erro": "Largura e altura devem ser maiores que zero."}),
                400,
            )

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
        pdf_output_bytes = pdf.output(dest="S")
        if isinstance(pdf_output_bytes, str):
            pdf_output_bytes = pdf_output_bytes.encode("latin-1")

        if len(pdf_output_bytes) == 0:
            return jsonify({"erro": "Erro ao gerar PDF: arquivo vazio."}), 500

        pdf_output = io.BytesIO(pdf_output_bytes)
        pdf_output.seek(0)

        return send_file(
            pdf_output,
            mimetype="application/pdf",
            as_attachment=True,
            download_name="etiqueta.pdf",
        )

    except ValueError as ve:
        return jsonify({"erro": f"Valor inválido: {str(ve)}"}), 400
    except Exception as e:
        return jsonify({"erro": f"Erro interno do servidor: {str(e)}"}), 500


if __name__ == "__main__":
    # Em produção (Render, etc.), geralmente não se usa debug=True
    app.run(host="0.0.0.0", port=5000)

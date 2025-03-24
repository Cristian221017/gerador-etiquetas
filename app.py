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

    def add_etiqueta(self, remetente, destinatario, cte, nfs, obs, volume_atual, total_volumes):
        largura_texto = self.largura_mm - 10  # Ajustando para evitar que o texto saia da etiqueta

        # **Remetente**
        self.set_font("Arial", style='B', size=8)
        self.cell(20, 5, "Remetente:", ln=False)
        self.set_font("Arial", size=8)
        self.cell(0, 5, remetente.strip(), ln=True)

        # **Destinatário**
        self.set_font("Arial", style='B', size=8)
        self.cell(20, 5, "Destinatário:", ln=False)
        self.set_font("Arial", size=8)
        self.cell(0, 5, destinatario.strip(), ln=True)

        # **CTE e Volumes na mesma linha**
        self.set_font("Arial", style='B', size=12)
        self.cell(15, 5, "CTE:", ln=False)
        self.set_font("Arial", size=12)
        self.cell(self.largura_mm / 2 - 25, 5, cte.strip(), ln=False)

        self.set_font("Arial", style='B', size=12)
        self.cell(20, 5, "Volumes:", ln=False)
        self.set_font("Arial", size=12)
        self.cell(0, 5, f"{volume_atual}/{total_volumes}", ln=True)

        # **Notas Fiscais**
        self.set_font("Arial", style='B', size=8)
        self.cell(0, 5, "Notas Fiscais:", ln=True)
        self.set_font("Arial", size=8)
        self.multi_cell(largura_texto, 5, nfs.strip(), align='L') # Alinhamento à esquerda

        # **Observação** (✅ Agora ajustado para garantir alinhamento)
        self.set_font("Arial", style='B', size=8)
        self.cell(0, 5, "Observação:", ln=True)
        self.set_font("Arial", size=8)
        self.multi_cell(largura_texto, 5, obs.strip(), align='L') # Alinhamento à esquerda
"""
laudo_pdf.py — Gera o laudo histopatológico em PDF.

Frente: cabeçalho da faculdade + campos do laudo (centralizado).
Verso:  SÓ aparece se houver imagens. Layout dinâmico:
        1 img  → uma centralizada
        2 imgs → lado a lado
        3 imgs → 2 em cima + 1 embaixo (centralizada)
        4 imgs → grade 2x2
"""

from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, Image as RLImage,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY

LEGENDA_VERSO = "Fotomicrografias ilustrativas do caso em Análise. HLE"

TEXTO_RODAPE = (
    "O resultado deste exame é decorrente da correlação dos achados "
    "microscópicos com as informações clínicas e imagiológicas enviadas "
    "para estudo. Este resultado pode ser reavaliado com a ampliação de "
    "informações adicionais."
)

# Logo do cabeçalho: procura na mesma pasta do script
from pathlib import Path
LOGO_PATH = Path(__file__).parent / "Logo-Odonto-UFRGS.png"

AZUL = colors.HexColor("#1a3a6b")
CINZA_BORDA = colors.HexColor("#999999")
CINZA_GRID = colors.HexColor("#cccccc")


def _estilos(escala=1.0):
    """escala: multiplicador do tamanho da fonte (1.0 = normal)."""
    base = getSampleStyleSheet()
    return {
        "titulo": ParagraphStyle("titulo", parent=base["Normal"],
                                 fontName="Helvetica-Bold", fontSize=13,
                                 leading=16, alignment=TA_CENTER),
        "subtitulo": ParagraphStyle("subtitulo", parent=base["Normal"],
                                    fontName="Helvetica-Bold", fontSize=11,
                                    leading=14, alignment=TA_CENTER),
        "endereco": ParagraphStyle("endereco", parent=base["Normal"],
                                   fontName="Helvetica", fontSize=8,
                                   leading=10, alignment=TA_CENTER),
        "rotulo": ParagraphStyle("rotulo", parent=base["Normal"],
                                 fontName="Helvetica-Bold", fontSize=7.5 * escala,
                                 leading=9 * escala, textColor=AZUL),
        "valor": ParagraphStyle("valor", parent=base["Normal"],
                                fontName="Helvetica", fontSize=9.5 * escala,
                                leading=12 * escala),
        "legenda": ParagraphStyle("legenda", parent=base["Normal"],
                                  fontName="Helvetica-Oblique", fontSize=10,
                                  leading=13, alignment=TA_CENTER),
        "aumento": ParagraphStyle("aumento", parent=base["Normal"],
                                  fontName="Helvetica-Bold", fontSize=9,
                                  leading=11, alignment=TA_CENTER),
        "rodape": ParagraphStyle("rodape", parent=base["Normal"],
                                 fontName="Helvetica-Oblique", fontSize=8,
                                 leading=11, alignment=TA_JUSTIFY,
                                 textColor=colors.HexColor("#444444")),
        "assinatura": ParagraphStyle("assinatura", parent=base["Normal"],
                                     fontName="Helvetica", fontSize=9,
                                     leading=11, alignment=TA_CENTER,
                                     textColor=colors.HexColor("#333333")),
        "_escala": escala,
    }


def _campo(rotulo, valor, est):
    """Retorna UMA célula (Paragraph) com rótulo em cima e valor embaixo."""
    escala = est.get("_escala", 1.0)
    tam_rotulo = round(7.5 * escala, 1)
    v = str(valor).replace("\n", "<br/>") if valor else "&nbsp;"
    txt = f'<font color="#1a3a6b" size="{tam_rotulo}"><b>{rotulo}</b></font><br/>{v}'
    return Paragraph(txt, est["valor"])


def _tem_imagens(imagens):
    return imagens and any(item for item in imagens if item)


def gerar_laudo_pdf(dados: dict, imagens: list = None,
                    escala_fonte: float = 1.0, logo_modo: str = "normal") -> bytes:
    """
    dados: campos do laudo.
    imagens: lista de tuplas (caminho, aumento). Só gera verso se houver.
    escala_fonte: multiplicador do tamanho da fonte (1.0 = normal, 0.85 = menor, 1.15 = maior).
    logo_modo: "normal", "pequena" ou "sem" (controla a imagem do topo).
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        topMargin=14 * mm, bottomMargin=14 * mm,
        leftMargin=16 * mm, rightMargin=16 * mm,
    )
    est = _estilos(escala_fonte)
    story = []
    largura = doc.width

    # ── CABEÇALHO ──────────────────────────────────────────────────────────
    if LOGO_PATH.exists() and logo_modo != "sem":
        proporcao = 0.75 if logo_modo == "normal" else 0.42  # pequena = 42%
        logo_w = largura * proporcao
        logo_h = logo_w / 4.07
        logo = RLImage(str(LOGO_PATH), width=logo_w, height=logo_h)
        wrap = Table([[logo]], colWidths=[largura])
        wrap.setStyle(TableStyle([("ALIGN", (0, 0), (-1, -1), "CENTER")]))
        story.append(wrap)
        story.append(Spacer(1, 2 * mm))
        story.append(Paragraph("Laudo de Exame Histopatológico", est["subtitulo"]))
    else:
        story.append(Paragraph("Faculdade de Odontologia da UFRGS", est["titulo"]))
        story.append(Paragraph("Laboratório de Patologia — Laudo de Exame Histopatológico", est["subtitulo"]))
    story.append(Paragraph("Rua Ramiro Barcelos, 2492 / sala 503 &nbsp;•&nbsp; Fone (51) 3316.5023 &nbsp;•&nbsp; Porto Alegre/RS &nbsp;•&nbsp; CEP 90035-003", est["endereco"]))
    story.append(Spacer(1, 5 * mm))

    borda = TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.6, CINZA_BORDA),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, CINZA_GRID),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ])

    def linha(celulas, larguras):
        t = Table([celulas], colWidths=larguras)
        t.setStyle(borda)
        return t

    blocos = [
        linha([_campo("Número de Registro:", dados.get("num_registro"), est),
               _campo("Data:", dados.get("data"), est)],
              [largura * 0.6, largura * 0.4]),
        linha([_campo("Nome do Paciente:", dados.get("nome"), est),
               _campo("Endereço do Paciente:", dados.get("endereco_paciente"), est)],
              [largura * 0.55, largura * 0.45]),
        linha([_campo("Idade:", dados.get("idade"), est),
               _campo("Gênero:", dados.get("genero"), est),
               _campo("Raça:", dados.get("raca"), est),
               _campo("Profissão:", dados.get("profissao"), est)],
              [largura * 0.16, largura * 0.26, largura * 0.20, largura * 0.38]),
        linha([_campo("Titulação:", dados.get("titulacao"), est),
               _campo("Nome do Cirurgião:", dados.get("cirurgiao"), est),
               _campo("Endereço do Cirurgião:", dados.get("endereco_cirurgiao"), est),
               _campo("Convênio:", dados.get("convenio"), est)],
              [largura * 0.15, largura * 0.30, largura * 0.32, largura * 0.23]),
        linha([_campo("História Clínica:", dados.get("historia_clinica"), est)], [largura]),
        linha([_campo("Fumo:", dados.get("fumo"), est),
               _campo("Álcool:", dados.get("alcool"), est)],
              [largura * 0.5, largura * 0.5]),
        linha([_campo("Diagnóstico Clínico:", dados.get("diagnostico_clinico"), est),
               _campo("Localização Anatômica:", dados.get("localizacao"), est),
               _campo("Tipo de Biópsia:", dados.get("tipo_biopsia"), est)],
              [largura * 0.36, largura * 0.40, largura * 0.24]),
        linha([_campo("Aspecto Macroscópico:", dados.get("aspecto_macroscopico"), est)], [largura]),
        linha([_campo("Aspecto Microscópico:", dados.get("aspecto_microscopico"), est)], [largura]),
        linha([_campo("Diagnóstico Histopatológico:", dados.get("diagnostico_histopatologico"), est),
               _campo("Patologista Responsável:", dados.get("patologista"), est)],
              [largura * 0.6, largura * 0.4]),
    ]

    # Observações: só entra no PDF se tiver conteúdo
    if str(dados.get("observacoes", "")).strip():
        blocos.append(
            linha([_campo("Observações:", dados.get("observacoes"), est)], [largura])
        )

    for b in blocos:
        story.append(b)
        story.append(Spacer(1, 2 * mm))

    # ── Texto padrão de rodapé (após Observações) ──────────────────────────
    story.append(Spacer(1, 3 * mm))
    story.append(Paragraph(TEXTO_RODAPE, est["rodape"]))

    # ── Campo de Assinatura (espaço + linha para assinar) ──────────────────
    story.append(Spacer(1, 14 * mm))  # espaço para colar/assinar
    assinatura = Table(
        [[""], [Paragraph("Assinatura", est["assinatura"])]],
        colWidths=[largura * 0.6],
    )
    assinatura.setStyle(TableStyle([
        ("LINEABOVE", (0, 1), (0, 1), 0.8, colors.HexColor("#333333")),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 1), (0, 1), 2),
    ]))
    wrap_ass = Table([[assinatura]], colWidths=[largura])
    wrap_ass.setStyle(TableStyle([("ALIGN", (0, 0), (-1, -1), "CENTER")]))
    story.append(wrap_ass)

    # ── VERSO (só se houver imagens) ───────────────────────────────────────
    if _tem_imagens(imagens):
        imgs = [item for item in imagens if item]
        story.append(PageBreak())
        story.append(Spacer(1, 15 * mm))
        story.append(_montar_verso(imgs, largura, est))
        story.append(Spacer(1, 10 * mm))
        story.append(Paragraph(LEGENDA_VERSO, est["legenda"]))

    doc.build(story)
    buffer.seek(0)
    return buffer.read()


def _celula_imagem(caminho, aumento, largura_celula, altura_img, est):
    """Monta uma célula: imagem + aumento embaixo."""
    try:
        img = RLImage(caminho, width=largura_celula - 8, height=altura_img)
    except Exception:
        img = Paragraph(f"[Imagem não carregada]", est["valor"])
    cap = Paragraph(aumento or "&nbsp;", est["aumento"])
    inner = Table([[img], [cap]], colWidths=[largura_celula])
    inner.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    return inner


def _montar_verso(imgs, largura, est):
    """Layout dinâmico conforme o número de imagens."""
    n = len(imgs)
    estilo_grade = TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ])

    if n == 1:
        cw = largura * 0.7
        cel = _celula_imagem(imgs[0][0], imgs[0][1], cw, 90 * mm, est)
        grade = Table([[cel]], colWidths=[cw])

    elif n == 2:
        cw = largura * 0.48
        cels = [_celula_imagem(p, a, cw, 70 * mm, est) for p, a in imgs]
        grade = Table([cels], colWidths=[cw, cw])

    elif n == 3:
        cw = largura * 0.48
        c1 = _celula_imagem(imgs[0][0], imgs[0][1], cw, 60 * mm, est)
        c2 = _celula_imagem(imgs[1][0], imgs[1][1], cw, 60 * mm, est)
        c3 = _celula_imagem(imgs[2][0], imgs[2][1], cw, 60 * mm, est)
        # terceira centralizada (ocupa as duas colunas)
        grade = Table([[c1, c2], [c3, ""]], colWidths=[cw, cw])
        estilo_grade.add("SPAN", (0, 1), (1, 1))

    else:  # 4
        cw = largura * 0.48
        c = [_celula_imagem(p, a, cw, 55 * mm, est) for p, a in imgs[:4]]
        grade = Table([[c[0], c[1]], [c[2], c[3]]], colWidths=[cw, cw])

    grade.setStyle(estilo_grade)

    # centraliza a grade na página
    wrapper = Table([[grade]], colWidths=[largura])
    wrapper.setStyle(TableStyle([("ALIGN", (0, 0), (-1, -1), "CENTER")]))
    return wrapper


if __name__ == "__main__":
    exemplo = {
        "num_registro": "34803", "data": "22/05/2026",
        "nome": "Jessica Cardoso Menezes", "endereco_paciente": "Viamão/RS",
        "idade": "34", "genero": "Feminino", "raca": "NI", "profissao": "NI",
        "titulacao": "CD", "cirurgiao": "Fernanda Visioli",
        "endereco_cirurgiao": "UFRGS", "convenio": "SUS",
        "historia_clinica": "Paciente teve grave infecção nos rins e tomou antibiótico que afrouxou os dentes.",
        "fumo": "Não", "alcool": "Não",
        "diagnostico_clinico": "Hiperplasia inflamatória",
        "localizacao": "Língua, bordo direito", "tipo_biopsia": "Excisional",
        "aspecto_macroscopico": "01 fragmento de tecido mole, consistência fibrosa, coloração branca, forma e superfície irregulares, medindo 23x15x10 mm.",
        "aspecto_microscopico": "Os cortes histopatológicos mostram fragmento de mucosa bucal contendo tecido conjuntivo com deposição de fibras colágenas e infiltrado inflamatório crônico.",
        "diagnostico_histopatologico": "Hiperplasia inflamatória",
        "patologista": "Natália Daroit", "observacoes": "",
    }
    # teste sem imagens
    pdf = gerar_laudo_pdf(exemplo, [])
    with open("teste_sem_verso.pdf", "wb") as f:
        f.write(pdf)
    print("Gerado teste_sem_verso.pdf (só frente)")

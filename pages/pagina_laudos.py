import streamlit as st
import uuid
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import banco
from laudo_pdf import gerar_laudo_pdf

PASTA_IMAGENS = Path(__file__).parent.parent / "dados" / "imagens"
PASTA_IMAGENS.mkdir(parents=True, exist_ok=True)

# localiza os logos (procura na pasta do programa)
def _achar_arquivo(nomes):
    for nome in nomes:
        p = Path(__file__).parent.parent / nome
        if p.exists():
            return str(p)
    return None

# logo grande (login + topo do laudo + PDF)
LOGO = _achar_arquivo(("Logo-Odonto-UFRGS.png", "logo-odonto-ufrgs.png", "logo.png"))

OPC_GENERO  = ["", "Feminino", "Masculino", "NI"]
OPC_BIOPSIA = ["", "Incisional", "Excisional", "Punch", "Citológica", "Outra"]

# campos editáveis no formulário (origem não é editável)
CAMPOS_FORM = [c for c in banco.CAMPOS if c != "origem"]


# ═════════════════════════════════════════════════════════════════════════════
# LOGIN
# ═════════════════════════════════════════════════════════════════════════════

USUARIOS = {
    "mariana":  {"senha": "ufrgs2026", "nome": "Profa. Mariana"},
    "pantelis": {"senha": "grecia",    "nome": "Prof. Pantelis"},
    "victor":   {"senha": "victor123", "nome": "Victor"},
}

if "usuario_logado" not in st.session_state:
    st.session_state.usuario_logado = None

if st.session_state.usuario_logado is None:
    # logo centralizado acima do título
    if LOGO:
        c1, c2, c3 = st.columns([1, 2, 1])
        with c2:
            st.image(LOGO, width='stretch')
    st.title("🔒 Laudos Histopatológicos – UFRGS")
    with st.form("login"):
        u = st.text_input("Usuário:")
        s = st.text_input("Senha:", type="password")
        if st.form_submit_button("Entrar", type="primary"):
            if u in USUARIOS and USUARIOS[u]["senha"] == s:
                st.session_state.usuario_logado = USUARIOS[u]["nome"]
                st.rerun()
            else:
                st.error("Usuário ou senha incorretos.")
    st.stop()


# ═════════════════════════════════════════════════════════════════════════════
# ESTADO + AÇÕES
# ═════════════════════════════════════════════════════════════════════════════

if "laudo_uuid" not in st.session_state:
    st.session_state.laudo_uuid = str(uuid.uuid4())


def novo_laudo():
    st.session_state.laudo_uuid = str(uuid.uuid4())
    for k in CAMPOS_FORM:
        st.session_state.pop(k, None)
    # desmarca os checkboxes de foto
    st.session_state["chk_foto_clinica"] = False
    st.session_state["chk_foto_biopsia"] = False
    st.session_state.imagens_verso = []


def carregar(uuid_):
    dados = banco.carregar_laudo(uuid_)
    if not dados:
        return
    st.session_state.laudo_uuid = uuid_
    for k in CAMPOS_FORM:
        st.session_state[k] = dados.get(k, "") or ""
    # sincroniza os checkboxes de foto (banco guarda "0"/"1")
    st.session_state["chk_foto_clinica"] = (str(dados.get("tem_foto_clinica", "")) == "1")
    st.session_state["chk_foto_biopsia"] = (str(dados.get("tem_foto_biopsia", "")) == "1")
    # garante que valores de selectbox fora da lista não quebrem o widget
    if st.session_state.get("genero", "") not in OPC_GENERO:
        OPC_GENERO.append(st.session_state["genero"])
    if st.session_state.get("tipo_biopsia", "") not in OPC_BIOPSIA:
        OPC_BIOPSIA.append(st.session_state["tipo_biopsia"])


def salvar():
    uuid_ = st.session_state.laudo_uuid
    num = str(st.session_state.get("num_registro", "")).strip()
    if not num:
        st.session_state._msg = ("erro", "O número de registro é obrigatório.")
        return
    if banco.num_registro_existe(num, uuid_):
        st.session_state._msg = ("erro", f"Já existe um laudo com o registro {num}.")
        return

    novo = banco.carregar_laudo(uuid_) is None
    dados = {c: str(st.session_state.get(c, "")) for c in CAMPOS_FORM}
    # checkboxes de foto → "0"/"1"
    dados["tem_foto_clinica"] = "1" if st.session_state.get("chk_foto_clinica") else "0"
    dados["tem_foto_biopsia"] = "1" if st.session_state.get("chk_foto_biopsia") else "0"
    dados["origem"] = "manual"
    banco.salvar_laudo(uuid_, dados)
    banco.registrar_log(st.session_state.usuario_logado, "criou" if novo else "editou", num)
    st.session_state._msg = ("ok", f"Laudo {num} salvo!")


# ═════════════════════════════════════════════════════════════════════════════
# SIDEBAR — busca (50 mais recentes + busca por digitação)
# ═════════════════════════════════════════════════════════════════════════════

with st.sidebar:
    st.markdown(f"👤 **{st.session_state.usuario_logado}**")
    if st.button("Sair", width='stretch'):
        st.session_state.usuario_logado = None
        st.rerun()
    st.markdown("---")

    total = banco.contar()
    st.markdown("### 🔍 Buscar Laudo")
    busca = st.text_input(
        "Nome, registro, data ou diagnóstico:",
        label_visibility="collapsed",
        placeholder="Digite para buscar...",
        key="busca_texto",
    )

    # ── Paginação ──────────────────────────────────────────────────────────
    POR_PAGINA = 25
    if "pagina" not in st.session_state:
        st.session_state.pagina = 1

    # reseta para página 1 quando o termo de busca muda
    if st.session_state.get("_ultima_busca") != busca:
        st.session_state.pagina = 1
        st.session_state._ultima_busca = busca

    total_resultados = banco.contar_busca(busca)
    total_paginas = max(1, (total_resultados + POR_PAGINA - 1) // POR_PAGINA)
    pagina = min(st.session_state.pagina, total_paginas)

    offset = (pagina - 1) * POR_PAGINA
    resultados = banco.buscar(busca, limite=POR_PAGINA, offset=offset)

    if busca.strip():
        st.caption(f"{total_resultados} resultado(s) para “{busca}” · pág. {pagina}/{total_paginas}")
    else:
        st.caption(f"{total} laudos · pág. {pagina}/{total_paginas} (por nº de registro)")

    with st.container(border=True, height=400):
        if not resultados:
            st.caption("Nenhum laudo encontrado.")
        else:
            for r in resultados:
                rotulo = f"**Nº {r.get('num_registro','') or '—'}** — {r.get('nome','') or '(sem nome)'}"
                st.button(
                    rotulo, key=f"load_{r['uuid']}",
                    on_click=carregar, args=(r["uuid"],),
                    width='stretch',
                )

    # ── Controles de página ────────────────────────────────────────────────
    def ir_pagina(p):
        st.session_state.pagina = p

    if total_paginas > 1:
        c1, c2, c3 = st.columns([1, 2, 1])
        with c1:
            st.button("‹", disabled=(pagina <= 1),
                      on_click=ir_pagina, args=(pagina - 1,), width='stretch')
        with c2:
            # seletor direto de página
            nova = st.number_input(
                "pág", min_value=1, max_value=total_paginas, value=pagina,
                step=1, label_visibility="collapsed", key="sel_pagina",
            )
            if nova != pagina:
                st.session_state.pagina = int(nova)
                st.rerun()
        with c3:
            st.button("›", disabled=(pagina >= total_paginas),
                      on_click=ir_pagina, args=(pagina + 1,), width='stretch')
        st.caption(f"Página {pagina} de {total_paginas}")

    st.markdown("---")
    st.caption("Laudos Histopatológicos · v2.3")


# ═════════════════════════════════════════════════════════════════════════════
# CABEÇALHO
# ═════════════════════════════════════════════════════════════════════════════

# logo acima do título principal
if LOGO:
    cl1, cl2, cl3 = st.columns([1, 2, 1])
    with cl2:
        st.image(LOGO, width='stretch')

col_t, col_b = st.columns([4, 1])
with col_t:
    st.title("Laudo de Exame Histopatológico")
with col_b:
    st.write("")
    st.button("➕ Novo Laudo", on_click=novo_laudo, width='stretch')

# mensagem de feedback
msg = st.session_state.pop("_msg", None)
if msg:
    tipo, texto = msg
    (st.success if tipo == "ok" else st.error)(texto)

st.markdown("---")


# ═════════════════════════════════════════════════════════════════════════════
# ABAS
# ═════════════════════════════════════════════════════════════════════════════

tab_dados, tab_imagens, tab_pdf = st.tabs([
    "📝 Dados do Laudo", "🖼️ Imagens (Verso)", "📄 Gerar PDF"
])


# ── ABA 1 — DADOS ──────────────────────────────────────────────────────────
with tab_dados:
    st.markdown("### Identificação")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.text_input("Número de Registro: *", key="num_registro")
    with c2:
        st.text_input("Data:", key="data", placeholder="DD/MM/AAAA")
    with c3:
        st.text_input("Convênio:", key="convenio")

    st.markdown("### Paciente")
    c1, c2 = st.columns([2, 2])
    with c1:
        st.text_input("Nome do Paciente:", key="nome")
    with c2:
        st.text_input("Endereço do Paciente:", key="endereco_paciente")

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.text_input("Idade:", key="idade")
    with c2:
        if "genero" not in st.session_state:
            st.session_state["genero"] = ""
        st.selectbox("Gênero:", OPC_GENERO, key="genero")
    with c3:
        st.text_input("Raça:", key="raca")
    with c4:
        st.text_input("Profissão:", key="profissao")

    st.markdown("### Cirurgião")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.text_input("Titulação:", key="titulacao")
    with c2:
        st.text_input("Nome do Cirurgião:", key="cirurgiao")
    with c3:
        st.text_input("Endereço do Cirurgião:", key="endereco_cirurgiao")

    st.markdown("### História Clínica")
    st.text_area("História Clínica:", key="historia_clinica", height=80)
    c1, c2 = st.columns(2)
    with c1:
        st.text_input("Fumo:", key="fumo")
    with c2:
        st.text_input("Álcool:", key="alcool")

    st.markdown("### Exame")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.text_input("Diagnóstico Clínico:", key="diagnostico_clinico")
    with c2:
        st.text_input("Localização Anatômica:", key="localizacao")
    with c3:
        if "tipo_biopsia" not in st.session_state:
            st.session_state["tipo_biopsia"] = ""
        st.selectbox("Tipo de Biópsia:", OPC_BIOPSIA, key="tipo_biopsia")

    st.text_area("Aspecto Macroscópico:", key="aspecto_macroscopico", height=100)
    st.text_area("Aspecto Microscópico:", key="aspecto_microscopico", height=140)

    st.markdown("### Diagnóstico")
    st.text_input("Diagnóstico Histopatológico:", key="diagnostico_histopatologico")
    st.text_input("Patologista Responsável:", key="patologista")
    st.text_area("Observações:", key="observacoes", height=60)

    # ── Registro de fotos (controle de acervo) ─────────────────────────────
    st.markdown("### Acervo de Fotos")
    st.caption("Marque se este caso possui fotos guardadas (ex: no HD externo da patologia).")
    cfa, cfb = st.columns(2)
    with cfa:
        if "chk_foto_clinica" not in st.session_state:
            st.session_state["chk_foto_clinica"] = False
        st.checkbox("📷 Tem foto clínica", key="chk_foto_clinica")
    with cfb:
        if "chk_foto_biopsia" not in st.session_state:
            st.session_state["chk_foto_biopsia"] = False
        st.checkbox("🔬 Tem foto da biópsia", key="chk_foto_biopsia")

    st.markdown("---")
    st.button("💾 Salvar Laudo", on_click=salvar, type="primary", key="save_dados", width='stretch')


# ── ABA 2 — IMAGENS DO VERSO ────────────────────────────────────────────────
with tab_imagens:
    st.markdown("### Fotomicrografias (Verso)")
    st.caption("Até 4 imagens. O verso só é gerado se houver imagens. Informe o aumento de cada uma.")

    if "imagens_verso" not in st.session_state:
        st.session_state.imagens_verso = []

    def _otimizar_imagem(raw_bytes: bytes) -> bytes:
        """Reduz a imagem para no máx. 1400px no maior lado (leve, sem travar)."""
        from io import BytesIO
        from PIL import Image
        try:
            im = Image.open(BytesIO(raw_bytes))
            im = im.convert("RGB")
            im.thumbnail((1400, 1400))  # mantém proporção
            out = BytesIO()
            im.save(out, format="JPEG", quality=85)
            return out.getvalue()
        except Exception:
            return raw_bytes  # se falhar, usa o original

    up = st.file_uploader("Adicionar imagens (PNG/JPG):", type=["png", "jpg", "jpeg"], accept_multiple_files=True)
    if up:
        for f in up:
            if len(st.session_state.imagens_verso) >= 4:
                st.warning("Máximo de 4 imagens.")
                break
            if not any(x["nome"] == f.name for x in st.session_state.imagens_verso):
                otim = _otimizar_imagem(f.getvalue())
                st.session_state.imagens_verso.append({"nome": f.name, "bytes": otim, "aumento": ""})

    if st.session_state.imagens_verso:
        cols = st.columns(2)
        for i, img in enumerate(st.session_state.imagens_verso):
            with cols[i % 2]:
                st.image(img["bytes"], width=280)
                img["aumento"] = st.text_input(
                    f"Aumento da imagem {i+1}:",
                    placeholder="Ex: x10, x40, 100x...", key=f"aum_{i}",
                )
                if st.button(f"🗑️ Remover imagem {i+1}", key=f"del_{i}"):
                    st.session_state.imagens_verso.pop(i)
                    st.session_state.pop(f"aum_{i}", None)
                    st.rerun()
    else:
        st.info("Nenhuma imagem adicionada. O verso só é gerado se houver imagens.")


# ── ABA 3 — GERAR PDF ───────────────────────────────────────────────────────
with tab_pdf:
    st.markdown("### Gerar PDF do Laudo")

    if st.button("📄 Gerar PDF", type="primary"):
        dados = {c: st.session_state.get(c, "") for c in CAMPOS_FORM}
        imagens = []
        for i, img in enumerate(st.session_state.get("imagens_verso", [])):
            caminho = PASTA_IMAGENS / f"tmp_{i}_{img['nome']}"
            caminho.write_bytes(img["bytes"])
            imagens.append((str(caminho), img["aumento"]))

        try:
            pdf_bytes = gerar_laudo_pdf(dados, imagens)
            banco.registrar_log(st.session_state.usuario_logado, "gerou PDF", dados.get("num_registro", ""))
            st.download_button(
                "⬇️ Baixar PDF", data=pdf_bytes,
                file_name=f"laudo_{dados.get('num_registro','SN')}.pdf",
                mime="application/pdf",
            )
            st.success("PDF gerado! Clique para baixar.")
        except Exception as e:
            st.error(f"Erro ao gerar o PDF: {e}")


# ── Rodapé discreto com o UUID ──────────────────────────────────────────────
st.markdown("---")
st.caption(f"ID interno do laudo: {st.session_state.laudo_uuid}")

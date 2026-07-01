"""
pagina_cigarro.py — Projeto Cigarro Eletrônico (questionário).

Cadastro de participantes com o questionário do Apêndice C:
identificação, hábitos de cigarro de combustão, cigarro eletrônico,
álcool e histórico de câncer de boca.

Coleta ÚNICA (sem T0/T1/T2).
Banco de dados SEPARADO: fica em dados_cigarro/.
Requer login (feito na página principal).
"""

import streamlit as st
import pandas as pd
import uuid
from pathlib import Path
from datetime import date, datetime

# ── Proteção: exige login feito na página principal ─────────────────────────
if not st.session_state.get("usuario_logado"):
    st.warning("🔒 Faça login na página principal (Laudos) para acessar o Cigarro Eletrônico.")
    st.stop()


# ═════════════════════════════════════════════════════════════════════════════
# CONSTANTES E CAMINHOS  (banco SEPARADO, na pasta dados_cigarro/)
# ═════════════════════════════════════════════════════════════════════════════

PASTA_DADOS = Path(__file__).parent.parent / "dados_cigarro"
PASTA_DADOS.mkdir(exist_ok=True)
ARQUIVO = PASTA_DADOS / "participantes.csv"

OPC_GENERO = ["", "Masculino", "Feminino"]
OPC_GRUPO  = ["", "Controle", "Desordem potencialmente maligna bucal", "Carcinoma Espinocelular"]
OPC_SIMNAO = ["", "Sim", "Não"]

# ── Campos persistidos (todos do questionário) ──────────────────────────────
CAMPOS = [
    # identificação
    "num_registro", "grupo", "pesquisador", "data_coleta",
    "genero", "data_nascimento",
    # cigarro de combustão — atual
    "comb_atual", "comb_atual_tipo", "comb_atual_qtd", "comb_atual_tempo",
    # cigarro de combustão — anterior
    "comb_ant", "comb_ant_tipo", "comb_ant_qtd", "comb_ant_tempo_fumou", "comb_ant_parou",
    # cigarro eletrônico — atual
    "elet_atual", "elet_atual_tipo", "elet_atual_freq", "elet_atual_tempo",
    # cigarro eletrônico — anterior
    "elet_ant", "elet_ant_tipo", "elet_ant_freq", "elet_ant_tempo_fumou", "elet_ant_parou",
    # álcool — atual
    "alc_atual", "alc_atual_tipo", "alc_atual_tempo", "alc_atual_qtd",
    # álcool — anterior
    "alc_ant", "alc_ant_tipo", "alc_ant_qtd", "alc_ant_tempo_uso", "alc_ant_parou",
    # histórico
    "hist_cancer", "hist_cancer_tempo",
]


# ═════════════════════════════════════════════════════════════════════════════
# HELPERS
# ═════════════════════════════════════════════════════════════════════════════

def calcular_idade(data_str: str):
    if not data_str:
        return None
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
        try:
            nasc = datetime.strptime(data_str.strip(), fmt).date()
            hoje = date.today()
            return hoje.year - nasc.year - ((hoje.month, hoje.day) < (nasc.month, nasc.day))
        except ValueError:
            continue
    return None


def safe_index(lista: list, valor: str) -> int:
    try:
        return lista.index(valor) if valor else 0
    except ValueError:
        return 0


# ═════════════════════════════════════════════════════════════════════════════
# PERSISTÊNCIA (CSV)
# ═════════════════════════════════════════════════════════════════════════════

def ler() -> pd.DataFrame:
    if ARQUIVO.exists():
        return pd.read_csv(ARQUIVO, dtype=str, keep_default_na=False)
    return pd.DataFrame(columns=["uuid"] + CAMPOS)


def salvar():
    df = ler()
    uuid_atual = st.session_state.cig_uuid
    dados = {"uuid": uuid_atual}
    for k in CAMPOS:
        dados[k] = str(st.session_state.get(k, ""))

    if not df.empty and uuid_atual in df["uuid"].values:
        idx = df[df["uuid"] == uuid_atual].index[0]
        for k, v in dados.items():
            df.at[idx, k] = v
    else:
        df = pd.concat([df, pd.DataFrame([dados])], ignore_index=True)

    df.to_csv(ARQUIVO, index=False, encoding="utf-8-sig")
    st.toast("✅ Dados salvos!", icon="💾")


def carregar(uuid_):
    df = ler()
    row = df[df["uuid"] == uuid_]
    if row.empty:
        return
    row = row.iloc[0]
    st.session_state.cig_uuid = uuid_
    for k in CAMPOS:
        st.session_state[k] = row.get(k, "") or ""


# ═════════════════════════════════════════════════════════════════════════════
# ESTADO INICIAL
# ═════════════════════════════════════════════════════════════════════════════

if "cig_uuid" not in st.session_state:
    st.session_state.cig_uuid = str(uuid.uuid4())


def novo_participante():
    st.session_state.cig_uuid = str(uuid.uuid4())
    for k in CAMPOS:
        st.session_state.pop(k, None)


# ═════════════════════════════════════════════════════════════════════════════
# SIDEBAR — busca de participantes
# ═════════════════════════════════════════════════════════════════════════════

with st.sidebar:
    df = ler()

    st.markdown("### 🔍 Buscar Participante")
    busca = st.text_input(
        "Nº de registro ou UUID:", key="cig_busca",
        label_visibility="collapsed", placeholder="Nº registro ou UUID",
    )

    st.markdown(f"##### Participantes ({len(df)})")
    with st.container(border=True, height=420):
        df_filt = df
        if busca and not df.empty:
            mask = (
                df["num_registro"].str.contains(busca, case=False, na=False)
                | df["uuid"].str.contains(busca, case=False, na=False)
            )
            df_filt = df[mask]

        if df_filt.empty:
            st.caption("Nenhum participante.")
        else:
            for _, row in df_filt.iterrows():
                num = row.get("num_registro", "") or "(sem nº)"
                grupo = row.get("grupo", "") or "—"
                st.button(
                    f"**Nº {num}**\n\n`{grupo}`",
                    key=f"cig_load_{row['uuid']}",
                    on_click=carregar,
                    args=(row["uuid"],),
                    width='stretch',
                )

    st.markdown("---")
    st.caption("Projeto Cigarro Eletrônico · v1.0")


# ═════════════════════════════════════════════════════════════════════════════
# CABEÇALHO
# ═════════════════════════════════════════════════════════════════════════════

st.title("💨 Cigarro Eletrônico")
st.caption(f"🆔 UUID do participante: `{st.session_state.cig_uuid}`")

col1, col2, col3 = st.columns([2, 1, 1])
with col1:
    st.write("")
    st.write("")
with col2:
    st.write("")
    st.write("")
    st.button("💾 Salvar", on_click=salvar, type="primary", key="save_top", width='stretch')
with col3:
    st.write("")
    st.write("")
    st.button("➕ Novo Participante", on_click=novo_participante, width='stretch')

st.markdown("---")


# ═════════════════════════════════════════════════════════════════════════════
# QUESTIONÁRIO
# ═════════════════════════════════════════════════════════════════════════════

# ── Identificação ───────────────────────────────────────────────────────────
st.markdown("### 📋 Identificação")
col1, col2, col3, col4 = st.columns([1.3, 1.3, 1.3, 0.8])
with col1:
    st.text_input("Participante (nº de registro):", key="num_registro")
    st.text_input("Pesquisador:", key="pesquisador")
with col2:
    st.selectbox("Grupo:", OPC_GRUPO,
                 index=safe_index(OPC_GRUPO, st.session_state.get("grupo", "")),
                 key="grupo")
    st.text_input("Data da coleta:", key="data_coleta", placeholder="DD/MM/AAAA")
with col3:
    st.selectbox("Gênero:", OPC_GENERO,
                 index=safe_index(OPC_GENERO, st.session_state.get("genero", "")),
                 key="genero")
    st.text_input("Data de nascimento:", key="data_nascimento", placeholder="DD/MM/AAAA")
with col4:
    st.write("")  # alinha com o gênero acima
    st.write("")
    idade = calcular_idade(st.session_state.get("data_nascimento", ""))
    idade_txt = f"{idade} anos" if idade is not None else "—"
    st.markdown("**Idade:**")
    st.info(idade_txt)

st.markdown("---")

# ── Cigarro de combustão — ATUAL ────────────────────────────────────────────
st.markdown("### 🚬 Cigarro de combustão (atualmente)")
st.selectbox("Você fuma cigarro de combustão atualmente?", OPC_SIMNAO,
             index=safe_index(OPC_SIMNAO, st.session_state.get("comb_atual", "")),
             key="comb_atual")
if st.session_state.get("comb_atual") == "Sim":
    col1, col2, col3 = st.columns(3)
    with col1:
        st.text_input("Tipo:", key="comb_atual_tipo")
    with col2:
        st.text_input("Quantos cigarros por dia?", key="comb_atual_qtd")
    with col3:
        st.text_input("Há quanto tempo?", key="comb_atual_tempo")
else:
    for k in ("comb_atual_tipo", "comb_atual_qtd", "comb_atual_tempo"):
        st.session_state[k] = ""

# ── Cigarro de combustão — ANTERIOR ─────────────────────────────────────────
st.markdown("### 🚬 Cigarro de combustão (anteriormente)")
st.selectbox("Você já fumou cigarro de combustão anteriormente?", OPC_SIMNAO,
             index=safe_index(OPC_SIMNAO, st.session_state.get("comb_ant", "")),
             key="comb_ant")
if st.session_state.get("comb_ant") == "Sim":
    col1, col2 = st.columns(2)
    with col1:
        st.text_input("Tipo:", key="comb_ant_tipo")
        st.text_input("Quantos cigarros por dia?", key="comb_ant_qtd")
    with col2:
        st.text_input("Por quanto tempo fumou?", key="comb_ant_tempo_fumou")
        st.text_input("Parou há quanto tempo?", key="comb_ant_parou")
else:
    for k in ("comb_ant_tipo", "comb_ant_qtd", "comb_ant_tempo_fumou", "comb_ant_parou"):
        st.session_state[k] = ""

st.markdown("---")

# ── Cigarro eletrônico — ATUAL ──────────────────────────────────────────────
st.markdown("### 💨 Cigarro eletrônico (atualmente)")
st.selectbox("Você fuma cigarro eletrônico atualmente?", OPC_SIMNAO,
             index=safe_index(OPC_SIMNAO, st.session_state.get("elet_atual", "")),
             key="elet_atual")
if st.session_state.get("elet_atual") == "Sim":
    col1, col2, col3 = st.columns(3)
    with col1:
        st.text_input("Tipo:", key="elet_atual_tipo")
    with col2:
        st.text_input("Qual a frequência?", key="elet_atual_freq")
    with col3:
        st.text_input("Há quanto tempo?", key="elet_atual_tempo")
else:
    for k in ("elet_atual_tipo", "elet_atual_freq", "elet_atual_tempo"):
        st.session_state[k] = ""

# ── Cigarro eletrônico — ANTERIOR ───────────────────────────────────────────
st.markdown("### 💨 Cigarro eletrônico (anteriormente)")
st.selectbox("Você já fumou cigarro eletrônico anteriormente?", OPC_SIMNAO,
             index=safe_index(OPC_SIMNAO, st.session_state.get("elet_ant", "")),
             key="elet_ant")
if st.session_state.get("elet_ant") == "Sim":
    col1, col2 = st.columns(2)
    with col1:
        st.text_input("Tipo:", key="elet_ant_tipo")
        st.text_input("Qual a frequência?", key="elet_ant_freq")
    with col2:
        st.text_input("Por quanto tempo fumou?", key="elet_ant_tempo_fumou")
        st.text_input("Parou há quanto tempo?", key="elet_ant_parou")
else:
    for k in ("elet_ant_tipo", "elet_ant_freq", "elet_ant_tempo_fumou", "elet_ant_parou"):
        st.session_state[k] = ""

st.markdown("---")

# ── Álcool — ATUAL ──────────────────────────────────────────────────────────
st.markdown("### 🍺 Bebida alcoólica (atualmente)")
st.selectbox("Você ingere bebida alcoólica atualmente?", OPC_SIMNAO,
             index=safe_index(OPC_SIMNAO, st.session_state.get("alc_atual", "")),
             key="alc_atual")
if st.session_state.get("alc_atual") == "Sim":
    col1, col2, col3 = st.columns(3)
    with col1:
        st.text_input("Tipo:", key="alc_atual_tipo")
    with col2:
        st.text_input("Há quanto tempo faz uso?", key="alc_atual_tempo")
    with col3:
        st.text_input("Quanto bebe por dia ou semana?", key="alc_atual_qtd")
else:
    for k in ("alc_atual_tipo", "alc_atual_tempo", "alc_atual_qtd"):
        st.session_state[k] = ""

# ── Álcool — ANTERIOR ───────────────────────────────────────────────────────
st.markdown("### 🍺 Bebida alcoólica (anteriormente)")
st.selectbox("Você já ingeriu bebida alcoólica anteriormente?", OPC_SIMNAO,
             index=safe_index(OPC_SIMNAO, st.session_state.get("alc_ant", "")),
             key="alc_ant")
if st.session_state.get("alc_ant") == "Sim":
    col1, col2 = st.columns(2)
    with col1:
        st.text_input("Tipo:", key="alc_ant_tipo")
        st.text_input("Quanto bebia por dia ou semana?", key="alc_ant_qtd")
    with col2:
        st.text_input("Por quanto tempo fez uso?", key="alc_ant_tempo_uso")
        st.text_input("Parou há quanto tempo?", key="alc_ant_parou")
else:
    for k in ("alc_ant_tipo", "alc_ant_qtd", "alc_ant_tempo_uso", "alc_ant_parou"):
        st.session_state[k] = ""

st.markdown("---")

# ── Histórico ───────────────────────────────────────────────────────────────
st.markdown("### 🏥 Histórico")
st.selectbox("Tem histórico de câncer de boca?", OPC_SIMNAO,
             index=safe_index(OPC_SIMNAO, st.session_state.get("hist_cancer", "")),
             key="hist_cancer")
if st.session_state.get("hist_cancer") == "Sim":
    st.text_input("Se sim, há quanto tempo?", key="hist_cancer_tempo")
else:
    st.session_state["hist_cancer_tempo"] = ""

st.markdown("---")
st.button("💾 Salvar", on_click=salvar, type="primary", key="save_bottom", width='stretch')
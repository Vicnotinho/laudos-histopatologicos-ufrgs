"""
pagina_longitudinal.py — Projeto Longitudinal (citologia — Nathalia).

Estudo longitudinal: pacientes com múltiplas coletas ao longo do tempo,
com análises Papanicolaou, AgNOR (convencional e meio líquido), imagens
clínicas e um modelo multicategórico de risco.

Banco de dados SEPARADO dos Laudos: fica em dados_longitudinal/.
Requer login (feito na página principal).
"""

import streamlit as st
import pandas as pd
import uuid
from pathlib import Path
from datetime import date, datetime

# ── Proteção: exige login feito na página principal ─────────────────────────
if not st.session_state.get("usuario_logado"):
    st.warning("🔒 Faça login na página principal (Laudos) para acessar o Longitudinal.")
    st.stop()


# ═════════════════════════════════════════════════════════════════════════════
# CONSTANTES E CAMINHOS  (banco SEPARADO, na pasta dados_longitudinal/)
# ═════════════════════════════════════════════════════════════════════════════

PASTA_DADOS = Path(__file__).parent.parent / "dados_longitudinal"
PASTA_DADOS.mkdir(exist_ok=True)
ARQUIVO_PACIENTES = PASTA_DADOS / "pacientes.csv"
ARQUIVO_COLETAS   = PASTA_DADOS / "coletas.csv"

# ── Opções dos comboboxes ─────────────────────────────────────────────────
OPC_GENERO     = ["", "Feminino", "Masculino"]
OPC_FUMA       = ["", "Não", "Sim", "Ex-fumante"]
OPC_BEBE       = ["", "Bebe", "Não bebe", "Não bebe mais"]
OPC_GRUPO      = ["", "Controle", "Desordem potencialmente maligna bucal", "Carcinoma Espinocelular"]
OPC_LESAO      = [
    "",
    "Placa branca",
    "Placa branca com áreas eritroplásicas ulceradas",
    "Placa branca/avermelhada onde teve CECB há 15 anos",
    "Placa branca delgada",
    "Região eritematosa",
    "Eritroplasia",
]
OPC_LOCALIZACAO = [
    "",
    "Dorso da língua",
    "Assoalho da boca",
    "Borda da língua",
    "Língua",
]
OPC_SUPERFICIE = ["", "Homogênea", "Não homogênea"]
OPC_COR        = ["", "Branca", "Mista", "Avermelhada"]

# ── Campos persistidos ─────────────────────────────────────────────────────
CAMPOS_PACIENTE = ["nome", "data_nascimento", "telefone", "genero", "registros_paciente"]

CAMPOS_COLETA = [
    "num_registro", "data_coleta", "grupo", "tempo_anterior",
    # hábitos
    "fuma", "cigarros_por_dia", "bebe", "latas_por_dia",
    # lesão
    "lesao_clinica",
    "localizacao_1", "localizacao_2", "localizacao_3",
    "superficie", "cor",
    # papa convencional
    "papac_data", "papac_reg", "papac_drive",
    "papac_anu", "papac_sup", "papac_int", "papac_agn",
    "papac_ags", "papac_bin", "papac_par",
    # papa líquido
    "papal_data", "papal_reg", "papal_drive",
    "papal_anu", "papal_sup", "papal_int", "papal_agn",
    "papal_ags", "papal_bin", "papal_par",
    # agnor convencional
    "agnorc_data", "agnorc_reg", "agnorc_drive",
    "agnorc_nn", "agnorc_na", "agnorc_nc", "agnorc_ns",
    "agnorc_mpn", "agnorc_mtn", "agnorc_mta",
    "agnorc_mtnor", "agnorc_mts",
    "agnorc_e1", "agnorc_e2", "agnorc_e3", "agnorc_e4", "agnorc_e5",
    # agnor líquido
    "agnorl_data", "agnorl_reg", "agnorl_drive",
    "agnorl_nn", "agnorl_na", "agnorl_nc", "agnorl_ns",
    "agnorl_mpn", "agnorl_mtn", "agnorl_mta",
    "agnorl_mtnor", "agnorl_mts",
    "agnorl_e1", "agnorl_e2", "agnorl_e3", "agnorl_e4", "agnorl_e5",
    # imagens
    "img_data", "img_reg", "img_drive",
    "img_obs_lin", "img_obs_ass", "img_obs_muc",
    "img_obs_pal", "img_obs_lab", "img_obs_out",
    # multicategórico (citologia + histologia ficam aqui)
    "mc_papa", "mc_agnor", "mc_displasia",
]


# ═════════════════════════════════════════════════════════════════════════════
# HELPERS
# ═════════════════════════════════════════════════════════════════════════════

def calcular_idade(data_str: str):
    """Aceita DD/MM/AAAA e retorna a idade em anos, ou None se inválido."""
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
    """Retorna o índice do valor na lista, ou 0 se não encontrar."""
    try:
        return lista.index(valor) if valor else 0
    except ValueError:
        return 0


# ═════════════════════════════════════════════════════════════════════════════
# PERSISTÊNCIA (CSV)
# ═════════════════════════════════════════════════════════════════════════════

def ler_pacientes() -> pd.DataFrame:
    if ARQUIVO_PACIENTES.exists():
        return pd.read_csv(ARQUIVO_PACIENTES, dtype=str, keep_default_na=False)
    return pd.DataFrame(columns=["uuid"] + CAMPOS_PACIENTE)


def ler_coletas() -> pd.DataFrame:
    if ARQUIVO_COLETAS.exists():
        return pd.read_csv(ARQUIVO_COLETAS, dtype=str, keep_default_na=False)
    return pd.DataFrame(columns=["uuid_paciente", "t"] + CAMPOS_COLETA)


def calcular_registros_do_paciente(uuid_, df_coletas=None) -> str:
    df_c = df_coletas if df_coletas is not None else ler_coletas()
    coletas = df_c[df_c["uuid_paciente"] == uuid_]
    if coletas.empty:
        return ""
    coletas = coletas.copy()
    coletas["t_num"] = pd.to_numeric(coletas["t"], errors="coerce").fillna(0).astype(int)
    coletas = coletas.sort_values("t_num")
    nums = [str(n).strip() for n in coletas["num_registro"].tolist() if str(n).strip()]
    return ", ".join(nums)


def salvar():
    """Salva o paciente atual + a coleta atual nos CSVs."""
    uuid_atual = st.session_state.long_paciente_uuid
    t_atual    = str(st.session_state.long_coleta_atual)

    # Coletas primeiro (para recalcular registros depois)
    df_c = ler_coletas()
    dados_c = {"uuid_paciente": uuid_atual, "t": t_atual}
    for k in CAMPOS_COLETA:
        dados_c[k] = str(st.session_state.get(k, ""))

    if not df_c.empty:
        mask = (df_c["uuid_paciente"] == uuid_atual) & (df_c["t"] == t_atual)
        existentes = df_c[mask]
        if not existentes.empty:
            idx = existentes.index[0]
            for k, v in dados_c.items():
                df_c.at[idx, k] = v
        else:
            df_c = pd.concat([df_c, pd.DataFrame([dados_c])], ignore_index=True)
    else:
        df_c = pd.DataFrame([dados_c])

    df_c.to_csv(ARQUIVO_COLETAS, index=False, encoding="utf-8-sig")

    # Pacientes
    df_p = ler_pacientes()
    dados_p = {"uuid": uuid_atual}
    for k in CAMPOS_PACIENTE:
        dados_p[k] = str(st.session_state.get(k, ""))
    dados_p["registros_paciente"] = calcular_registros_do_paciente(uuid_atual, df_c)

    if uuid_atual in df_p["uuid"].values:
        idx = df_p[df_p["uuid"] == uuid_atual].index[0]
        for k, v in dados_p.items():
            df_p.at[idx, k] = v
    else:
        df_p = pd.concat([df_p, pd.DataFrame([dados_p])], ignore_index=True)

    df_p.to_csv(ARQUIVO_PACIENTES, index=False, encoding="utf-8-sig")
    st.session_state.registros_paciente = dados_p["registros_paciente"]
    st.toast("✅ Dados salvos!", icon="💾")


def carregar_paciente(uuid_):
    df_p = ler_pacientes()
    row = df_p[df_p["uuid"] == uuid_]
    if row.empty:
        return
    row = row.iloc[0]

    st.session_state.long_paciente_uuid = uuid_
    for k in CAMPOS_PACIENTE:
        st.session_state[k] = row.get(k, "") or ""

    df_c = ler_coletas()
    coletas = df_c[df_c["uuid_paciente"] == uuid_]
    if coletas.empty:
        st.session_state.long_coleta_atual = 0
        for k in CAMPOS_COLETA:
            st.session_state.pop(k, None)
        return

    coletas = coletas.copy()
    coletas["t_num"] = pd.to_numeric(coletas["t"], errors="coerce").fillna(0).astype(int)
    ultima = coletas.sort_values("t_num").iloc[-1]
    st.session_state.long_coleta_atual = int(ultima["t_num"])
    for k in CAMPOS_COLETA:
        st.session_state[k] = ultima.get(k, "") or ""

    # restaura checkboxes/expansões a partir dos dados
    st.session_state.tem_loc2 = bool(st.session_state.get("localizacao_2", ""))
    st.session_state.tem_loc3 = bool(st.session_state.get("localizacao_3", ""))


def carregar_registro(uuid_paciente, t):
    df_p = ler_pacientes()
    row_p = df_p[df_p["uuid"] == uuid_paciente]
    if row_p.empty:
        return
    row_p = row_p.iloc[0]

    st.session_state.long_paciente_uuid = uuid_paciente
    for k in CAMPOS_PACIENTE:
        st.session_state[k] = row_p.get(k, "") or ""

    df_c = ler_coletas()
    mask = (df_c["uuid_paciente"] == uuid_paciente) & (df_c["t"] == str(t))
    row_c = df_c[mask]
    if row_c.empty:
        return
    row_c = row_c.iloc[0]
    st.session_state.long_coleta_atual = int(t)
    for k in CAMPOS_COLETA:
        st.session_state[k] = row_c.get(k, "") or ""

    st.session_state.tem_loc2 = bool(st.session_state.get("localizacao_2", ""))
    st.session_state.tem_loc3 = bool(st.session_state.get("localizacao_3", ""))


# ═════════════════════════════════════════════════════════════════════════════
# ESTADO INICIAL
# ═════════════════════════════════════════════════════════════════════════════

if "long_paciente_uuid" not in st.session_state:
    st.session_state.long_paciente_uuid = str(uuid.uuid4())
if "long_coleta_atual" not in st.session_state:
    st.session_state.long_coleta_atual = 0


def novo_paciente():
    st.session_state.long_paciente_uuid = str(uuid.uuid4())
    st.session_state.long_coleta_atual = 0
    for k in CAMPOS_PACIENTE + CAMPOS_COLETA:
        st.session_state.pop(k, None)
    st.session_state.pop("tem_loc2", None)
    st.session_state.pop("tem_loc3", None)


def nova_coleta():
    st.session_state.long_coleta_atual += 1
    for k in CAMPOS_COLETA:
        st.session_state.pop(k, None)
    st.session_state.pop("tem_loc2", None)
    st.session_state.pop("tem_loc3", None)


# ═════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ═════════════════════════════════════════════════════════════════════════════

with st.sidebar:
    df_pacientes = ler_pacientes()
    df_coletas   = ler_coletas()

    # Atualiza automaticamente os registros do paciente atual
    st.session_state.registros_paciente = calcular_registros_do_paciente(
        st.session_state.long_paciente_uuid, df_coletas
    )

    st.markdown("### 🔍 Buscar Paciente")
    busca_paciente = st.text_input(
        "Nome ou UUID:", key="long_busca_paciente",
        label_visibility="collapsed", placeholder="Nome ou UUID",
    )

    st.markdown(f"##### Pacientes ({len(df_pacientes)})")
    with st.container(border=True, height=260):
        df_p_filt = df_pacientes
        if busca_paciente and not df_pacientes.empty:
            mask = (
                df_pacientes["nome"].str.contains(busca_paciente, case=False, na=False)
                | df_pacientes["uuid"].str.contains(busca_paciente, case=False, na=False)
            )
            df_p_filt = df_pacientes[mask]

        if df_p_filt.empty:
            st.caption("Nenhum paciente.")
        else:
            for _, row in df_p_filt.iterrows():
                nome_exib = row.get("nome", "") or "(sem nome)"
                regs = row.get("registros_paciente", "") or "—"
                st.button(
                    f"**{nome_exib}**\n\n`{regs}`",
                    key=f"long_load_p_{row['uuid']}",
                    on_click=carregar_paciente,
                    args=(row["uuid"],),
                    width='stretch',
                )

    st.markdown("---")

    st.markdown("### 🔍 Buscar Registro")
    busca_registro = st.text_input(
        "Número de registro:", key="long_busca_registro",
        label_visibility="collapsed", placeholder="Ex: 208",
    )

    st.markdown(f"##### Registros ({len(df_coletas)})")
    with st.container(border=True, height=260):
        df_c_filt = df_coletas
        if busca_registro and not df_coletas.empty:
            mask = df_coletas["num_registro"].str.contains(busca_registro, case=False, na=False)
            df_c_filt = df_coletas[mask]

        if df_c_filt.empty:
            st.caption("Nenhum registro.")
        else:
            for _, row in df_c_filt.iterrows():
                num = row.get("num_registro", "") or "(sem nº)"
                t_ = row.get("t", "0")
                nome_p = ""
                if not df_pacientes.empty:
                    rp = df_pacientes[df_pacientes["uuid"] == row["uuid_paciente"]]
                    if not rp.empty:
                        nome_p = rp.iloc[0].get("nome", "") or ""
                rotulo = f"**Nº {num}** — T{t_}" + (f"\n\n{nome_p}" if nome_p else "")
                st.button(
                    rotulo,
                    key=f"long_load_r_{row['uuid_paciente']}_{t_}",
                    on_click=carregar_registro,
                    args=(row["uuid_paciente"], t_),
                    width='stretch',
                )

    st.markdown("---")
    st.caption("Projeto Longitudinal · v4.3")


# ═════════════════════════════════════════════════════════════════════════════
# CABEÇALHO — DADOS FIXOS DO PACIENTE
# ═════════════════════════════════════════════════════════════════════════════

st.title("🔬 Longitudinal")
st.caption(f"🆔 UUID do paciente: `{st.session_state.long_paciente_uuid}`")

# ── Importar dados coletados no tablet (PWA) ────────────────────────────────
with st.expander("📥 Importar dados do tablet (2 arquivos exportados do app)"):
    st.caption(
        "Selecione os DOIS arquivos exportados do aplicativo do tablet: "
        "`longitudinal_pacientes_...csv` e `longitudinal_coletas_...csv`."
    )
    up_pac = st.file_uploader("Arquivo de PACIENTES:", type=["csv"], key="long_up_pac")
    up_col = st.file_uploader("Arquivo de COLETAS:", type=["csv"], key="long_up_col")

    if up_pac is not None and up_col is not None:
        try:
            df_pac_novo = pd.read_csv(up_pac, dtype=str, sep=";", keep_default_na=False)
            df_col_novo = pd.read_csv(up_col, dtype=str, sep=";", keep_default_na=False)
            df_pac_atual = ler_pacientes()
            df_col_atual = ler_coletas()

            uuids_atuais = set(df_pac_atual["uuid"].values) if not df_pac_atual.empty else set()
            novos_pac = df_pac_novo[~df_pac_novo["uuid"].isin(uuids_atuais)]

            st.info(
                f"O arquivo tem **{len(df_pac_novo)}** paciente(s) e "
                f"**{len(df_col_novo)}** coleta(s). "
                f"{len(novos_pac)} paciente(s) novo(s)."
            )
            if st.button("✅ Confirmar importação", type="primary"):
                # pacientes: adiciona novos / atualiza existentes
                df_pac_final = df_pac_atual.copy() if not df_pac_atual.empty else pd.DataFrame(columns=["uuid"] + CAMPOS_PACIENTE)
                for _, linha in df_pac_novo.iterrows():
                    if linha["uuid"] in uuids_atuais:
                        idx = df_pac_final[df_pac_final["uuid"] == linha["uuid"]].index[0]
                        for c in linha.index:
                            df_pac_final.at[idx, c] = linha[c]
                    else:
                        df_pac_final = pd.concat([df_pac_final, pd.DataFrame([linha])], ignore_index=True)
                df_pac_final.to_csv(ARQUIVO_PACIENTES, index=False, encoding="utf-8-sig")

                # coletas: substitui por uuid_paciente + t
                df_col_final = df_col_atual.copy() if not df_col_atual.empty else pd.DataFrame(columns=["uuid_paciente", "t"] + CAMPOS_COLETA)
                for _, linha in df_col_novo.iterrows():
                    if not df_col_final.empty:
                        mask = (df_col_final["uuid_paciente"] == linha["uuid_paciente"]) & (df_col_final["t"] == linha["t"])
                        existente = df_col_final[mask]
                    else:
                        existente = pd.DataFrame()
                    if not existente.empty:
                        idx = existente.index[0]
                        for c in linha.index:
                            df_col_final.at[idx, c] = linha[c]
                    else:
                        df_col_final = pd.concat([df_col_final, pd.DataFrame([linha])], ignore_index=True)
                df_col_final.to_csv(ARQUIVO_COLETAS, index=False, encoding="utf-8-sig")

                st.success(f"✅ Importado! {len(novos_pac)} paciente(s) novo(s) e {len(df_col_novo)} coleta(s).")
                st.rerun()
        except Exception as e:
            st.error(f"Erro ao ler os arquivos: {e}")


col1, col2, col3, col4, col5, col6 = st.columns([3, 1.5, 1.5, 1.5, 1.1, 1.3])
with col1:
    st.text_input("Nome:", key="nome")
with col2:
    st.text_input("Data de nascimento:", key="data_nascimento", placeholder="DD/MM/AAAA")
with col3:
    st.selectbox("Gênero:", OPC_GENERO,
                 index=safe_index(OPC_GENERO, st.session_state.get("genero", "")),
                 key="genero")
with col4:
    st.text_input("Telefone:", key="telefone")
with col5:
    st.write("")
    st.write("")
    st.button("💾 Salvar", on_click=salvar, type="primary", key="save_header", width='stretch')
with col6:
    st.write("")
    st.write("")
    st.button("➕ Novo Paciente", on_click=novo_paciente, width='stretch')

# Idade calculada + lista de registros do paciente
col1, col2 = st.columns([1, 3])
with col1:
    idade = calcular_idade(st.session_state.get("data_nascimento", ""))
    idade_txt = f"{idade} anos" if idade is not None else "—"
    st.markdown("**Idade:**")
    st.info(idade_txt)
with col2:
    st.text_input(
        "Números de registro do paciente:",
        key="registros_paciente",
        disabled=True,
        help="Preenchido automaticamente conforme as coletas são salvas.",
    )

st.markdown("---")


# ═════════════════════════════════════════════════════════════════════════════
# ABAS
# ═════════════════════════════════════════════════════════════════════════════

tab_paciente, tab_papa_c, tab_papa_l, tab_agnor_c, tab_agnor_l, tab_imagens, tab_multi = st.tabs([
    "Dados do Paciente",
    "Análise Papa Convencional",
    "Análise Papa Meio Líquido",
    "AgNOR Convencional",
    "AgNOR Meio Líquido",
    "Imagens",
    "Multicategórico",
])


# ───────────────────────────────────────────────────────────────────────────
# ABA 1 — DADOS DA COLETA
# ───────────────────────────────────────────────────────────────────────────
with tab_paciente:
    coleta_label = f"T{st.session_state.long_coleta_atual}"

    col_titulo, col_botao = st.columns([4, 1])
    with col_titulo:
        st.markdown(f"### Dados da Coleta — **{coleta_label}**")
    with col_botao:
        st.button("➕ Nova Coleta", on_click=nova_coleta, width='stretch')

    col1, col2, col3 = st.columns(3)
    with col1:
        st.text_input("Número de registro:", key="num_registro")
    with col2:
        st.text_input("Data da coleta:", key="data_coleta", placeholder="DD/MM/AAAA")
    with col3:
        st.text_input("Tempo desde a coleta anterior:", key="tempo_anterior", placeholder="Ex: 8 meses")

    st.selectbox(
        "Grupo:", OPC_GRUPO,
        index=safe_index(OPC_GRUPO, st.session_state.get("grupo", "")),
        key="grupo",
    )

    # ── Hábitos ────────────────────────────────────────────────────────────
    st.markdown("### Hábitos")
    col1, col2 = st.columns(2)
    with col1:
        st.selectbox(
            "Fumante:", OPC_FUMA,
            index=safe_index(OPC_FUMA, st.session_state.get("fuma", "")),
            key="fuma",
        )
        if st.session_state.get("fuma") in ("Sim", "Ex-fumante"):
            st.text_input("Quantos cigarros por dia:", key="cigarros_por_dia")
        else:
            st.session_state["cigarros_por_dia"] = ""

    with col2:
        st.selectbox(
            "Álcool:", OPC_BEBE,
            index=safe_index(OPC_BEBE, st.session_state.get("bebe", "")),
            key="bebe",
        )
        if st.session_state.get("bebe") in ("Bebe", "Não bebe mais"):
            st.text_input("Quantas latas por dia:", key="latas_por_dia")
        else:
            st.session_state["latas_por_dia"] = ""

    # ── Lesão ──────────────────────────────────────────────────────────────
    st.markdown("### Lesão")
    st.selectbox(
        "Lesão clínica:", OPC_LESAO,
        index=safe_index(OPC_LESAO, st.session_state.get("lesao_clinica", "")),
        key="lesao_clinica",
    )

    st.selectbox(
        "Localização:", OPC_LOCALIZACAO,
        index=safe_index(OPC_LOCALIZACAO, st.session_state.get("localizacao_1", "")),
        key="localizacao_1",
    )

    if "tem_loc2" not in st.session_state:
        st.session_state.tem_loc2 = bool(st.session_state.get("localizacao_2", ""))
    st.checkbox("É mais de uma região?", key="tem_loc2")

    if st.session_state.tem_loc2:
        st.selectbox(
            "Segunda localização:", OPC_LOCALIZACAO,
            index=safe_index(OPC_LOCALIZACAO, st.session_state.get("localizacao_2", "")),
            key="localizacao_2",
        )

        if "tem_loc3" not in st.session_state:
            st.session_state.tem_loc3 = bool(st.session_state.get("localizacao_3", ""))
        st.checkbox("Existe uma terceira região?", key="tem_loc3")

        if st.session_state.tem_loc3:
            st.selectbox(
                "Terceira localização:", OPC_LOCALIZACAO,
                index=safe_index(OPC_LOCALIZACAO, st.session_state.get("localizacao_3", "")),
                key="localizacao_3",
            )
        else:
            st.session_state["localizacao_3"] = ""
    else:
        st.session_state["localizacao_2"] = ""
        st.session_state["localizacao_3"] = ""

    # Superfície e Cor da lesão (alimentam o multicategórico)
    col1, col2 = st.columns(2)
    with col1:
        st.selectbox(
            "Superfície:", OPC_SUPERFICIE,
            index=safe_index(OPC_SUPERFICIE, st.session_state.get("superficie", "")),
            key="superficie",
        )
    with col2:
        st.selectbox(
            "Cor:", OPC_COR,
            index=safe_index(OPC_COR, st.session_state.get("cor", "")),
            key="cor",
        )

    st.markdown("---")
    st.button("💾 Salvar", on_click=salvar, type="primary", key="save_paciente", width='stretch')


# ───────────────────────────────────────────────────────────────────────────
# ABA 2 — PAPA CONVENCIONAL
# ───────────────────────────────────────────────────────────────────────────
with tab_papa_c:
    st.markdown("### Análise Papa Convencional")

    col1, col2 = st.columns(2)
    with col1:
        st.text_input("Data da coleta:",     key="papac_data")
        st.text_input("Número de registro:", key="papac_reg")
    with col2:
        st.text_input("Link da pasta no Drive:", key="papac_drive")

    st.markdown("##### Análise Papanicolaou")
    col1, col2 = st.columns(2)
    with col1:
        st.text_input("Células Anucleadas:",      key="papac_anu")
        st.text_input("Superficiais com Núcleo:", key="papac_sup")
        st.text_input("Intermediárias:",          key="papac_int")
        st.text_input("Aglomerados Normais:",     key="papac_agn")
    with col2:
        st.text_input("Aglomerados Suspeitos:", key="papac_ags")
        st.text_input("Binucleadas:",           key="papac_bin")
        st.text_input("Parabasais Suspeitas:",  key="papac_par")

    st.markdown("---")
    st.button("💾 Salvar", on_click=salvar, type="primary", key="save_papac", width='stretch')


# ───────────────────────────────────────────────────────────────────────────
# ABA 3 — PAPA MEIO LÍQUIDO
# ───────────────────────────────────────────────────────────────────────────
with tab_papa_l:
    st.markdown("### Análise Papa Meio Líquido")

    col1, col2 = st.columns(2)
    with col1:
        st.text_input("Data da coleta:",     key="papal_data")
        st.text_input("Número de registro:", key="papal_reg")
    with col2:
        st.text_input("Link da pasta no Drive:", key="papal_drive")

    st.markdown("##### Análise Papanicolaou")
    col1, col2 = st.columns(2)
    with col1:
        st.text_input("Células Anucleadas:",      key="papal_anu")
        st.text_input("Superficiais com Núcleo:", key="papal_sup")
        st.text_input("Intermediárias:",          key="papal_int")
        st.text_input("Aglomerados Normais:",     key="papal_agn")
    with col2:
        st.text_input("Aglomerados Suspeitos:", key="papal_ags")
        st.text_input("Binucleadas:",           key="papal_bin")
        st.text_input("Parabasais Suspeitas:",  key="papal_par")

    st.markdown("---")
    st.button("💾 Salvar", on_click=salvar, type="primary", key="save_papal", width='stretch')


# ───────────────────────────────────────────────────────────────────────────
# ABA 4 — AgNOR CONVENCIONAL
# ───────────────────────────────────────────────────────────────────────────
with tab_agnor_c:
    st.markdown("### AgNOR Convencional")

    col1, col2 = st.columns(2)
    with col1:
        st.text_input("Data da coleta:",     key="agnorc_data")
        st.text_input("Número de registro:", key="agnorc_reg")
    with col2:
        st.text_input("Link da pasta no Drive:", key="agnorc_drive")

    st.markdown("##### Análise AgNOR")
    col1, col2 = st.columns(2)
    with col1:
        st.text_input("Número de núcleos:",            key="agnorc_nn")
        st.text_input("Número de AgNORs:",             key="agnorc_na")
        st.text_input("Número de Clusters:",           key="agnorc_nc")
        st.text_input("Número de satélites:",          key="agnorc_ns")
        st.text_input("Média de AgNOR por núcleo:",    key="agnorc_mpn")
        st.text_input("Média de tamanho dos Núcleos:", key="agnorc_mtn")
        st.text_input("Média de tamanho dos AgNORs:",  key="agnorc_mta")
    with col2:
        st.text_input("Média tamanho das NORs:",      key="agnorc_mtnor")
        st.text_input("Média tamanho dos satélites:", key="agnorc_mts")
        st.text_input("AgNOR = 1:",                   key="agnorc_e1")
        st.text_input("AgNOR = 2:",                   key="agnorc_e2")
        st.text_input("AgNOR = 3:",                   key="agnorc_e3")
        st.text_input("AgNOR = 4:",                   key="agnorc_e4")
        st.text_input("AgNOR = 5+:",                  key="agnorc_e5")

    st.markdown("---")
    st.button("💾 Salvar", on_click=salvar, type="primary", key="save_agnorc", width='stretch')


# ───────────────────────────────────────────────────────────────────────────
# ABA 5 — AgNOR MEIO LÍQUIDO
# ───────────────────────────────────────────────────────────────────────────
with tab_agnor_l:
    st.markdown("### AgNOR Meio Líquido")

    col1, col2 = st.columns(2)
    with col1:
        st.text_input("Data da coleta:",     key="agnorl_data")
        st.text_input("Número de registro:", key="agnorl_reg")
    with col2:
        st.text_input("Link da pasta no Drive:", key="agnorl_drive")

    st.markdown("##### Análise AgNOR")
    col1, col2 = st.columns(2)
    with col1:
        st.text_input("Número de núcleos:",            key="agnorl_nn")
        st.text_input("Número de AgNORs:",             key="agnorl_na")
        st.text_input("Número de Clusters:",           key="agnorl_nc")
        st.text_input("Número de satélites:",          key="agnorl_ns")
        st.text_input("Média de AgNOR por núcleo:",    key="agnorl_mpn")
        st.text_input("Média de tamanho dos Núcleos:", key="agnorl_mtn")
        st.text_input("Média de tamanho dos AgNORs:",  key="agnorl_mta")
    with col2:
        st.text_input("Média tamanho das NORs:",      key="agnorl_mtnor")
        st.text_input("Média tamanho dos satélites:", key="agnorl_mts")
        st.text_input("AgNOR = 1:",                   key="agnorl_e1")
        st.text_input("AgNOR = 2:",                   key="agnorl_e2")
        st.text_input("AgNOR = 3:",                   key="agnorl_e3")
        st.text_input("AgNOR = 4:",                   key="agnorl_e4")
        st.text_input("AgNOR = 5+:",                  key="agnorl_e5")

    st.markdown("---")
    st.button("💾 Salvar", on_click=salvar, type="primary", key="save_agnorl", width='stretch')


# ───────────────────────────────────────────────────────────────────────────
# ABA 6 — IMAGENS CLÍNICAS
# ───────────────────────────────────────────────────────────────────────────
with tab_imagens:
    st.markdown("### Imagens Clínicas")

    col1, col2 = st.columns(2)
    with col1:
        st.text_input("Data da coleta:",     key="img_data")
    with col2:
        st.text_input("Número de registro:", key="img_reg")

    st.text_input("Link da pasta no Drive (com todas as imagens):", key="img_drive")

    st.markdown("##### Observações por região")
    col1, col2 = st.columns(2)
    with col1:
        st.text_input("Língua:",         key="img_obs_lin")
        st.text_input("Assoalho bucal:", key="img_obs_ass")
        st.text_input("Mucosa jugal:",   key="img_obs_muc")
    with col2:
        st.text_input("Palato/céu da boca:", key="img_obs_pal")
        st.text_input("Lábio:",              key="img_obs_lab")
        st.text_input("Outras regiões:",     key="img_obs_out")

    st.markdown("---")
    st.button("💾 Salvar", on_click=salvar, type="primary", key="save_img", width='stretch')


# ───────────────────────────────────────────────────────────────────────────
# ABA 7 — MULTICATEGÓRICO  (preview com cálculo automático)
# ───────────────────────────────────────────────────────────────────────────
with tab_multi:
    st.markdown("### Modelo Multicategórico de Risco")
    st.caption("Os campos em destaque vêm automaticamente das outras abas. Os comboboxes são preenchidos aqui.")

    # ── Leitura dos dados das outras abas ──────────────────────────────────
    genero = st.session_state.get("genero", "")
    idade  = calcular_idade(st.session_state.get("data_nascimento", ""))
    fuma   = st.session_state.get("fuma", "")
    bebe   = st.session_state.get("bebe", "")
    loc1   = st.session_state.get("localizacao_1", "")

    # Pontuação Anamnese
    pts_genero = {"Feminino": 1, "Masculino": 2}
    p_gen   = pts_genero.get(genero, 0)
    p_idade = 1 if (idade is not None and idade < 50) else (2 if idade is not None else 0)

    fuma_ativo = fuma in ("Sim", "Ex-fumante")
    bebe_ativo = bebe and bebe != "Não bebe"
    if fuma_ativo and bebe_ativo:
        fator_txt, fator_pts = "Fumo + álcool", 2
    elif fuma_ativo:
        fator_txt, fator_pts = "Fumo", 1
    else:
        fator_txt, fator_pts = "Sem fator", 0

    p_anamnese = p_gen + p_idade + fator_pts

    # ── ANAMNESE ───────────────────────────────────────────────────────────
    st.markdown("#### 🩺 Anamnese")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Gênero",      f"{genero or '—'}",                                 f"{p_gen} pt" if p_gen else "0 pts")
    c2.metric("Idade",       f"{'<50' if (idade is not None and idade<50) else ('>50' if idade is not None else '—')}",
              f"{p_idade} pt" if p_idade else "0 pts")
    c3.metric("Fator risco", fator_txt,                                          f"{fator_pts} pt" if fator_pts else "0 pts")
    c4.metric("Subtotal",    f"{p_anamnese} pts")

    # ── EXAME FÍSICO ───────────────────────────────────────────────────────
    st.markdown("#### 🔍 Exame Físico")

    if loc1 in ("Assoalho da boca", "Língua", "Borda da língua", "Dorso da língua"):
        p_loc, loc_txt = 2, "Soalho/língua"
    elif loc1:
        p_loc, loc_txt = 1, "Outros"
    else:
        p_loc, loc_txt = 0, "—"

    # Superfície vem da aba Coleta
    superficie = st.session_state.get("superficie", "")
    pts_superficie = {"Homogênea": 1, "Não homogênea": 2}
    p_sup = pts_superficie.get(superficie, 0)

    # Cor vem da aba Coleta
    cor = st.session_state.get("cor", "")
    pts_cor = {"Branca": 1, "Mista": 2, "Avermelhada": 1}
    p_cor = pts_cor.get(cor, 0)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Localização", loc_txt,             f"{p_loc} pt" if p_loc else "0 pts")
    c2.metric("Superfície",  superficie or "—",   f"{p_sup} pt" if p_sup else "0 pts")
    c3.metric("Cor",         cor or "—",          f"{p_cor} pt" if p_cor else "0 pts")

    def extrai_pts(txt):
        if not txt:
            return 0
        try:
            return int(txt.split("(")[-1].rstrip(")"))
        except (ValueError, IndexError):
            return 0

    p_exame = p_loc + p_sup + p_cor
    c4.metric("Subtotal", f"{p_exame} pts")

    # ── CITOLOGIA ──────────────────────────────────────────────────────────
    st.markdown("#### 🧫 Citologia")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.selectbox(
            "Papanicolaou:", ["", "Inflamatório (1)", "Suspeito (3)"],
            index=safe_index(["", "Inflamatório (1)", "Suspeito (3)"], st.session_state.get("mc_papa", "")),
            key="mc_papa",
        )
    with c2:
        st.selectbox(
            "AgNOR:", ["", "Média <3,69 (1)", "Média >3,69 (2)"],
            index=safe_index(["", "Média <3,69 (1)", "Média >3,69 (2)"], st.session_state.get("mc_agnor", "")),
            key="mc_agnor",
        )

    p_papa  = extrai_pts(st.session_state.get("mc_papa", ""))
    p_agnor = extrai_pts(st.session_state.get("mc_agnor", ""))
    p_cito  = p_papa + p_agnor
    c3.metric("Subtotal", f"{p_cito} pts")

    # ── HISTOLOGIA ─────────────────────────────────────────────────────────
    st.markdown("#### 🔬 Histologia (Displasia Epitelial)")
    c1, c2 = st.columns([2, 1])
    with c1:
        st.selectbox(
            "Displasia Epitelial:", ["", "Ausência (1)", "Presença (3)"],
            index=safe_index(["", "Ausência (1)", "Presença (3)"], st.session_state.get("mc_displasia", "")),
            key="mc_displasia",
        )
    p_hist = extrai_pts(st.session_state.get("mc_displasia", ""))
    c2.metric("Subtotal", f"{p_hist} pts")

    # ── TOTAL ──────────────────────────────────────────────────────────────
    st.markdown("---")
    total = p_anamnese + p_exame + p_cito + p_hist
    st.markdown(f"## 🎯 Pontuação total: **{total} pts**")
    st.caption("Faixas de risco serão definidas pelo professor.")

    st.markdown("---")
    st.button("💾 Salvar", on_click=salvar, type="primary", key="save_multi", width='stretch')

"""
Página de Estatísticas — análise de TODOS os laudos.

Fica separada do preenchimento de laudos (multipage do Streamlit).
Aparece automaticamente no menu lateral quando está dentro da pasta 'pages/'.
"""

import sys
from pathlib import Path

# permite importar banco.py que está na pasta de cima
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st
import pandas as pd
import banco

st.set_page_config(page_title="Estatísticas – Laudos UFRGS", layout="wide")

# ── Proteção: exige login feito na página principal ─────────────────────────
if not st.session_state.get("usuario_logado"):
    st.warning("🔒 Faça login na página principal (Laudos) para acessar as estatísticas.")
    st.stop()


st.title("📊 Estatísticas dos Laudos")
st.caption("Análise de todos os laudos do banco. Escolha o que analisar e o período.")

with st.sidebar:
    st.markdown(f"👤 **{st.session_state.usuario_logado}**")
    st.markdown("---")
    st.caption(f"Total no banco: {banco.contar()} laudos")

anos = banco.anos_disponiveis()

if not anos:
    st.info("Ainda não há datas padronizadas para gerar estatísticas.")
    st.stop()


# ── Controles ───────────────────────────────────────────────────────────────
c1, c2, c3 = st.columns([2, 1, 1])
with c1:
    analise = st.selectbox(
        "O que você quer ver?",
        ["Casos por ano",
         "Diagnósticos mais comuns",
         "Distribuição por gênero",
         "Localizações mais comuns",
         "Evolução de um diagnóstico por ano",
         "Acerto clínico × histopatológico"],
    )
with c2:
    ano_ini = st.selectbox("De:", anos, index=0)
with c3:
    ano_fim = st.selectbox("Até:", anos, index=len(anos) - 1)

if ano_ini > ano_fim:
    ano_ini, ano_fim = ano_fim, ano_ini

st.markdown("---")


# ── Casos por ano ───────────────────────────────────────────────────────────
if analise == "Casos por ano":
    dados_g = banco.casos_por_ano(ano_ini, ano_fim)
    if dados_g:
        df = pd.DataFrame(dados_g, columns=["Ano", "Casos"]).set_index("Ano")
        st.bar_chart(df)
        st.markdown(f"**Total no período: {df['Casos'].sum()} laudos**")
        with st.expander("Ver tabela"):
            st.dataframe(df, width='stretch')
    else:
        st.info("Sem dados nesse período.")

# ── Diagnósticos mais comuns ────────────────────────────────────────────────
elif analise == "Diagnósticos mais comuns":
    top = st.slider("Quantos mostrar:", 5, 30, 15)
    dados_g = banco.ranking_diagnosticos(ano_ini, ano_fim, top=top)
    if dados_g:
        df = pd.DataFrame(dados_g, columns=["Diagnóstico", "Casos"]).set_index("Diagnóstico")
        st.bar_chart(df, horizontal=True)
        with st.expander("Ver tabela"):
            st.dataframe(df, width='stretch')
    else:
        st.info("Sem dados nesse período.")

# ── Gênero ──────────────────────────────────────────────────────────────────
elif analise == "Distribuição por gênero":
    dados_g = banco.distribuicao_genero(ano_ini, ano_fim)
    if dados_g:
        df = pd.DataFrame(dados_g, columns=["Gênero", "Casos"]).set_index("Gênero")
        col1, col2 = st.columns(2)
        with col1:
            st.bar_chart(df)
        with col2:
            st.dataframe(df, width='stretch')
    else:
        st.info("Sem dados nesse período.")

# ── Localização ─────────────────────────────────────────────────────────────
elif analise == "Localizações mais comuns":
    top = st.slider("Quantos mostrar:", 5, 30, 15)
    dados_g = banco.ranking_localizacao(ano_ini, ano_fim, top=top)
    if dados_g:
        df = pd.DataFrame(dados_g, columns=["Localização", "Casos"]).set_index("Localização")
        st.bar_chart(df, horizontal=True)
        with st.expander("Ver tabela"):
            st.dataframe(df, width='stretch')
    else:
        st.info("Sem dados nesse período.")

# ── Evolução de um diagnóstico ──────────────────────────────────────────────
elif analise == "Evolução de um diagnóstico por ano":
    termo = st.text_input("Diagnóstico a rastrear:", placeholder="Ex: ameloblastoma, linfonodo...")
    if termo.strip():
        dados_g = banco.casos_por_ano(ano_ini, ano_fim, termo_diag=termo)
        if dados_g:
            df = pd.DataFrame(dados_g, columns=["Ano", "Casos"]).set_index("Ano")
            st.line_chart(df)
            st.markdown(f"**“{termo}” — total no período: {df['Casos'].sum()} casos**")
            with st.expander("Ver tabela"):
                st.dataframe(df, width='stretch')
        else:
            st.info(f"Nenhum caso de “{termo}” nesse período.")
    else:
        st.info("Digite um diagnóstico para ver a evolução ano a ano.")

# ── Acerto clínico × histopatológico ────────────────────────────────────────
elif analise == "Acerto clínico × histopatológico":
    st.caption(
        "Verifica em quantos casos o diagnóstico **histopatológico** (resultado) "
        "estava entre as hipóteses do diagnóstico **clínico** (suspeita do dentista)."
    )
    st.warning(
        "⚠️ Análise preliminar: compara os textos como estão escritos, **sem "
        "tabela de sinônimos ainda**. Ex: 'CEC' e 'Carcinoma espinocelular' são "
        "contados como diferentes até a normalização com o professor. "
        "Os números reais de acerto tendem a ser maiores."
    )

    r = banco.comparar_clinico_histo(ano_ini, ano_fim)

    if r["comparaveis"] == 0:
        st.info("Não há laudos com os dois diagnósticos preenchidos nesse período.")
    else:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Comparáveis", r["comparaveis"])
        c2.metric("Bateu", r["acertou"])
        c3.metric("Não bateu", r["nao_bateu"])
        c4.metric("% de acerto", f"{r['percentual']}%")
        st.caption(f"({r['sem_dados']} laudos ficaram de fora por ter algum dos dois campos vazio)")

        # gráfico simples
        df = pd.DataFrame(
            [("Bateu", r["acertou"]), ("Não bateu", r["nao_bateu"])],
            columns=["Resultado", "Casos"],
        ).set_index("Resultado")
        st.bar_chart(df)

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Exemplos que bateram:**")
            if r["exemplos_acerto"]:
                for num, clin, histo in r["exemplos_acerto"]:
                    st.markdown(f"- Nº {num}: clínico *“{clin}”* → histo *“{histo}”*")
            else:
                st.caption("Nenhum exemplo.")
        with col2:
            st.markdown("**Exemplos que NÃO bateram:**")
            if r["exemplos_erro"]:
                for num, clin, histo in r["exemplos_erro"]:
                    st.markdown(f"- Nº {num}: clínico *“{clin}”* → histo *“{histo}”*")
            else:
                st.caption("Nenhum exemplo.")
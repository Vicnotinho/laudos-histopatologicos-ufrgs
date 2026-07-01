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
         "Acerto clínico × histopatológico",
         "Idade por diagnóstico",
         "Distribuição de idade (geral)",
         "Tamanho dos fragmentos (volume)"],
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

# ── Idade por diagnóstico ───────────────────────────────────────────────────
elif analise == "Idade por diagnóstico":
    st.caption("Quantos casos de um diagnóstico, e quantos caem numa faixa de idade.")
    col_a, col_b = st.columns([2, 1])
    with col_a:
        termo = st.text_input("Diagnóstico:", placeholder="Ex: lipoma, carcinoma...")
    with col_b:
        campo = st.radio("Buscar em:", ["Histopatológico", "Clínico"], horizontal=True)

    c1, c2, c3 = st.columns(3)
    with c1:
        idade_min = st.number_input("Idade mínima:", min_value=0, max_value=120, value=0)
    with c2:
        idade_max = st.number_input("Idade máxima:", min_value=0, max_value=120, value=100)
    with c3:
        passo = st.number_input("Frequência (de quantos em quantos anos):", min_value=1, max_value=50, value=5)

    if termo.strip():
        campo_db = "histo" if campo == "Histopatológico" else "clinico"
        r = banco.prevalencia_por_diagnostico(
            termo, campo=campo_db,
            idade_min=idade_min, idade_max=idade_max,
            ano_ini=ano_ini, ano_fim=ano_fim,
        )
        if r["total"] == 0:
            st.info(f"Nenhum caso de “{termo}” encontrado.")
        else:
            m1, m2, m3, m4 = st.columns(4)
            m1.metric(f"Casos de “{termo}”", r["total"])
            pct = round(100 * r["na_faixa"] / r["com_idade"], 1) if r["com_idade"] else 0
            m2.metric(f"Entre {idade_min}-{idade_max} anos", f"{r['na_faixa']} ({pct}%)")
            m3.metric("Idade média", f"{r['media_idade']} anos")
            m4.metric("Faixa observada", f"{r['min_idade']}-{r['max_idade']}")
            st.caption(f"({r['com_idade']} dos {r['total']} casos têm idade preenchida)")

            if r["idades"]:
                import pandas as pd
                # agrupa pela frequência escolhida, dentro do intervalo min-max
                faixas = {}
                for i in r["idades"]:
                    if idade_min <= i <= idade_max:
                        ini = idade_min + ((i - idade_min) // passo) * passo
                        chave = (ini, ini + passo - 1)
                        faixas[chave] = faixas.get(chave, 0) + 1
                if faixas:
                    faixas_ord = sorted(faixas.items(), key=lambda x: x[0][0])
                    df = pd.DataFrame(
                        [(f"{a}-{b}", n) for (a, b), n in faixas_ord],
                        columns=[f"Faixa etária (de {passo} em {passo} anos)", "Casos"],
                    ).set_index(f"Faixa etária (de {passo} em {passo} anos)")
                    st.markdown(f"**Distribuição de “{termo}” por idade:**")
                    st.bar_chart(df)
                else:
                    st.info(f"Nenhum caso de “{termo}” entre {idade_min} e {idade_max} anos.")
    else:
        st.info("Digite um diagnóstico para analisar.")

# ── Distribuição de idade (geral) ───────────────────────────────────────────
elif analise == "Distribuição de idade (geral)":
    st.caption("Escolha a faixa de idade e de quantos em quantos anos quer agrupar.")
    c1, c2, c3 = st.columns(3)
    with c1:
        idade_min = st.number_input("Idade mínima:", min_value=0, max_value=120, value=0)
    with c2:
        idade_max = st.number_input("Idade máxima:", min_value=0, max_value=120, value=100)
    with c3:
        passo = st.number_input("Agrupar de quantos em quantos anos:", min_value=1, max_value=50, value=5)

    if idade_min > idade_max:
        idade_min, idade_max = idade_max, idade_min

    r = banco.distribuicao_idade(ano_ini, ano_fim, idade_min=idade_min,
                                 idade_max=idade_max, passo=passo)
    if r["faixas"]:
        import pandas as pd
        df = pd.DataFrame(r["faixas"], columns=["Faixa etária", "Pacientes"]).set_index("Faixa etária")
        st.bar_chart(df)
        st.markdown(f"**Total entre {idade_min} e {idade_max} anos: {r['total']} pacientes**")
        with st.expander("Ver tabela"):
            st.dataframe(df, width='stretch')
    else:
        st.info("Nenhum paciente nessa faixa de idade.")

# ── Tamanho dos fragmentos (volume) ─────────────────────────────────────────
elif analise == "Tamanho dos fragmentos (volume)":
    st.caption(
        "Digite uma lesão para ver a distribuição dos tamanhos (volume em mm³) "
        "dela. Só considera casos com as 3 dimensões (LxAxP)."
    )
    col_a, col_b = st.columns([2, 1])
    with col_a:
        termo = st.text_input("Lesão:", placeholder="Ex: Hiperplasia epitelial e hiperceratose")
    with col_b:
        campo = st.radio("Buscar em:", ["Histopatológico", "Clínico"], horizontal=True)

    campo_db = "histo" if campo == "Histopatológico" else "clinico"

    # frequência (agrupamento) — 0 = automática
    freq = st.number_input(
        "Agrupar de quantos em quantos mm³ (0 = automático):",
        min_value=0, max_value=100000, value=0, step=100,
    )

    if not termo.strip():
        st.info("Digite uma lesão para ver a distribuição dos tamanhos.")
    else:
        r = banco.distribuicao_volume_lesao(
            termo, campo=campo_db, faixa=(freq if freq > 0 else None),
            ano_ini=ano_ini, ano_fim=ano_fim,
        )
        if not r["casos"]:
            st.info(f"Nenhum caso de “{termo}” com as 3 dimensões encontrado.")
        else:
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Com volume", len(r["casos"]))
            m2.metric("Menor", f"{r['min_vol']} mm³")
            m3.metric("Maior", f"{r['max_vol']} mm³")
            m4.metric("Média", f"{r['media_vol']} mm³")
            st.caption(
                f"({r['sem_3d']} casos de “{termo}” ficaram de fora por não ter as 3 medidas) "
                f"· agrupamento usado: {int(r['faixa_usada'])} mm³"
            )

            import pandas as pd
            # gráfico da distribuição (volumes mais comuns)
            if r["faixas"]:
                df_f = pd.DataFrame(r["faixas"], columns=["Faixa de volume (mm³)", "Casos"]).set_index("Faixa de volume (mm³)")
                st.markdown("**Volumes mais comuns:**")
                st.bar_chart(df_f)

            # opção de ver as dimensões originais
            ver = st.radio(
                "Ver detalhes:",
                ["Não mostrar", "Dimensões originais (ex: 22x2x10)", "Lista por volume"],
                horizontal=True,
            )
            if ver == "Dimensões originais (ex: 22x2x10)":
                df = pd.DataFrame(r["casos"], columns=["Nº registro", "Volume (mm³)", "Dimensões"])
                st.dataframe(df[["Nº registro", "Dimensões"]], width='stretch', hide_index=True)
            elif ver == "Lista por volume":
                df = pd.DataFrame(r["casos"], columns=["Nº registro", "Volume (mm³)", "Dimensões"])
                st.dataframe(df, width='stretch', hide_index=True)

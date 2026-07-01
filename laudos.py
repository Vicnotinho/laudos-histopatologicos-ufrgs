"""
laudos.py — Roteador principal do sistema (mantém 'streamlit run laudos.py').

Define o logo da barra lateral e o menu de páginas com nomes bonitos:
   📝 Laudos       (pagina_laudos.py)        — histopatologia (Pantelis)
   📊 Estatísticas (pagina_estatisticas.py)
   🔬 Longitudinal (pagina_longitudinal.py)  — citologia (Nathalia), banco separado
   💨 Cigarro Eletrônico (pagina_cigarro.py)  — questionário, banco separado
"""

import streamlit as st
from pathlib import Path

st.set_page_config(page_title="Laudos Histopatológicos – UFRGS", layout="wide")


def _achar_arquivo(nomes):
    for nome in nomes:
        p = Path(__file__).parent / nome
        if p.exists():
            return str(p)
    return None


# logo menor no topo da barra lateral (acima do menu de páginas)
LOGO_MENOR = _achar_arquivo(
    ("Logo-Odonto-UFRGS-menor.png", "logo-odonto-ufrgs-menor.png",
     "Logo-Odonto-UFRGS.png", "logo.png")
)
if LOGO_MENOR:
    st.logo(LOGO_MENOR, size="large")

# aumenta o logo da barra lateral para ficar legível
st.markdown(
    """
    <style>
    [data-testid="stSidebarHeader"] img,
    [data-testid="stLogo"] {
        height: 4.5rem !important;
        max-width: 100% !important;
        object-fit: contain !important;
    }
    [data-testid="stSidebarHeader"] {
        padding-top: 0.5rem !important;
        padding-bottom: 0.5rem !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# menu de páginas com nomes e ícones bonitos
pagina_laudos = st.Page(
    "paginas/pagina_laudos.py", title="Laudos", icon="📝", default=True
)
pagina_estat = st.Page(
    "paginas/pagina_estatisticas.py", title="Estatísticas", icon="📊"
)
pagina_long = st.Page(
    "paginas/pagina_longitudinal.py", title="Longitudinal", icon="🔬"
)
pagina_cigarro = st.Page(
    "paginas/pagina_cigarro.py", title="Cigarro Eletrônico", icon="💨"
)

nav = st.navigation([pagina_laudos, pagina_estat, pagina_long, pagina_cigarro])
nav.run()

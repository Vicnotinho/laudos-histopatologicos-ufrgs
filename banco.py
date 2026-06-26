"""
banco.py — Camada de banco de dados (SQLite) do sistema de laudos.

Um único arquivo local (dados/laudos.db), rápido mesmo com milhares de laudos.
Offline, atende à LGPD.
"""

import sqlite3
import uuid
from pathlib import Path
from datetime import datetime

PASTA_DADOS = Path(__file__).parent / "dados"
PASTA_DADOS.mkdir(exist_ok=True)
ARQUIVO_DB = PASTA_DADOS / "laudos.db"

CAMPOS = [
    "num_registro", "data", "nome", "endereco_paciente",
    "idade", "genero", "raca", "profissao",
    "titulacao", "cirurgiao", "endereco_cirurgiao", "convenio",
    "historia_clinica", "fumo", "alcool",
    "tipo_biopsia", "localizacao", "diagnostico_clinico",
    "aspecto_macroscopico", "aspecto_microscopico",
    "diagnostico_histopatologico", "patologista", "observacoes",
    "tem_foto_clinica", "tem_foto_biopsia",
    "origem",
]


import unicodedata


def _sem_acento(txt):
    """Remove acentos e deixa minúsculo (para busca que ignora acento)."""
    if txt is None:
        return ""
    txt = str(txt)
    txt = "".join(c for c in unicodedata.normalize("NFD", txt)
                  if unicodedata.category(c) != "Mn")
    return txt.lower()


def conectar():
    conn = sqlite3.connect(ARQUIVO_DB)
    conn.row_factory = sqlite3.Row
    # registra função para busca sem acento (nódulo = nodulo)
    conn.create_function("semacento", 1, _sem_acento)
    return conn


def inicializar():
    """Cria as tabelas se não existirem."""
    colunas_sql = ",\n        ".join(f'"{c}" TEXT' for c in CAMPOS)
    with conectar() as conn:
        conn.execute(f"""
            CREATE TABLE IF NOT EXISTS laudos (
                uuid TEXT PRIMARY KEY,
                {colunas_sql}
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                data_hora TEXT,
                usuario TEXT,
                acao TEXT,
                num_registro TEXT
            )
        """)
        # migração: adiciona colunas novas que ainda não existam na tabela
        existentes = {row[1] for row in conn.execute("PRAGMA table_info(laudos)").fetchall()}
        for c in CAMPOS:
            if c not in existentes:
                conn.execute(f'ALTER TABLE laudos ADD COLUMN "{c}" TEXT')
        # índices que aceleram a busca
        conn.execute('CREATE INDEX IF NOT EXISTS idx_num ON laudos("num_registro")')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_nome ON laudos("nome")')
        conn.commit()


# ─────────────────────────────────────────────────────────────────────────────
# CRUD
# ─────────────────────────────────────────────────────────────────────────────

def salvar_laudo(uuid_: str, dados: dict) -> None:
    """Insere ou atualiza um laudo."""
    with conectar() as conn:
        existe = conn.execute("SELECT 1 FROM laudos WHERE uuid = ?", (uuid_,)).fetchone()
        valores = [str(dados.get(c, "")) for c in CAMPOS]
        if existe:
            sets = ", ".join(f'"{c}" = ?' for c in CAMPOS)
            conn.execute(f"UPDATE laudos SET {sets} WHERE uuid = ?", valores + [uuid_])
        else:
            cols = ", ".join(f'"{c}"' for c in CAMPOS)
            ph = ", ".join("?" for _ in CAMPOS)
            conn.execute(f'INSERT INTO laudos (uuid, {cols}) VALUES (?, {ph})', [uuid_] + valores)
        conn.commit()


def carregar_laudo(uuid_: str) -> dict | None:
    with conectar() as conn:
        row = conn.execute("SELECT * FROM laudos WHERE uuid = ?", (uuid_,)).fetchone()
    return dict(row) if row else None


def num_registro_existe(num_registro: str, uuid_atual: str) -> bool:
    if not num_registro:
        return False
    with conectar() as conn:
        row = conn.execute(
            'SELECT uuid FROM laudos WHERE "num_registro" = ? AND uuid != ?',
            (str(num_registro), uuid_atual),
        ).fetchone()
    return row is not None


def _num_ordenavel(sql_col: str) -> str:
    """Expressão SQL que converte num_registro em número para ordenar (vazios por último)."""
    return f"""
        CASE
            WHEN {sql_col} GLOB '*[0-9]*'
            THEN CAST({sql_col} AS INTEGER)
            ELSE 999999999
        END
    """


# campos onde a busca procura (sem acento)
_CAMPOS_BUSCA = [
    "nome", "num_registro", "data",
    "diagnostico_histopatologico", "diagnostico_clinico",
    "localizacao", "aspecto_microscopico", "aspecto_macroscopico",
    "cirurgiao",
]


def _where_busca() -> str:
    """Cláusula WHERE que ignora acento, comparando semacento(campo) com o termo."""
    return " OR ".join(f'semacento("{c}") LIKE ?' for c in _CAMPOS_BUSCA)


def buscar(termo: str = "", limite: int = 50, offset: int = 0) -> list[dict]:
    """
    Sem termo: ordenado por número de registro.
    Com termo: busca em vários campos, ignorando acentos (nódulo = nodulo).
    offset permite paginação (pular N resultados).
    """
    ordem = f"ORDER BY {_num_ordenavel('num_registro')} ASC"
    with conectar() as conn:
        if termo.strip():
            like = f"%{_sem_acento(termo.strip())}%"
            params = [like] * len(_CAMPOS_BUSCA) + [limite, offset]
            rows = conn.execute(
                f"""
                SELECT * FROM laudos
                WHERE {_where_busca()}
                {ordem}
                LIMIT ? OFFSET ?
                """,
                params,
            ).fetchall()
        else:
            rows = conn.execute(
                f"SELECT * FROM laudos {ordem} LIMIT ? OFFSET ?", (limite, offset)
            ).fetchall()
    return [dict(r) for r in rows]


def contar_busca(termo: str = "") -> int:
    """Conta quantos resultados a busca retorna (para calcular páginas)."""
    with conectar() as conn:
        if termo.strip():
            like = f"%{_sem_acento(termo.strip())}%"
            params = [like] * len(_CAMPOS_BUSCA)
            return conn.execute(
                f"SELECT COUNT(*) FROM laudos WHERE {_where_busca()}",
                params,
            ).fetchone()[0]
        return conn.execute("SELECT COUNT(*) FROM laudos").fetchone()[0]


def contar() -> int:
    with conectar() as conn:
        return conn.execute("SELECT COUNT(*) FROM laudos").fetchone()[0]


# ─────────────────────────────────────────────────────────────────────────────
# LOG
# ─────────────────────────────────────────────────────────────────────────────

def registrar_log(usuario: str, acao: str, num_registro: str) -> None:
    with conectar() as conn:
        conn.execute(
            "INSERT INTO log (data_hora, usuario, acao, num_registro) VALUES (?, ?, ?, ?)",
            (datetime.now().strftime("%d/%m/%Y %H:%M:%S"), usuario, acao, num_registro),
        )
        conn.commit()


# ─────────────────────────────────────────────────────────────────────────────
# ESTATÍSTICAS
# ─────────────────────────────────────────────────────────────────────────────

def _ano_da_data(col="data"):
    """Extrai o ano (AAAA) do campo data no formato DD/MM/AAAA."""
    return f"substr({col}, 7, 4)"


def anos_disponiveis() -> list[str]:
    """Lista os anos que aparecem nos dados (para o filtro de período)."""
    with conectar() as conn:
        rows = conn.execute(
            f'SELECT DISTINCT {_ano_da_data()} AS ano FROM laudos '
            f'WHERE length("data") = 10 ORDER BY ano'
        ).fetchall()
    return [r["ano"] for r in rows if r["ano"] and r["ano"].isdigit()]


def _filtro_periodo(ano_ini, ano_fim):
    """Monta cláusula WHERE de período. Retorna (sql, params)."""
    if ano_ini and ano_fim:
        return (f'AND {_ano_da_data()} BETWEEN ? AND ?', [str(ano_ini), str(ano_fim)])
    return ("", [])


def casos_por_ano(ano_ini=None, ano_fim=None, termo_diag="") -> list[tuple]:
    """Quantos laudos por ano. Opcional: filtrar por um diagnóstico."""
    cond_diag = ""
    params = []
    if termo_diag.strip():
        cond_diag = '''AND ("diagnostico_histopatologico" LIKE ?
                          OR "diagnostico_clinico" LIKE ?)'''
        like = f"%{termo_diag.strip()}%"
        params += [like, like]

    f_sql, f_par = _filtro_periodo(ano_ini, ano_fim)
    params += f_par

    with conectar() as conn:
        rows = conn.execute(
            f'''
            SELECT {_ano_da_data()} AS ano, COUNT(*) AS total
            FROM laudos
            WHERE length("data") = 10 {cond_diag} {f_sql}
            GROUP BY ano ORDER BY ano
            ''', params
        ).fetchall()
    return [(r["ano"], r["total"]) for r in rows if r["ano"] and r["ano"].isdigit()]


def ranking_diagnosticos(ano_ini=None, ano_fim=None, top=20) -> list[tuple]:
    """Diagnósticos histopatológicos mais frequentes."""
    f_sql, params = _filtro_periodo(ano_ini, ano_fim)
    with conectar() as conn:
        rows = conn.execute(
            f'''
            SELECT TRIM("diagnostico_histopatologico") AS diag, COUNT(*) AS total
            FROM laudos
            WHERE TRIM("diagnostico_histopatologico") != '' {f_sql}
            GROUP BY LOWER(diag) ORDER BY total DESC LIMIT ?
            ''', params + [top]
        ).fetchall()
    return [(r["diag"], r["total"]) for r in rows]


def distribuicao_genero(ano_ini=None, ano_fim=None) -> list[tuple]:
    f_sql, params = _filtro_periodo(ano_ini, ano_fim)
    with conectar() as conn:
        rows = conn.execute(
            f'''
            SELECT TRIM("genero") AS g, COUNT(*) AS total
            FROM laudos WHERE TRIM("genero") != '' {f_sql}
            GROUP BY LOWER(g) ORDER BY total DESC
            ''', params
        ).fetchall()
    return [(r["g"], r["total"]) for r in rows]


def ranking_localizacao(ano_ini=None, ano_fim=None, top=20) -> list[tuple]:
    f_sql, params = _filtro_periodo(ano_ini, ano_fim)
    with conectar() as conn:
        rows = conn.execute(
            f'''
            SELECT TRIM("localizacao") AS loc, COUNT(*) AS total
            FROM laudos WHERE TRIM("localizacao") != '' {f_sql}
            GROUP BY LOWER(loc) ORDER BY total DESC LIMIT ?
            ''', params + [top]
        ).fetchall()
    return [(r["loc"], r["total"]) for r in rows]


# ─────────────────────────────────────────────────────────────────────────────
# COMPARAÇÃO: diagnóstico clínico (hipóteses) × histopatológico (resultado)
# ─────────────────────────────────────────────────────────────────────────────

def comparar_clinico_histo(ano_ini=None, ano_fim=None) -> dict:
    """
    Verifica, para cada laudo, se o diagnóstico HISTOPATOLÓGICO (resultado)
    aparece dentro do diagnóstico CLÍNICO (hipóteses do dentista).

    Trabalha com o texto como está (sem tabela de sinônimos ainda).
    A comparação ignora acento e maiúsculas.

    Retorna um dicionário com:
      total            — laudos com os dois campos preenchidos
      acertou          — histo aparece no texto do clínico
      nao_bateu        — histo NÃO aparece no clínico
      sem_dados        — algum dos campos vazio
      percentual       — % de acerto sobre os comparáveis
      exemplos_acerto  — alguns exemplos (clínico, histo)
      exemplos_erro    — alguns exemplos (clínico, histo)
    """
    f_sql, params = _filtro_periodo(ano_ini, ano_fim)
    with conectar() as conn:
        rows = conn.execute(
            f'''SELECT "diagnostico_clinico" AS clinico,
                       "diagnostico_histopatologico" AS histo,
                       "num_registro" AS num
                FROM laudos
                WHERE length("data") = 10 {f_sql}''' if (ano_ini and ano_fim)
            else '''SELECT "diagnostico_clinico" AS clinico,
                           "diagnostico_histopatologico" AS histo,
                           "num_registro" AS num
                    FROM laudos''',
            params,
        ).fetchall()

    acertou = nao_bateu = sem_dados = 0
    exemplos_acerto, exemplos_erro = [], []

    for r in rows:
        clinico = _sem_acento((r["clinico"] or "").strip())
        histo = _sem_acento((r["histo"] or "").strip())

        if not clinico or not histo:
            sem_dados += 1
            continue

        # "acertou" se o resultado histopatológico aparece no texto clínico
        # (compara também o caminho inverso, caso o clínico seja mais curto)
        if histo in clinico or clinico in histo:
            acertou += 1
            if len(exemplos_acerto) < 8:
                exemplos_acerto.append((r["num"], r["clinico"], r["histo"]))
        else:
            nao_bateu += 1
            if len(exemplos_erro) < 8:
                exemplos_erro.append((r["num"], r["clinico"], r["histo"]))

    comparaveis = acertou + nao_bateu
    percentual = round(100 * acertou / comparaveis, 1) if comparaveis else 0.0

    return {
        "total": len(rows),
        "comparaveis": comparaveis,
        "acertou": acertou,
        "nao_bateu": nao_bateu,
        "sem_dados": sem_dados,
        "percentual": percentual,
        "exemplos_acerto": exemplos_acerto,
        "exemplos_erro": exemplos_erro,
    }


# inicializa ao importar
inicializar()
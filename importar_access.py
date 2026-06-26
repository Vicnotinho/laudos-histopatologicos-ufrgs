"""
importar_access.py — Importa TODOS os laudos de um Access (.accdb/.mdb) para laudos.csv

⚠️  RODE NA SUA MÁQUINA, OFFLINE. O arquivo tem dados de pacientes (LGPD).

═══════════════════════════════════════════════════════════════════════════════
O QUE ESTE SCRIPT FAZ:
  • Junta TODAS as tabelas de laudo (uma por ano) num arquivo só.
  • Pula automaticamente tabelas vazias.
  • Não duplica: se o mesmo Número de registro aparecer em mais de uma
    tabela (ex: "Cópia de..."), só entra uma vez.
  • Guarda de qual tabela/ano cada registro veio (campo "origem").

COMO USAR:
  1) pip install pandas pyodbc   (uma vez)
     + Microsoft Access Database Engine (Windows)
  2) Edite CAMINHO_ACCESS e SENHA abaixo.
  3) Deixe MODO = "importar" e rode:  python importar_access.py
═══════════════════════════════════════════════════════════════════════════════
"""

import uuid
from pathlib import Path

import pandas as pd
import pyodbc
import banco


# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURAÇÃO
# ─────────────────────────────────────────────────────────────────────────────

CAMINHO_ACCESS = r"C:\Users\victo\OneDrive\Documentos\Consultório\programa laudo pantelis\dados_antigos.accdb"
SENHA = "COLOQUE_A_SENHA_AQUI"

MODO = "importar"   # "explorar" (lista tabelas) ou "importar"

PASTA_DADOS = Path(__file__).parent / "dados"
ARQUIVO_LAUDOS = PASTA_DADOS / "laudos.csv"

# Tabelas que NUNCA são laudos (estrutura diferente) — sempre ignoradas
TABELAS_IGNORAR = {"Diagnósticos"}

# ── Mapa: campo_do_programa  →  coluna_no_access ───────────────────────────
# Os nomes do Access vêm com ":" no fim em vários campos — já considerado.
MAPA_COLUNAS = {
    "num_registro":                "Número",
    "data":                        "Data:",
    "nome":                        "Nome do Paciente:",
    "endereco_paciente":           "Endereço do Paciente:",
    "idade":                       "Idade",
    "genero":                      "Genero",
    "raca":                        "Raça",
    "profissao":                   "Profissão",
    "titulacao":                   "Titulação",
    "cirurgiao":                   "Nome do Cirurgião:",
    "endereco_cirurgiao":          "Endereço do Cirurgião:",
    "convenio":                    "Convênio",
    "historia_clinica":            "História Clínica:",
    "fumo":                        "Fumo",
    "alcool":                      "Álcool",
    "tipo_biopsia":                "Tipo de Biópsia",
    "localizacao":                 "Localização Anatômica:",
    "diagnostico_clinico":         "Diagnóstico Clínico:",
    "aspecto_macroscopico":        "Aspecto Macroscópico:",
    "aspecto_microscopico":        "Aspecto Microscópico:",
    "diagnostico_histopatologico": "Diagnóstico Histopatológico:",
    "patologista":                 "Patologista Responsável:",
    "observacoes":                 "Observações:",
}

CAMPOS_PROGRAMA = list(MAPA_COLUNAS.keys())


# ─────────────────────────────────────────────────────────────────────────────

def conectar():
    conn_str = (
        r"DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};"
        rf"DBQ={CAMINHO_ACCESS};"
        rf"PWD={SENHA};"
    )
    return pyodbc.connect(conn_str)


def listar_tabelas(cursor):
    return [t.table_name for t in cursor.tables(tableType="TABLE")]


def explorar():
    conn = conectar()
    cursor = conn.cursor()
    print("\n📋 Tabelas encontradas:")
    for t in listar_tabelas(cursor):
        try:
            n = pd.read_sql(f"SELECT COUNT(*) AS n FROM [{t}]", conn)["n"].iloc[0]
        except Exception:
            n = "?"
        print(f"   • {t}  ({n} linhas)")
    conn.close()


def linha_tem_conteudo(registro) -> bool:
    """True se a linha tiver pelo menos número de registro OU nome."""
    return bool(str(registro.get("num_registro", "")).strip()
                or str(registro.get("nome", "")).strip())


def importar():
    conn = conectar()
    cursor = conn.cursor()
    tabelas = [t for t in listar_tabelas(cursor) if t not in TABELAS_IGNORAR]

    print("\n" + "=" * 70)
    print("IMPORTANDO — juntando todas as tabelas de laudo")
    print("=" * 70)

    todos = []
    vistos = set()        # números de registro já incluídos (deduplicação)
    total_lidos = 0
    total_dup = 0
    total_vazios = 0

    for tabela in tabelas:
        try:
            df = pd.read_sql(f"SELECT * FROM [{tabela}]", conn)
        except Exception as e:
            print(f"   ⚠️  Pulei '{tabela}' (erro de leitura: {e})")
            continue

        if df.empty:
            print(f"   ⏭️  '{tabela}' está vazia — ignorada.")
            continue

        # confere se a tabela tem as colunas mínimas de um laudo
        colunas = set(df.columns)
        if MAPA_COLUNAS["num_registro"] not in colunas and MAPA_COLUNAS["nome"] not in colunas:
            print(f"   ⏭️  '{tabela}' não parece um laudo — ignorada.")
            continue

        n_tabela = 0
        for _, row in df.iterrows():
            total_lidos += 1
            registro = {"uuid": str(uuid.uuid4()), "origem": tabela}
            for campo, col in MAPA_COLUNAS.items():
                if col in df.columns:
                    val = row[col]
                    registro[campo] = "" if pd.isna(val) else str(val).strip()
                else:
                    registro[campo] = ""

            # pula linhas em branco
            if not linha_tem_conteudo(registro):
                total_vazios += 1
                continue

            # deduplica por número de registro (quando houver)
            chave = registro["num_registro"].strip()
            if chave and chave in vistos:
                total_dup += 1
                continue
            if chave:
                vistos.add(chave)

            todos.append(registro)
            n_tabela += 1

        print(f"   ✅ '{tabela}': {n_tabela} laudos aproveitados.")

    conn.close()

    if not todos:
        print("\n❌ Nenhum laudo importado. Verifique os nomes das colunas.")
        return

    # grava no SQLite, sem duplicar número de registro já existente
    banco.inicializar()
    novos = 0
    ja_existiam = 0
    for registro in todos:
        num = registro["num_registro"].strip()
        uuid_ = registro.pop("uuid")
        if num and banco.num_registro_existe(num, uuid_):
            ja_existiam += 1
            continue
        dados = {c: registro.get(c, "") for c in banco.CAMPOS}
        banco.salvar_laudo(uuid_, dados)
        novos += 1

    print("\n" + "=" * 70)
    print("RESUMO:")
    print(f"  Linhas lidas no Access:        {total_lidos}")
    print(f"  Linhas vazias ignoradas:       {total_vazios}")
    print(f"  Duplicatas (entre tabelas):    {total_dup}")
    print(f"  Já existiam no banco:          {ja_existiam}")
    print(f"  Novos laudos importados:       {novos}")
    print(f"  TOTAL no banco agora:          {banco.contar()}")
    print(f"  Arquivo: {banco.ARQUIVO_DB}")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    try:
        if MODO == "explorar":
            explorar()
        else:
            importar()
    except pyodbc.Error as e:
        print("\n❌ Erro de conexão com o Access:")
        print(f"   {e}")
        print("\nDicas:")
        print("  • Instalou o Microsoft Access Database Engine?")
        print("  • A senha e o caminho estão corretos?")
        print("  • Python e o Access Engine são ambos 64 bits (ou ambos 32)?")

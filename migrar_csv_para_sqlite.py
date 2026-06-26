"""
migrar_csv_para_sqlite.py — Converte o laudos.csv antigo para o novo laudos.db

Use UMA vez, para não perder os laudos já importados do Access.
Rode na sua máquina:  python migrar_csv_para_sqlite.py
"""

import uuid
import pandas as pd
from pathlib import Path
import banco

CSV = Path(__file__).parent / "dados" / "laudos.csv"


def migrar():
    if not CSV.exists():
        print(f"❌ Não encontrei {CSV}. Nada a migrar.")
        return

    df = pd.read_csv(CSV, dtype=str, keep_default_na=False)
    print(f"📄 {len(df)} laudos no CSV. Migrando para o SQLite...")

    banco.inicializar()
    migrados = 0
    for _, row in df.iterrows():
        uuid_ = row.get("uuid") or str(uuid.uuid4())
        dados = {c: row.get(c, "") for c in banco.CAMPOS}
        banco.salvar_laudo(uuid_, dados)
        migrados += 1

    print(f"✅ {migrados} laudos migrados para {banco.ARQUIVO_DB}")
    print(f"   Total no banco agora: {banco.contar()}")
    print("\nPode renomear o laudos.csv antigo para backup (ex: laudos_backup.csv).")


if __name__ == "__main__":
    migrar()

# Sistema de Laudos Histopatológicos — UFRGS

Sistema para emissão e gestão de laudos de exame histopatológico do
Laboratório de Patologia da Faculdade de Odontologia da UFRGS.

> ⚠️ **Aviso de privacidade (LGPD):** este repositório contém **apenas o código**
> do sistema. **Nenhum dado de paciente** é incluído. O banco de dados real
> roda localmente e nunca deve ser enviado para o GitHub ou qualquer nuvem
> pública.

---

## O que o sistema faz

- 📝 Cadastro e edição de laudos histopatológicos
- 🔍 Busca rápida (nome, registro, data, diagnóstico, etc.), com paginação
- 📄 Geração de PDF do laudo (frente com dados + verso com fotomicrografias)
- 📊 Estatísticas: casos por ano, diagnósticos mais comuns, distribuição por
  gênero, localizações, evolução de um diagnóstico, e comparação entre
  diagnóstico clínico e histopatológico
- 🔒 Login de acesso e registro de log de ações
- 📷 Controle de acervo de fotos (clínica e de biópsia)

---

## Tecnologias

- **Python 3.11+**
- **Streamlit** — interface web local
- **SQLite** — banco de dados local (um arquivo)
- **ReportLab** — geração de PDF
- **Pillow** — otimização de imagens
- **pandas / openpyxl** — manipulação de dados e Excel

---

## Como rodar (ambiente de exemplo)

> Como o repositório não traz dados, o sistema inicia com um banco vazio.
> É possível cadastrar laudos de teste para experimentar.

```bash
# 1. Instalar as dependências
pip install -r requirements.txt

# 2. Rodar o sistema
streamlit run laudos.py
```

O navegador abre automaticamente em `http://localhost:8501`.

**Login de exemplo:** os usuários e senhas ficam definidos no início do
`laudos.py`. Em produção, devem ser alterados.

---

## Estrutura dos arquivos

| Arquivo | O que faz |
|---|---|
| `laudos.py` | Aplicação principal (interface dos laudos) |
| `banco.py` | Camada de banco de dados (SQLite) |
| `laudo_pdf.py` | Geração do PDF do laudo |
| `pages/` | Páginas adicionais (Estatísticas) |
| `importar_access.py` | Importação de dados de um arquivo Access (uso local) |
| `padronizar_datas.py` | Padroniza datas para DD/MM/AAAA |
| `limpar_numeros.py` | Remove sufixos ".0" dos números de registro |
| `limpar_genero_e_obvios.py` | Padroniza gênero e duplicatas óbvias |
| `detector_diagnosticos_v2.py` | Detecta diagnósticos histopatológicos parecidos |
| `detector_diagnosticos_clinico.py` | Detecta diagnósticos clínicos parecidos |
| `detector_localizacao.py` | Detecta localizações anatômicas parecidas |

---

## Privacidade e segurança

Este sistema lida com dados sensíveis de saúde, protegidos pela
**Lei Geral de Proteção de Dados (LGPD)**. Por isso:

- O banco de dados (`dados/laudos.db`) **nunca** é versionado (veja `.gitignore`).
- Imagens de pacientes **não** são incluídas no repositório.
- O sistema foi projetado para rodar **localmente / offline**.
- Qualquer migração para nuvem deve passar pela avaliação institucional da UFRGS.

---

## Licença e contexto

Projeto acadêmico desenvolvido no âmbito da pós-graduação da Faculdade de
Odontologia da UFRGS. Uso restrito ao contexto da instituição.

# Jurimetria RCE + Saúde Pública — v2.1

> **Responsabilidade Civil do Estado em Saúde** com **paginação integral do DataJUD**, **detector híbrido de “acordo”**, e **módulo de inferência** (IC de proporções, Fisher 2×2 e Kaplan–Meier “tempo até acordo”).
> Saída consolidada em **Excel** com múltiplas abas analíticas.

---

## Sumário

* [Visão Geral](#visão-geral)
* [Principais Funcionalidades (v2.1)](#principais-funcionalidades-v21)
* [Arquitetura do Pipeline](#arquitetura-do-pipeline)
* [Instalação](#instalação)
* [Execução Rápida](#execução-rápida)
* [Parâmetros de Linha de Comando](#parâmetros-de-linha-de-comando)
* [Modelo de Dados & Variáveis](#modelo-de-dados--variáveis)
* [Detector de “Acordo” (híbrido)](#detector-de-acordo-híbrido)
* [Metodologia Estatística](#metodologia-estatística)
* [Abas do Excel (saídas)](#abas-do-excel-saídas)
* [Limitações & Boas Práticas](#limitações--boas-práticas)
* [Roteiro de Evolução](#roteiro-de-evolução)
* [Contribuindo](#contribuindo)
* [Licença](#licença)
* [Avisos de Compliance (LGPD & Fontes)](#avisos-de-compliance-lgpd--fontes)

---

## Visão Geral

Este repositório contém o script `jurimetria_rce_saude_v21.py`, que implementa um **pipeline completo** de jurimetria para análises de **Responsabilidade Civil do Estado (RCE)** em **Saúde Pública** no âmbito dos **Tribunais Estaduais** brasileiros, consumindo a **API Pública do DataJUD (CNJ)**.

O pipeline vai de **coleta** → **sanitização** → **construção de variáveis jurídicas** (tutela, acordo, decisão) → **métricas descritivas** → **inferência estatística** → **exportação** em planilha **Excel** com abas prontas para exploração e apresentação.

---

## Principais Funcionalidades (v2.1)

* **Paginação integral** por **janelas temporais** (`--inicio/--fim` + `--janela-dias`) combinada com `from/size`, para cobrir períodos extensos respeitando limites do backend do DataJUD.
* **Detector de “acordo” híbrido**: regex + lista estendida de termos + **negações** + **normalização de acentos**, reduzindo falsos positivos/negativos na leitura de `movimentos.nome`.
* **Inferência plug-and-play**:

  * **IC 95%** (Wilson) para proporções;
  * **Fisher 2×2** (bicaudal) para associação **Tutela × Acordo** (com OR corrigida em caso de zeros);
  * **Kaplan–Meier** (KM) para **“tempo até acordo”** **condicionado à primeira tutela** (censura à direita, variância de Greenwood).
* **Excel** com múltiplas abas: **Resumo\_Executivo**, **Processos\_Detalhados**, **Análise por Classe**, **Análise Temporal**, **Inferência (Proporções/IC)**, **Fisher 2×2 (tabela e meta)**, **KM (curva e estatísticas)** e **Parâmetros de Consulta**.

---

## Arquitetura do Pipeline

```
DataJUD API  →  Paginação (janelas Δt)  →  Parsing de processos
                                  ↓
                   Sanitização de datas e textos
                                  ↓
        Sinais jurídicos (tutela, acordo, decisão, sentença)
                                  ↓
         Métricas descritivas + tempos (tramitação, tutela→acordo)
                                  ↓
 Inferência (IC, Fisher 2×2, Kaplan–Meier tempo até acordo)
                                  ↓
                   Exportação Excel (abas analíticas)
```

---

## Instalação

Requer Python 3.9+.

```bash
# 1) Clonar este repositório
git clone <URL-do-seu-repo>
cd <pasta-do-repo>

# 2) Criar ambiente (opcional, mas recomendado)
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 3) Instalar dependências
pip install -U requests pandas numpy openpyxl
```

> **API Key do DataJUD**
> Defina sua chave pública em variável de ambiente:
>
> ```bash
> export DATAJUD_API_KEY="SUA_CHAVE_DO_CNJ"
> ```

---

## Execução Rápida

```bash
python3 jurimetria_rce_saude_v21.py \
  --tribunal TJMT \
  --inicio 2018-01-01 \
  --fim 2025-09-04 \
  --page-size 2000 \
  --janela-dias 90 \
  --limite 100000 \
  --nao-perguntar
```

**Argumentos essenciais**:

* `--tribunal`: sigla (ex.: `TJMT`, `TJRJ`, `TJSP`).
* `--inicio`, `--fim`: intervalo de data de ajuizamento.
* `--janela-dias`: tamanho da janela temporal para paginação (ex.: 90).
* `--page-size`: tamanho da página (até \~10.000, sujeito ao backend).
* `--limite`: teto de processos a coletar.

---

## Parâmetros de Linha de Comando

| Parâmetro         | Tipo | Default | Descrição                                        |
| ----------------- | ---- | ------- | ------------------------------------------------ |
| `--tribunal`      | str  | `TJMT`  | Sigla do Tribunal (ex.: `TJMT`)                  |
| `--inicio`        | date | —       | Data inicial (YYYY-MM-DD) para `dataAjuizamento` |
| `--fim`           | date | —       | Data final (YYYY-MM-DD)                          |
| `--page-size`     | int  | 2000    | Tamanho da página por requisição                 |
| `--janela-dias`   | int  | 90      | Largura da janela temporal (dias)                |
| `--limite`        | int  | 100000  | Limite total de processos                        |
| `--nao-perguntar` | flag | off     | Pula confirmação interativa                      |

> Dica: configure por variáveis de ambiente (`DATAJUD_TRIBUNAL`, `DATAJUD_INICIO`, `DATAJUD_FIM`, etc.) se preferir.

---

## Modelo de Dados & Variáveis

**Unidade de análise**: processo.

**Filtros de coleta**:

* `assuntos.codigo` em uma lista temática de **RCE/saúde** (parametrizada no script).

**Sinais jurídicos por processo**:

* `tem_tutela`: `True` se **algum movimento** tem **código** em uma *whitelist* de tutelas (ex.: 51, 60, 85, 26, 581, 454).
* `tem_acordo`: `True` se **algum movimento** tem **nome** compatível com **acordo** via detector híbrido (regex + negações).
* `tem_deferimento` / `tem_indeferimento`: busca textual (com normalização) em `movimentos.nome`.
* `tem_sentenca`: presença de “sentença”, “julgamento” ou “decisão”.

**Tempos (dias)**:

* `dias_tramitacao` = `dataHoraUltimaAtualizacao` − `dataAjuizamento`.
* `dias_tutela_acordo` = **primeiro acordo** − **primeira tutela** (quando ambos existem).
* `dias_followup_tutela` = `dataHoraUltimaAtualizacao` − **primeira tutela** (censura quando não há acordo).

**Sanitização**:

* Remoção de datas inválidas/absurdas (ex.: anos 2261–2263, fora de 1990–2035).
* Normalização de texto (minúsculo, sem acentos) para casamentos robustos.

---

## Detector de “Acordo” (híbrido)

* **Positivos** (exemplos): `acordo`, `homologacao`, `conciliacao`, `mediacao`, `transacao`, `composicao`, `autocomposicao`, `termo de acordo`, `acordo (judicial|extrajudicial)`, `composicao amigavel`, `convencao`, `ajuste`.
* **Negações** (descartam “acordo”): `sem acordo`, `não houve (acordo|composição|...)`, `(acordo|...) frustrad*`, `infrutifer*`, `inexit*`, `tentativa de (acordo|...)`, `não homolog*`, `homologação negad*`.

> **Por que híbrido?** Reduz falsos positivos (ex.: “tentativa de conciliação frustrada”) e falsos negativos (ex.: “transação”, “composição”) sem depender de códigos específicos e heterogêneos por tribunal.

---

## Metodologia Estatística

**Descritiva**:

* Proporções: `taxa_tutela`, `taxa_acordo`, `tutela ∩ acordo`, `Pr(acordo | tutela)`, `Pr(deferimento | decisão)`;
* Tempos: média/mediana/mín/máx de `dias_tramitacao` e média/mediana de `dias_tutela_acordo`.

**Inferencial**:

* **Intervalos de Confiança (95%)** para proporções via **Wilson** (mais estável que Wald).
* **Teste exato de Fisher (2×2)**: associação entre **Tutela** (sim/não) × **Acordo** (sim/não), odds ratio com correção de Haldane-Anscombe quando necessário.
* **Kaplan–Meier (KM)**: **tempo até acordo** **condicionado à primeira tutela**, com **censura à direita** (sem acordo até a última atualização). Variância de **Greenwood**.

  * Amostra da KM: apenas processos com **primeira tutela** registrada;
  * Eventos: acordo;
  * Censuras: sem acordo até o fim do follow-up.

> **Atenção:** o pipeline **não** faz identificação causal. Para estimar efeito de tutela em acordo/tempos, considere **propensity score**, **Cox com covariáveis**, efeitos fixos por **comarca/ano** e análises de **robustez**.

---

## Abas do Excel (saídas)

* **Resumo\_Executivo** – visão geral (contagens, taxas e tempos).
* **Processos\_Detalhados** – por processo (sinais jurídicos, tempos e movimentos relevantes).
* **Analise\_por\_Classe** – groupby classe (taxas e efetividade).
* **Analise\_Temporal** – por ano de ajuizamento (volumes e taxas).
* **Inferencia\_Proporcoes** – estimativas com **IC 95% (Wilson)**.
* **Fisher\_2x2\_Tutela\_Acordo\_Tabela** – tabela de contingência.
* **Fisher\_2x2\_Tutela\_Acordo\_Meta** – **OR** e **p-valor** (bicaudal).
* **KM\_Tutela\_Acordo** – curva de sobrevivência e estatísticas.
* **Parametros\_Consulta** – trilha de auditoria (tribunal, datas, paginação, códigos usados).

---

## Limitações & Boas Práticas

* **Cobertura**: sempre que possível, use `--inicio/--fim` para **janelas temporais**. Sem datas, a API pode limitar a profundidade (offset).
* **Misclassificação**: nomes de movimentos variam por tribunal; o detector híbrido mitiga, mas não elimina erros. Avalie **amostras rotuladas**.
* **Censura**: `dias_tramitacao` usa última atualização (proxy de “andamento”) e **não** tempo até sentença/baixa. Para fins de encerramento, acrescente movimentos de baixa/transitado.
* **Causalidade**: o repositório entrega **descrição** + **inferência básica**. Para **efeito causal**, aplicar métodos apropriados (PS-matching/weighting, modelos de sobrevivência com covariáveis, efeitos fixos).
* **Reprodutibilidade**: registre `Parametros_Consulta` e versões de dependências.

---

## Roteiro de Evolução

* [ ] **Gráficos** (KM e barras com IC) como imagens e/ou em uma aba “Charts” no Excel.
* [ ] **Mapeamento normativo** de movimentos (códigos CNJ) para “homologação de acordo” por tribunal.
* [ ] **Propensity Score** + **Cox PH** com covariáveis (classe, vara, comarca, ano, especialidade).
* [ ] **Paginação por `search_after`** (quando disponível) para maior eficiência.
* [ ] **CLI** para filtros por comarca/órgão/classse.
* [ ] **Dockerfile** para execução reprodutível.

---

## Contribuindo

Contribuições são bem-vindas!

* Abra uma **issue** com bug/ideia.
* Faça um **fork** e envie **PR** com descrição clara, testes e notas de impacto.
* Para alterações maiores (ex.: heurísticas do detector, modelos), proponha design na issue antes de implementar.

---

## Licença

Defina a licença do repositório (ex.: MIT/Apache-2.0).
Inclua o arquivo `LICENSE` na raiz.

---

## Avisos de Compliance (LGPD & Fontes)

* A **API Pública do DataJUD** fornece dados processuais **de acesso público**. Ainda assim, **recomenda-se**:

  * Evitar a exposição de **dados pessoais** desnecessários nas saídas/prints;
  * Usar os resultados **apenas** para finalidades legítimas (pesquisa, ensino, gestão pública/privada);
  * Registrar parâmetros de consulta e garantir **reprodutibilidade/auditabilidade**.
* Este projeto **não** substitui a leitura técnica/jurídica dos autos; é um **instrumento auxiliar** para **gestão de risco, negociação e pesquisa**.

---

### Citation / Como citar

> “Jurimetria RCE + Saúde Pública v2.1 (DataJUD): paginação integral, detector híbrido de acordo e inferência (IC, Fisher, KM). Repositório GitHub, 2025.”

---

### Contato

Abra uma **issue** no GitHub para dúvidas técnicas, sugestões e melhorias.

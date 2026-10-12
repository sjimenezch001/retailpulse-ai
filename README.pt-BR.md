# RetailPulse AI — resumo em português

[README canônico em inglês](README.md) · [Evidências](docs/portfolio_evidence.md)

Projeto pessoal de portfólio para análise de demanda no varejo. Ajuda gestores
comerciais, analistas de BI e planejadores a consultar vendas históricas, comparar
erros de previsão e rastrear a origem das métricas. Não representa uma implantação
em cliente nem comprova ganhos financeiros.

Meu foco neste portfólio é conectar perguntas de negócio a métricas SQL
reproduzíveis, interpretação de relatórios e avaliação de previsões. O desenvolvimento
utilizou assistência de agentes e validações automatizadas, com resultados e
decisões de lançamento identificados nas evidências.

![Captura real da aplicação com dados históricos M5](docs/evidence/rp10_ui/overview_light_en.png)

## Resultados verificados

- **4.530.250 unidades observadas** no piloto histórico M5 de três lojas e dois
  departamentos, encerrado em 22/05/2016. [Fonte](docs/evidence/rp09_real_acceptance.json).
- LightGBM: **74,825958% de WMAPE** no teste, contra **79,482353%** da média móvel.
  O MAE melhora; o RMSE piora: **2,431177 contra 2,361194**. A seleção usou apenas
  validação. [Model card](docs/model_card.md#final-one-time-test).
- **36 resultados esperados aprovados** na avaliação local: **22 chamadas Ollama
  validadas**, **14 resultados de pré-validação**, **zero fallback**. São casos
  selecionados, não prova de precisão universal. [Avaliação](docs/evidence/rp09_live_evaluation.json).
- RP-11 corrigido: **254 testes**, **88,15% de cobertura** combinada de linhas e
  ramificações; mínimo de **85%**. [Relatório](docs/evidence/rp11/ci_corrections.json).
  A validação local mais recente reportou **440 testes** e **88,15% de cobertura**.
  Windows, Ubuntu, container e aws-offline passaram no
  [CI publicado de main](https://github.com/sjimenezch001/retailpulse-ai/actions/runs/38274725819)
  da revisão `685839e7`, após os PRs #16 e #17. Esse CI antecede o candidato v1.0.0.

## Decisões e relatórios

A execução local e a demonstração sintética permitem reproduzir o fluxo sem
provisionar nuvem. DuckDB concentra as definições SQL; o Power BI importa dados
reconciliados com Gold. As ferramentas de leitura do assistente restringem o escopo
das respostas. O laboratório AWS foi separado e temporário.

- **Executive Overview:** tendências e comparação entre períodos, com cobertura
  de preços e atualização histórica para interpretar os indicadores.
- **Store & Product Diagnostics:** diferenças entre lojas, departamentos e produtos,
  variações semanais e sinais de picos, sem atribuir causalidade.
- **Forecast Performance:** demanda observada versus prevista, erros por horizonte
  ou segmento e comparação com os modelos de referência.

Veja [critérios técnicos](README.md#design-decisions-and-trade-offs) e
[lições do laboratório AWS](README.md#engineering-lessons-from-the-aws-demonstration).

## Executar a demonstração portátil

Requer Git, Python 3.12 e internet para instalar os pacotes. No PowerShell:

```powershell
git clone https://github.com/sjimenezch001/retailpulse-ai.git
cd retailpulse-ai
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe scripts/tasks.py setup
.\.venv\Scripts\python.exe -m retailpulse demo --mode synthetic --provider deterministic
```

Abra <http://127.0.0.1:8501>; documentação da API em <http://127.0.0.1:8000/docs>.
Ctrl+C encerra os servidores. Não requer Kaggle, Ollama, treinamento ou Docker.
Pergunte **How many units did SYN_A sell during all observed dates?**: são **378
unidades sintéticas**, com resposta determinística offline. As previsões simuladas
da demonstração não medem o desempenho real do LightGBM.

O fluxo implementado é M5 → Bronze → Silver → Gold/DuckDB → previsões/MLflow,
Power BI e ferramentas aprovadas → FastAPI → Streamlit. O roteador define o
escopo; o modelo local opcional confirma a seleção estruturada; ferramentas buscam
os números e a apresentação determinística exibe a resposta. Não há SQL livre
gerado pelo modelo. A aplicação continua em inglês/espanhol, com temas claro/escuro.

Consulte [modo real e roteiro](docs/web_demo.md), [Power BI](dashboards/powerbi/BUILD_GUIDE.md),
[assistente e Ollama](docs/agent_demo.md) e [reprodução isolada](docs/evidence/rp13_gate.md#clean-environment-reproduction).
Dados reais, bancos preenchidos, modelos e PBIX permanecem locais.

## Limites e situação

Vendas históricas não são estoque atual. `revenue_proxy` não é receita auditada;
preços ausentes não são zero. O assistente é limitado e sem contexto conversacional;
a aplicação local não oferece autenticação para hospedagem pública. A verificação
por outra pessoa permanece **PENDING**. A reprodução automatizada continua
sendo uma categoria distinta de evidência.

RP-00 a RP-11 implementados; **RP-12D validou serviços AWS reais com dados
sintéticos e documentou a remoção do laboratório**. Veja o [relatório final](docs/aws_teardown_report.md).
Os PRs #16 e #17 publicaram a documentação do portfólio. A versão
**1.0.0** corresponde à **Portfolio Release**; consulte as
[notas de versão](docs/release_notes_v1.0.0.md) e
[publicações do GitHub](https://github.com/sjimenezch001/retailpulse-ai/releases)
para conferir a publicação. Licencio o código original sob a [licença MIT](LICENSE);
dependências e materiais externos mantêm suas próprias licenças. As permissões
dos dados M5 são independentes; dados reais não são redistribuídos. Veja o
[checklist de lançamento](docs/release_checklist.md).

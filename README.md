# Desafio I2A2 D5 — Comunicação Proativa

MVP de uma ferramenta inteligente para comunicação proativa com segurados a partir de eventos meteorológicos externos.

## Escopo atual

O projeto está sendo desenvolvido incrementalmente. Este incremento consolida a arquitetura/contratos, as regras de seguro V1 e a fundação do Agente do Tempo:

- arquitetura modular entre domínio, integrações, serviços e API;
- regras V1 determinísticas do Rules Engine;
- dataset fictício e repository de segurados;
- consumo de avisos meteorológicos públicos do INMET;
- consumo de observações SYNOP publicadas pelo INMET no WIS2;
- normalização para um modelo interno independente da fonte;
- detecção determinística de `HEAVY_RAIN`, `HAIL` e `STRONG_WIND`;
- API HTTP mínima com FastAPI;
- provider mock, testes sem dependência da internet e integração externa opt-in;
- decisões técnicas documentadas para INMET/WIS2 e Grok.

LLM, geração de mensagens e notificações continuam fora do escopo desta etapa. A decisão arquitetural para a etapa futura é utilizar o Grok exclusivamente na geração/personalização das mensagens; ele não participará da decisão de negócio, compatibilidade de apólice ou prioridade.

## Arquitetura

```text
INMET / WIS2
    ↓
INMETWeatherProvider
    ↓  (payloads externos convertidos em WeatherInput)
WeatherService
    ↓
WeatherDetector
    ↓
WeatherSnapshot / WeatherEvent ──→ FastAPI /weather
            + Insured
                ↓
       InsuranceRulesEngine
                ↓
       NotificationDecision
```

Para avaliar a exposição de um único evento:

```text
WeatherEvent
    ↓
CoordinateRadiusMatcher (25 km)
    ↓
InsuredRepository (data/insureds.json)
    ↓
InsuranceRulesEngine
    ↓
NotificationDecision[] ──→ FastAPI /evaluate
```

O domínio não recebe o JSON original do INMET. O provider é o único componente que conhece os formatos externos e entrega `WeatherInput`, `WeatherAlert` e `Measurements` já normalizados. Isso permite trocar a fonte meteorológica sem alterar o detector ou a API.

Detalhes e responsabilidades estão em [`docs/architecture.md`](docs/architecture.md).

## Insurance Domain

A fundação do domínio de seguros representa segurados, localização, apólices e o contrato futuro de decisão:

```text
WeatherEvent       → Weather Domain
Insured / Policy   → Insurance Domain
WeatherEvent + Insured → InsuranceRulesEngine
InsuranceRulesEngine → NotificationDecision
```

`Location` é compartilhado pelos dois domínios e mantém as mesmas validações de latitude, longitude e finitude. A associação entre evento e tipo de seguro está centralizada no Rules Engine descrito abaixo.

O dataset fictício está em [`data/insureds.json`](data/insureds.json). Cada registro contém `insured_id`, `name`, `location` e `policies`; cada apólice contém `policy_id`, `policy_type` (`HOME` ou `AUTO`) e `status` (`ACTIVE` ou `INACTIVE`).

## Rules Engine

O [`InsuranceRulesEngine`](src/domain/insurance/rules_engine.py) recebe um `WeatherEvent` e um `Insured` e retorna uma única `NotificationDecision`. Ele não acessa APIs, não lê o dataset diretamente, não chama LLM e não faz matching geográfico definitivo.

O [`WeatherNotificationOrchestrator`](src/services/weather_notification_orchestrator.py) coordena o fluxo para vários segurados. O [`CoordinateRadiusMatcher`](src/domain/insurance/location_matcher.py) calcula a distância por Haversine e só encaminha ao Rules Engine quem estiver a até `WEATHER_EXPOSURE_RADIUS_KM` (padrão: 25 km). O limite é inclusivo. Essa distância é uma simplificação técnica do protótipo: proximidade geográfica representa apenas exposição potencial e não representa cobertura securitária, área oficial de alerta ou critério real de sinistro.

O [`JsonInsuredRepository`](src/repositories/insured_repository.py) é a camada responsável por ler e validar `data/insureds.json`. O orchestrator não conhece o formato JSON e preserva a ordem fornecida pelo repository. Segurados fora do raio não são avaliados pelo Rules Engine.

| Evento | Evidência | Apólice | Prioridade |
|---|---|---|---|
| `HEAVY_RAIN` | `ALERT` | `HOME` ativa | `HIGH` |
| `HEAVY_RAIN` | `OBSERVATION` | `HOME` ativa | `HIGH` |
| `HAIL` | `ALERT` | `AUTO` ativa | `HIGH` |
| `HAIL` | `ALERT` | `HOME` ativa | `MEDIUM` |
| `STRONG_WIND` | `ALERT` | `HOME` ativa | `HIGH` |
| `STRONG_WIND` | `OBSERVATION` | `HOME` ativa | `MEDIUM` |
| `STRONG_WIND` | `ALERT` | `AUTO` ativa | `HIGH` |
| `STRONG_WIND` | `OBSERVATION` | `AUTO` ativa | `MEDIUM` |

As regras são simplificações definidas para o MVP acadêmico e não representam critérios reais de subscrição ou regulação de seguros.

## Fonte meteorológica

O provider concreto combina duas interfaces públicas do INMET:

1. **Avisos ativos:** `https://apiprevmet3.inmet.gov.br/avisos/ativos`

   É usado para os eventos severos. O alerta informa fenômenos, severidade, período, riscos e polígono geográfico. Granizo só é gerado quando o texto do próprio aviso contém o sinal explícito `granizo`.

2. **WIS2 SYNOP:** `https://wis2bra.inmet.gov.br/oapi/collections/urn:wmo:md:br-inmet:synop/items`

   É usado para observações de estação próximas à localização consultada. A coleção publica features por medição; o provider identifica a estação por `wigos_station_identifier`, escolhe a estação mais próxima usando a posição do relatório mais recente e seleciona o relatório mais recente dessa estação.

As interfaces são encapsuladas por `INMETWeatherProvider`. A primeira foi escolhida por disponibilizar diretamente os avisos oficiais necessários para chuva intensa, granizo e vento; a coleção SYNOP complementa o evento com observações de temperatura, precipitação e vento.

## Decisões futuras de IA

O LLM escolhido para uma etapa posterior é o **Grok**. Sua responsabilidade será gerar ou personalizar o texto após a produção de uma `NotificationDecision`. O Grok não deverá selecionar segurados, avaliar apólices, calcular prioridade ou substituir as regras determinísticas do Rules Engine. Nesta etapa não há integração com LLM.

## Contrato `WeatherEvent`

O modelo canônico possui:

```text
event_id
event_type: HEAVY_RAIN | HAIL | STRONG_WIND
evidence_type: ALERT | OBSERVATION
severity: LOW | MEDIUM | HIGH | EXTREME
timestamp: datetime UTC-aware
location: latitude, longitude, municipality opcional
measurements: Celsius, millimeters, km/h
source
source_reference opcional
description opcional
```

## Regras do Agente do Tempo

Os thresholds para observações ficam centralizados em `WeatherThresholds` e podem ser configurados por variáveis de ambiente:

| Evento | Sinal de observação | Threshold padrão |
|---|---|---:|
| `HEAVY_RAIN` | precipitação horária | `20 mm/h` |
| `HEAVY_RAIN` | precipitação acumulada | `50 mm` |
| `STRONG_WIND` | velocidade ou rajada | `60 km/h` |
| `HAIL` | aviso do INMET contendo `granizo` | sem inferência numérica |

Os limites são simplificações definidas para o MVP, não regras oficiais de subscrição do INMET. Para severidade de observações, os limites altos são `50/80 mm/h` e `80/100 km/h`; acumulados diários usam `100/150 mm`. Para avisos oficiais, a severidade do INMET é mapeada deterministicamente: `Perigo Potencial` → `MEDIUM`, `Perigo` → `HIGH` e `Grande Perigo` → `EXTREME`.

Todos os timestamps do domínio são UTC-aware. O INMET informa observações em UTC; nenhuma conversão para horário local é feita no domínio. Valores ausentes ou inválidos da fonte, como `9999`, `-9999`, `999.9`, `-999.9`, `Null` e campos vazios, são descartados da medição e não geram eventos. Se o WIS2 não retornar nenhuma observação, o provider gera erro explícito; ele não fabrica um timestamp com o relógio local.

## Instalação

Requer Python 3.12 ou superior.

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
```

## Configuração

```bash
cp .env.example .env
```

Os valores padrão já apontam para as interfaces públicas do INMET. O arquivo `.env` é ignorado pelo Git. Os thresholds podem ser ajustados sem modificar o código.

## Execução

```bash
uvicorn src.main:app --reload
```

Endpoints disponíveis:

```text
GET /health
GET /weather?latitude=-15.79&longitude=-47.93
POST /evaluate
```

Exemplo:

```bash
curl 'http://127.0.0.1:8000/weather?latitude=-15.79&longitude=-47.93'
```

A resposta é um `WeatherSnapshot` normalizado, com localização, medições, fonte, horário da observação e lista de `WeatherEvent`. O JSON bruto do INMET não é exposto.

`POST /evaluate` recebe os campos essenciais de um evento e retorna as decisões dos segurados potencialmente expostos. `event_id`, `timestamp`, `measurements` e `source` são opcionais na borda HTTP e recebem defaults; internamente o orchestrator sempre recebe um `WeatherEvent` canônico validado. Exemplo mínimo:

```bash
curl -X POST 'http://127.0.0.1:8000/evaluate' \
  -H 'Content-Type: application/json' \
  -d '{
    "event_type": "HEAVY_RAIN",
    "evidence_type": "ALERT",
    "severity": "HIGH",
    "location": {"latitude": -15.79, "longitude": -47.93}
  }'
```

A saída contém somente `NotificationDecision[]`; ainda não há mensagens, LLM ou envio de notificações.

Documentação interativa: <http://127.0.0.1:8000/docs>.

## Testes

```bash
pytest
```

Os testes unitários usam `httpx.MockTransport`, fixtures locais e `MockWeatherProvider`; portanto não precisam de acesso à internet. Existe um teste de integração externa marcado como `integration`, desabilitado por padrão, que pode ser executado com `RUN_EXTERNAL_INTEGRATION=1 pytest -m integration` quando houver conectividade com o INMET.

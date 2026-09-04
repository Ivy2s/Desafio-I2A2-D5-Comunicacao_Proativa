# Arquitetura do Agente do Tempo

## Fluxo

```text
INMET Avisos + WIS2 SYNOP
            ↓
    INMETWeatherProvider
            ↓
     parser/normalizer
            ↓
       WeatherInput
            ↓
      WeatherDetector
            ↓
      WeatherEvent(s)
            ↓
       WeatherService
        ↓
        FastAPI /weather
```

O domínio de seguros é mantido separado:

```text
WeatherEvent
    ↓
Weather Domain

Insured + Policy
    ↓
Insurance Domain
    ↓
InsuranceRulesEngine
    ↓
NotificationDecision
```

## Orquestração de exposição e regras

Para um evento já normalizado, a aplicação executa uma etapa de exposição geográfica antes do Rules Engine:

```text
WeatherEvent
    ↓
LocationMatcher
    ↓
InsuredRepository
    ↓
InsuranceRulesEngine
    ↓
NotificationDecision[]
```

`WeatherNotificationOrchestrator` coordena esse fluxo, preservando a ordem dos segurados recebidos. `CoordinateRadiusMatcher` responde somente se a localização do segurado está dentro do raio configurado; ele não conhece tipos de apólice nem decide elegibilidade. O Rules Engine continua sendo a única camada responsável por compatibilidade entre evento e apólices.

O adapter `JsonInsuredRepository` lê o dataset local e converte os registros para `Insured` por meio da validação Pydantic. Assim, o orchestrator recebe modelos de domínio e não acessa JSON diretamente. O repositório também pode ser substituído por um mock nos testes.

O endpoint `POST /evaluate` recebe um DTO HTTP com os campos essenciais, converte-o para um `WeatherEvent` canônico validado, carrega os segurados pelo repository configurado, executa o orchestrator e retorna as decisões produzidas pelo Rules Engine. Metadados omitidos pelo cliente recebem defaults somente na borda HTTP; o restante da aplicação não recebe um payload externo. O endpoint não gera mensagens nem envia notificações.

## Decisão de LLM

O provedor de LLM escolhido para uma etapa posterior é o **Grok**. Ele será usado somente pelo futuro Message Agent para geração ou personalização de mensagens a partir de uma `NotificationDecision`. Não terá responsabilidade por matching geográfico, seleção de segurados, compatibilidade de apólices ou prioridade. Nenhum código de LLM faz parte desta etapa.

O `InsuranceRulesEngine` recebe um `WeatherEvent` e um `Insured`, avalia as regras declaradas e retorna uma única decisão por segurado/evento.

## Responsabilidades

### `src/providers/weather/inmet.py`

É o adapter da infraestrutura externa. Ele:

- chama o endpoint de avisos ativos do INMET;
- filtra avisos pelo polígono que contém a coordenada consultada;
- chama a coleção WIS2 SYNOP e seleciona a estação mais próxima;
- identifica a estação pelo `wigos_station_identifier` estável (com fallback para o prefixo do `reportId`);
- seleciona a posição do relatório mais recente para comparar a proximidade e, dentro da estação escolhida, o relatório mais recente por `reportTime`;
- converte unidades externas para Celsius, milímetros e km/h;
- converte timestamps para UTC-aware;
- descarta sentinelas de ausência (`9999`, `Null` e vazio) e rejeita valores físicos inválidos;
- transforma os payloads em modelos internos;
- traduz timeout, erro HTTP e payload inválido para exceções próprias.

Nenhum outro componente precisa conhecer nomes de campos como `poligono`, `riscos`, `phenomenonTime`, `value` ou `maximum_wind_gust_speed`.

### `src/domain/weather/models.py`

Contém os contratos internos:

- `Location`;
- `Measurements`;
- `WeatherAlert`;
- `WeatherInput`;
- `WeatherEvent`;
- `WeatherSnapshot`.

Esses modelos não representam uma cópia do JSON do INMET. São estruturas do domínio do MVP.

### `src/domain/weather/detector.py`

Aplica regras determinísticas sobre dados normalizados:

- `HEAVY_RAIN`: alerta de chuvas intensas ou observação acima dos thresholds;
- `HAIL`: texto de aviso oficial contendo o fenômeno granizo;
- `STRONG_WIND`: aviso de vendaval, ventos intensos ou rajadas de vento, ou observação acima do threshold.

Cada `WeatherEvent` informa `evidence_type` como `ALERT` ou `OBSERVATION`. Assim, consumidores posteriores podem distinguir um evento gerado por aviso meteorológico de um evento derivado de medição.

O detector não acessa a internet e não usa LLM.

### `src/services/weather_service.py`

Orquestra provider e detector. Recebe `WeatherInput`, executa a detecção e devolve `WeatherSnapshot`.

### `src/api/routes/weather.py`

Expõe somente a camada HTTP. Não contém regras de evento nem detalhes de integração.

### `src/domain/insurance`

Contém os modelos estruturais `Insured`, `Policy` e `NotificationDecision`, além dos enums `PolicyType`, `PolicyStatus` e `NotificationPriority`. Esses modelos não decidem se uma notificação deve ser enviada.

`Location` vive em `src/domain/location.py` e é importado tanto pelo domínio meteorológico quanto pelo domínio de seguros, evitando duas implementações incompatíveis.

### `src/domain/insurance/rules_engine.py`

Contém a matriz declarativa `RULES` e `InsuranceRulesEngine`. O engine:

- considera somente apólices ativas;
- avalia todas as apólices;
- registra cada regra compatível uma única vez em `matched_rules`;
- escolhe a maior prioridade;
- produz razões determinísticas;
- retorna elegibilidade negativa quando não há regra compatível.

As regras são simplificações definidas para fins do MVP acadêmico e não representam critérios reais de subscrição ou regulação de seguros.

### `src/domain/insurance/location_matcher.py`

Define o protocolo `LocationMatcher`, a função Haversine e a implementação `CoordinateRadiusMatcher`. O raio padrão do MVP é 25 km, configurável por `WEATHER_EXPOSURE_RADIUS_KM`. O limite é inclusivo (`distance <= radius`). Se qualquer coordenada estiver ausente, não numérica, não finita ou fora dos limites geográficos, o matcher retorna `False`; o sistema não inventa uma localização.

Esse raio é uma simplificação técnica para o protótipo acadêmico. Estar geograficamente próximo do evento representa apenas exposição potencial; não representa cobertura securitária, área oficial de alerta, regra de subscrição ou critério real de sinistro.

### `src/repositories/insured_repository.py`

Expõe o contrato `InsuredRepository` e a implementação `JsonInsuredRepository`. O arquivo local deve conter uma lista de registros compatíveis com `Insured`; JSON malformado, estrutura diferente de lista, arquivo ausente ou registros inválidos geram `InsuredRepositoryError` explícito.

### `src/services/weather_notification_orchestrator.py`

Recebe `LocationMatcher`, `InsuranceRulesEngine` e, opcionalmente, `InsuredRepository` por construtor. Para cada segurado, primeiro verifica exposição; somente os expostos chegam ao Rules Engine. O orchestrator não reescreve `eligible`, `priority`, `reason` ou `matched_rules` e não executa processamento concorrente.

O matching geográfico do MVP é aplicado pelo `CoordinateRadiusMatcher` antes do Rules Engine. A presença de coordenadas próximas representa somente exposição potencial dentro da simplificação de 25 km; não é prova de cobertura, de área oficial de alerta ou de ocorrência de sinistro.

Na coleção SYNOP, a geometria pode variar entre relatórios da mesma estação. Por isso, coordenadas não são usadas como identidade da estação. O provider agrupa primeiro pelo identificador WIGOS, evitando que uma posição antiga e mais próxima faça o sistema descartar uma observação mais recente da mesma estação. Avisos meteorológicos continuam sendo tratados separadamente no endpoint de alertas e não substituem `observed_at` da observação SYNOP.

## Escolha das interfaces do INMET

O endpoint de avisos ativos é necessário porque o próprio aviso fornece o sinal semântico para fenômenos severos, especialmente granizo. O WIS2 SYNOP fornece observações estruturadas por estação e complementa o estado com medições.

Referências oficiais:

- [INMET WIS2 — catálogo de datasets](https://wis2bra.inmet.gov.br/)
- [WIS2 OGC API](https://wis2bra.inmet.gov.br/oapi/openapi?f=html)
- [Coleção SYNOP do WIS2](https://wis2bra.inmet.gov.br/oapi/collections/urn:wmo:md:br-inmet:synop?f=json)
- [Avisos públicos do INMET](https://apiprevmet3.inmet.gov.br/avisos/ativos)

O WIS2 disponibiliza o dataset de avisos como notificações MQTT e metadados, enquanto a interface HTTP pública de avisos ativos oferece diretamente os registros e polígonos necessários ao MVP. Por isso, as duas superfícies são utilizadas atrás de um único `WeatherProvider`.

## Testabilidade

`WeatherProvider` é um `Protocol`. A implementação real é `INMETWeatherProvider`; `MockWeatherProvider` fornece dados internos determinísticos. Os testes do detector usam `WeatherInput` e os testes do provider usam `httpx.MockTransport`, sem chamadas externas.

O matcher, o repository e o orchestrator também recebem dependências substituíveis. Os testes de orquestração usam engines e repositories de teste para verificar que segurados fora do raio não são avaliados e que a ordem de entrada é preservada.

## Configuração de thresholds

Os valores padrão estão em `WeatherThresholds` e podem ser sobrescritos por ambiente. A severidade de avisos oficiais vem do próprio INMET; severidade de eventos derivados apenas de observações é calculada pelo detector.

Os thresholds são simplificações de MVP adotadas pelo projeto e não devem ser tratados como regras oficiais do INMET. O INMET informa que dados de estações automáticas podem ser brutos e conter `9999`, `-9999`, `999.9`, `-999.9`, `Null` ou campos vazios para ausência de observação; esses valores são tratados como dados ausentes pelo adapter. Todos os datetimes aceitos pelos contratos de domínio são timezone-aware e normalizados para UTC.

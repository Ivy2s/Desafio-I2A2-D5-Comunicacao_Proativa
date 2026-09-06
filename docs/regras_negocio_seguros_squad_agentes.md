# Regras de negócio de seguros para uma squad de agentes inteligentes

## 1. Objetivo

Este documento define as regras de negócio para um protótipo de comunicação proativa com segurados. A solução deve monitorar eventos meteorológicos externos, identificar situações potencialmente prejudiciais aos bens segurados, selecionar os segurados elegíveis e gerar comunicações preventivas personalizadas.

O escopo está alinhado ao MVP proposto: consultar uma fonte pública de dados meteorológicos, detectar eventos relevantes, aplicar regras de decisão, gerar mensagens automaticamente e simular o envio da comunicação. O sistema não deve alterar coberturas, calcular indenizações, registrar sinistros ou substituir a regulação de sinistros.

> **Princípio central:** a squad pode recomendar ações preventivas, mas não pode criar cobertura, negar cobertura, prometer indenização ou afirmar que um sinistro ocorrerá.

## 2. Escopo funcional e limites

A solução deve cobrir, no mínimo, os seguintes cenários:

| Evento meteorológico | Produto-alvo | Objetivo da comunicação |
|---|---|---|
| Chuva intensa | Seguro residencial | Reduzir a exposição de telhados, janelas, áreas externas e sistemas elétricos. |
| Granizo | Seguro automóvel | Recomendar proteção do veículo e evitar deslocamentos desnecessários. |
| Ventos fortes | Seguro residencial e automóvel | Orientar sobre objetos soltos, estacionamento e áreas de risco. |
| Evento combinado | Produto aplicável ao risco | Aumentar a prioridade da mensagem quando mais de um perigo ocorrer na mesma janela. |

O protótipo deve utilizar a localização do risco segurado, como endereço residencial ou local habitual de guarda do veículo. A localização atual do segurado não é necessária para o MVP e não deve ser inferida sem fonte autorizada.

Estão fora do escopo a contratação de apólices, a alteração de dados cadastrais, a emissão de documentos contratuais, a abertura automática de sinistros, o acionamento de assistência 24 horas e o envio real de SMS, e-mail ou push.

## 3. Conceitos de negócio

| Conceito | Definição operacional |
|---|---|
| **Segurado** | Pessoa vinculada a uma apólice ativa e elegível para receber comunicação. |
| **Apólice ativa** | Apólice cuja vigência inclui o momento da avaliação e que não está cancelada, suspensa ou encerrada. |
| **Risco segurado** | Bem ou local coberto pela apólice, associado a uma localização válida. |
| **Evento meteorológico** | Ocorrência observada ou prevista por uma fonte externa, normalizada para o catálogo interno de eventos. |
| **Janela do evento** | Intervalo entre o início e o fim estimados do evento. Quando a fonte não informar esses horários, o sistema deve usar o período de validade do alerta ou a janela padrão configurada. |
| **Área de impacto** | Região geográfica na qual o evento pode afetar os riscos segurados. |
| **Severidade** | Classificação do potencial de impacto do evento: informativa, atenção ou crítica. |
| **Comunicação preventiva** | Mensagem destinada a reduzir a probabilidade ou a extensão de danos antes ou durante um evento. |
| **Simulação de envio** | Registro da comunicação como se fosse encaminhada, sem transmissão real para o canal do segurado. |

## 4. Princípios obrigatórios

1. **Separação entre decisão e redação.** A elegibilidade e a severidade devem ser calculadas por regras determinísticas. O modelo de linguagem pode redigir a mensagem, mas não pode decidir sozinho quem receberá a comunicação.
2. **Rastreabilidade.** Cada comunicação deve registrar a fonte dos dados, o horário da coleta, as regras acionadas, a versão das regras, o modelo utilizado e o resultado da simulação.
3. **Conservadorismo.** Na ausência de dados confiáveis, o sistema deve evitar uma comunicação assertiva sobre risco. Deve registrar a inconsistência e, se aplicável, usar uma mensagem genérica de baixa criticidade.
4. **Não invenção.** A mensagem não pode inventar endereço, cobertura, valor, prazo, probabilidade, assistência ou instrução que não estejam presentes nos dados autorizados.
5. **Privacidade por padrão.** O processamento deve utilizar apenas os dados necessários para identificar o risco, a apólice elegível e o canal de comunicação autorizado.
6. **Idempotência.** A mesma combinação de segurado, apólice, evento, janela e versão de regra não deve produzir comunicações duplicadas.
7. **Ação preventiva, não promessa contratual.** A comunicação deve recomendar cuidados e orientar o segurado a consultar os canais oficiais da seguradora quando necessário.

## 5. Modelo mínimo de dados

### 5.1. Registro do segurado e da apólice

```json
{
  "policy_id": "POL-000123",
  "customer_id": "CUS-000456",
  "product": "residencial",
  "status": "active",
  "valid_from": "2026-01-01T00:00:00-03:00",
  "valid_until": "2026-12-31T23:59:59-03:00",
  "risk_location": {
    "latitude": -23.5505,
    "longitude": -46.6333,
    "city": "São Paulo",
    "state": "SP",
    "reference": "bairro cadastrado"
  },
  "channels": {
    "sms": true,
    "email": true,
    "push": false
  },
  "communication_opt_out": false,
  "vehicle": {
    "type": "automobile",
    "garaging_location": null
  }
}
```

O sistema deve mascarar identificadores pessoais nos logs de aplicação e evitar armazenar nome completo, documento, telefone ou e-mail quando esses campos não forem necessários para a simulação.

### 5.2. Registro meteorológico normalizado

```json
{
  "source": "open_meteo_or_configured_provider",
  "source_event_id": "SRC-987654",
  "collected_at": "2026-09-06T18:00:00Z",
  "valid_from": "2026-09-06T21:00:00Z",
  "valid_until": "2026-09-07T03:00:00Z",
  "event_types": ["heavy_rain", "strong_wind"],
  "severity_from_source": "moderate",
  "precipitation_mm_1h": 28,
  "precipitation_mm_24h": 63,
  "wind_speed_kmh": 54,
  "wind_gust_kmh": 76,
  "hail_probability": null,
  "affected_area": {
    "geometry": "configured_polygon_or_radius",
    "center_latitude": -23.5505,
    "center_longitude": -46.6333
  },
  "source_url": "https://example.invalid/event/SRC-987654"
}
```

Os nomes dos campos são uma proposta de contrato interno. O agente de coleta deve adaptar o formato da API externa para esse contrato antes da análise de negócio.

## 6. Arquitetura da squad de agentes

A squad deve ser composta por agentes especializados, coordenados por um agente orquestrador. A implementação pode utilizar agentes independentes, funções tradicionais ou uma combinação dos dois, desde que as responsabilidades sejam preservadas.

| Agente | Responsabilidade | Pode decidir elegibilidade? | Saída principal |
|---|---|---:|---|
| **Orquestrador** | Controlar a execução, correlacionar as etapas, tratar falhas e impedir duplicidades. | Não | Estado da execução e identificador de correlação. |
| **Coletor meteorológico** | Consultar uma API pública, respeitar limites de acesso e armazenar o payload bruto. | Não | Dados brutos e metadados da coleta. |
| **Normalizador e validador** | Converter o payload para o contrato interno, validar unidade, horário, localização e completude. | Não | Evento meteorológico normalizado ou rejeitado. |
| **Detector de eventos** | Classificar chuva intensa, granizo, ventos fortes e eventos combinados. | Não | Lista de eventos e severidade preliminar. |
| **Agente de elegibilidade** | Comparar evento, localização, vigência, produto, preferências e cooldown da apólice. | Sim, usando regras determinísticas | Lista de destinatários elegíveis e motivos. |
| **Agente de priorização** | Definir prioridade, janela de comunicação e canal preferencial. | Não altera a elegibilidade | Prioridade e plano de comunicação. |
| **Agente de mensagens** | Produzir texto claro, personalizado e limitado às informações autorizadas. | Não | Mensagem estruturada e versão renderizada. |
| **Simulador de notificações** | Registrar o envio simulado e apresentar o resultado da demonstração. | Não | Registro de simulação com status. |
| **Auditor e observabilidade** | Validar trilhas, métricas, erros, latência e aderência às regras. | Pode bloquear a saída | Evidências de auditoria e alertas operacionais. |

O modelo de linguagem deve ser utilizado prioritariamente no agente de mensagens. Quando for usado em outros agentes, sua saída deve ser validada por esquema e não pode substituir as regras determinísticas de elegibilidade.

## 7. Regras de coleta e qualidade dos dados

### RN-COL-001 — Fonte meteorológica configurada

O sistema deve consultar pelo menos uma fonte pública de dados meteorológicos previamente configurada. A fonte, o endpoint, a unidade de medida, a periodicidade e o horário da última coleta devem estar documentados.

**Resultado quando satisfeita:** o payload é encaminhado para normalização.

**Resultado quando não satisfeita:** a execução é encerrada com status `DATA_SOURCE_UNAVAILABLE`; nenhuma comunicação crítica deve ser gerada com base em dados antigos sem que isso esteja explicitamente configurado.

### RN-COL-002 — Registro do payload bruto

Cada consulta deve registrar o identificador da execução, o horário da requisição, o status HTTP, a fonte, o período consultado e o hash ou identificador do payload. Segredos, chaves de API e dados pessoais não podem ser registrados.

### RN-COL-003 — Validade temporal

O sistema só deve considerar um evento se houver um horário de coleta e uma janela de validade coerente. Eventos com `valid_until` anterior a `valid_from` devem ser rejeitados.

Quando a fonte apresentar apenas uma previsão sem janela explícita, o normalizador deve aplicar a janela padrão definida na configuração e marcar o evento como `time_window_inferred: true`.

### RN-COL-004 — Unidade padronizada

A solução deve converter precipitação para milímetros, velocidade do vento para quilômetros por hora e coordenadas para latitude e longitude em graus decimais. Valores sem unidade conhecida devem ser rejeitados ou encaminhados para revisão técnica.

### RN-COL-005 — Localização válida

Um evento só pode ser associado a uma apólice se sua área de impacto possuir coordenadas ou geometria utilizável. Se não houver localização, o sistema pode manter o evento para observabilidade, mas não deve selecionar segurados.

### RN-COL-006 — Falha e retentativa

O coletor deve realizar até três tentativas com espera progressiva para erros transitórios. Após o limite, deve produzir um evento de falha e não reutilizar silenciosamente um payload antigo como se fosse atual.

### RN-COL-007 — Confiabilidade mínima

O normalizador deve classificar a confiabilidade do evento como `high`, `medium` ou `low`, considerando completude, consistência, atualidade e status da fonte. Eventos classificados como `low` não devem gerar mensagens de severidade crítica.

## 8. Regras de detecção de eventos

Os limiares abaixo são **valores iniciais de demonstração do MVP**. Devem ser configuráveis e validados pelo responsável de produto, pelo especialista de seguros e, quando aplicável, por meteorologista. Eles não representam critérios universais de cobertura ou de regulação de sinistros.

### RN-EVT-001 — Chuva intensa

Classificar o evento como `heavy_rain` quando pelo menos uma das condições for verdadeira:

- a fonte informar explicitamente chuva intensa ou alerta equivalente;
- a precipitação prevista ou observada for igual ou superior a **20 mm em uma hora**;
- a precipitação acumulada prevista ou observada for igual ou superior a **50 mm em 24 horas**.

A severidade deve ser `attention` por padrão e pode ser elevada para `critical` quando a fonte oficial classificar o alerta como alto ou quando o volume de 24 horas atingir o limiar crítico configurado.

### RN-EVT-002 — Granizo

Classificar o evento como `hail` quando a fonte informar granizo, tempestade com granizo ou probabilidade de granizo igual ou superior a **50%**.

Na ausência de confirmação explícita, uma indicação genérica de tempestade não deve ser convertida automaticamente em granizo. A inferência deve ser desativada no MVP, salvo se a fonte documentar a relação entre o código meteorológico e o perigo.

### RN-EVT-003 — Ventos fortes

Classificar o evento como `strong_wind` quando a velocidade sustentada for igual ou superior a **50 km/h** ou quando as rajadas forem iguais ou superiores a **70 km/h**.

A severidade deve ser elevada quando a fonte oficial emitir alerta específico de vento ou quando as rajadas ultrapassarem o limiar crítico configurado.

### RN-EVT-004 — Área costeira

Marcar `coastal_exposure: true` somente quando a apólice ou o cadastro territorial indicar que o risco está em região costeira. O sistema não deve inferir exposição costeira apenas pela proximidade de um evento de vento.

### RN-EVT-005 — Evento combinado

Classificar como `compound_event` quando dois ou mais tipos de evento relevantes incidirem sobre a mesma localização e janela temporal, com sobreposição mínima de **uma hora**.

A comunicação de evento combinado deve mencionar somente os perigos que foram confirmados pelos dados normalizados.

### RN-EVT-006 — Deduplicação de eventos

Eventos com o mesmo `source_event_id` devem ser tratados como a mesma ocorrência. Se a fonte não fornecer identificador, o sistema deve calcular uma chave com fonte, tipo, localização aproximada, início e fim da janela.

Uma atualização do mesmo evento só deve gerar nova decisão quando houver alteração material na severidade, na janela ou no tipo de perigo.

## 9. Regras de elegibilidade dos segurados

### RN-SEG-001 — Apólice ativa

Somente apólices com status `active` e vigência válida no horário de avaliação podem receber comunicação preventiva.

Apólices canceladas, suspensas, vencidas, inexistentes ou com dados de vigência inconsistentes devem ser excluídas.

### RN-SEG-002 — Produto compatível

O segurado deve possuir produto compatível com o evento. A matriz mínima do MVP é:

| Evento | Residencial | Automóvel | Observação |
|---|---:|---:|---|
| Chuva intensa | Sim | Não por padrão | Para automóvel, só utilizar se houver regra específica de alagamento ou inundação aprovada. |
| Granizo | Não por padrão | Sim | A mensagem deve evitar afirmar que o dano está coberto. |
| Vento forte | Sim | Sim | Para automóvel, orientar estacionamento seguro; para residencial, proteger objetos e aberturas. |
| Evento combinado | Aplicar eventos componentes | Aplicar eventos componentes | A elegibilidade é a união dos produtos compatíveis. |

### RN-SEG-003 — Localização dentro da área de impacto

O risco segurado deve estar dentro da área de impacto do evento. Para o MVP, quando a fonte fornecer somente um ponto central, pode ser utilizado um raio configurável de **20 km**, desde que isso seja identificado no log como aproximação.

Se a apólice possuir endereço residencial e o produto for residencial, utilizar o endereço do risco. Para automóvel, utilizar o local de guarda cadastrado quando disponível. Se o local de guarda não estiver disponível, utilizar a localização configurada para o risco somente se a regra de produto permitir.

### RN-SEG-004 — Dados de localização insuficientes

Apólices sem coordenadas válidas, endereço não geocodificado ou área de risco ambígua não devem receber uma mensagem específica de localização. O sistema deve registrar `INELIGIBLE_MISSING_LOCATION`.

### RN-SEG-005 — Consentimento e preferência de canal

O simulador só deve considerar canais habilitados para o segurado e não deve simular comunicação quando houver indicação de bloqueio ou opt-out. Se não houver canal habilitado, registrar `INELIGIBLE_NO_AUTHORIZED_CHANNEL`.

O opt-out deve prevalecer sobre a severidade do evento. Em situação crítica, o sistema deve registrar o bloqueio para auditoria, mas não deve ignorá-lo no protótipo.

### RN-SEG-006 — Segurado duplicado

Quando a mesma pessoa possuir várias apólices elegíveis para o mesmo evento, o sistema deve consolidar a comunicação por segurado e manter a referência de todas as apólices elegíveis. A mensagem não deve expor identificadores internos de apólice.

Se os produtos exigirem recomendações materialmente diferentes, o sistema pode gerar mensagens separadas por produto, respeitando o cooldown de cada comunicação.

### RN-SEG-007 — Janela de antecedência

A comunicação deve ser priorizada quando o início previsto do evento estiver entre **15 minutos e 48 horas** a partir do momento da avaliação. Eventos já encerrados não devem gerar comunicação preventiva.

Eventos que começarão em menos de 15 minutos podem ser classificados como urgentes, mas a mensagem deve ser curta e priorizar a ação imediata. Eventos com início superior a 48 horas podem ser armazenados para reavaliação, sem notificação no MVP.

### RN-SEG-008 — Cooldown por evento

Não enviar mais de uma comunicação ao mesmo segurado para o mesmo tipo de evento, produto e janela em um período de **24 horas**, salvo se a severidade aumentar ou a fonte corrigir materialmente a área de impacto.

### RN-SEG-009 — Limite de frequência

O MVP deve limitar o segurado a, no máximo, **três comunicações preventivas em sete dias**, independentemente do canal. Ao atingir o limite, a comunicação só deve ser simulada quando a severidade for `critical` e o evento for diferente do último comunicado.

### RN-SEG-010 — Ordem de precedência

A ordem de avaliação deve ser:

1. validar a fonte e o evento;
2. validar a vigência da apólice;
3. validar a compatibilidade do produto;
4. validar a localização;
5. validar consentimento e canal;
6. aplicar cooldown e limite de frequência;
7. calcular severidade e prioridade;
8. gerar a mensagem;
9. simular o envio;
10. registrar a auditoria.

Uma regra de exclusão interrompe a seleção para aquele segurado. A mensagem não deve ser gerada quando a elegibilidade for negativa.

## 10. Regras de severidade e priorização

### RN-PRI-001 — Níveis de severidade

A severidade final deve ser o maior nível entre a classificação da fonte, os limiares internos e a combinação de eventos, respeitando a confiabilidade dos dados.

| Nível | Critério mínimo | Tratamento |
|---|---|---|
| **Informativa** | Condição meteorológica relevante, mas abaixo do limiar de dano definido. | Pode ser exibida no painel; comunicação somente se o produto permitir. |
| **Atenção** | Evento que supera o limiar de atenção ou alerta equivalente da fonte. | Gerar comunicação preventiva para segurados elegíveis. |
| **Crítica** | Alerta alto da fonte, limiar crítico atingido ou evento combinado de alto impacto. | Priorizar comunicação, encurtar a mensagem e marcar para monitoramento. |

### RN-PRI-002 — Prioridade operacional

A prioridade de processamento deve ser calculada por:

1. severidade crítica;
2. início do evento mais próximo;
3. maior confiabilidade da fonte;
4. maior quantidade de segurados potencialmente impactados.

A prioridade não altera os critérios de elegibilidade. Ela apenas define a ordem de geração e simulação das comunicações.

### RN-PRI-003 — Atualização de severidade

Uma nova avaliação deve gerar atualização quando a severidade aumentar, quando o evento se aproximar da janela de início ou quando a área de impacto passar a conter novos riscos segurados.

Uma redução de severidade não deve gerar nova mensagem por padrão, para evitar ruído. A redução deve ser registrada no histórico do evento.

## 11. Regras de geração de mensagens

### RN-MSG-001 — Estrutura obrigatória

Toda mensagem deve conter, quando disponíveis e autorizados:

- saudação neutra ou identificação permitida do segurado;
- tipo de evento;
- região ou referência genérica do risco;
- janela temporal do evento;
- severidade ou indicação de atenção;
- de uma a três recomendações práticas;
- orientação para acompanhar canais oficiais;
- aviso de que a comunicação é preventiva e não altera as condições da apólice;
- canal de contato ou instrução para assistência, somente se estiver configurado.

### RN-MSG-002 — Personalização autorizada

A personalização pode utilizar produto, tipo de bem, cidade, região, janela do evento, canal e recomendações específicas do cenário. Não utilizar nome completo, número de documento, valor segurado, franquia ou detalhes contratuais que não estejam autorizados para a comunicação.

### RN-MSG-003 — Recomendações residenciais para chuva intensa

Para seguro residencial, priorizar recomendações como:

- verificar calhas, ralos, telhas, janelas e portas;
- retirar objetos soltos de áreas externas;
- proteger equipamentos e documentos em locais elevados;
- evitar contato com instalações elétricas em áreas molhadas;
- não realizar reparos em telhados durante chuva ou vento.

A mensagem não deve instruir o segurado a executar atividade que possa aumentar o risco pessoal.

### RN-MSG-004 — Recomendações automotivas para granizo

Para seguro automóvel, priorizar recomendações como:

- estacionar o veículo em local coberto e seguro, se possível;
- evitar deslocamentos durante o alerta;
- não estacionar sob árvores, estruturas instáveis ou placas soltas;
- acompanhar a evolução do alerta antes de iniciar a viagem.

A mensagem não deve prometer reparo, reembolso, cobertura automática ou dispensa de procedimentos contratuais.

### RN-MSG-005 — Recomendações para ventos fortes

Para residência, recomendar recolher objetos soltos, fechar aberturas e evitar áreas próximas a árvores e estruturas instáveis. Para automóvel, recomendar estacionamento protegido e evitar vias expostas quando isso for seguro e viável.

### RN-MSG-006 — Limite de extensão

A versão SMS deve possuir até **480 caracteres**, salvo configuração diferente do canal. A versão de e-mail ou painel pode ser mais extensa, mas deve permanecer objetiva e apresentar as ações por ordem de prioridade.

### RN-MSG-007 — Linguagem

A mensagem deve ser escrita em português claro, direto, respeitoso e sem alarmismo. Deve usar verbos de recomendação, como “verifique”, “evite” e “considere”, em vez de afirmar que o dano ocorrerá.

### RN-MSG-008 — Proibições de conteúdo

É proibido gerar mensagens que:

- afirmem que haverá sinistro;
- confirmem ou neguem cobertura;
- informem valor de indenização, franquia ou prazo de pagamento;
- solicitem senha, token, documento completo ou dados bancários;
- incluam links não cadastrados pela solução;
- atribuam certeza a uma previsão;
- recomendem atividade perigosa;
- exponham dados de outros segurados;
- apresentem conteúdo discriminatório ou irrelevante.

### RN-MSG-009 — Validação pós-geração

A mensagem gerada pelo modelo deve ser validada por regras antes da simulação. A validação deve verificar idioma, tamanho, presença do tipo de evento, coerência com a severidade, ausência de termos proibidos e ausência de dados não autorizados.

Se a validação falhar, o sistema deve usar um template determinístico de fallback e registrar `MESSAGE_GENERATION_FALLBACK`.

### RN-MSG-010 — Prompt e saída estruturada

O agente de mensagens deve receber somente os fatos aprovados pela etapa de decisão. A saída deve seguir esquema estruturado, por exemplo:

```json
{
  "subject": "Alerta preventivo de chuva intensa",
  "short_message": "...",
  "long_message": "...",
  "recommended_actions": ["...", "..."],
  "disclaimer": "Esta é uma comunicação preventiva e não altera as condições da apólice.",
  "used_facts": ["heavy_rain", "attention", "window_start", "city"],
  "validation_status": "pending"
}
```

O agente não deve receber a instrução de decidir elegibilidade nem de completar lacunas com suposições.

## 12. Regras de simulação de envio

### RN-SIM-001 — Simulação sem envio real

O simulador deve representar o envio sem chamar provedores reais de SMS, e-mail ou push. O resultado mínimo deve informar segurado mascarado, produto, evento, severidade, canal simulado, horário e status.

### RN-SIM-002 — Estados do simulador

| Estado | Uso |
|---|---|
| `READY` | Comunicação validada e pronta para simulação. |
| `SIMULATED_SENT` | Comunicação registrada como simulada com sucesso. |
| `BLOCKED_BY_RULE` | Comunicação impedida por regra de negócio. |
| `FALLBACK_TEMPLATE` | Modelo de linguagem falhou e template determinístico foi utilizado. |
| `SIMULATION_ERROR` | Falha técnica ao registrar o resultado. |
|
### RN-SIM-003 — Idempotência do envio

O identificador de idempotência deve ser formado por segurado, apólice consolidada, evento, janela, canal e versão das regras. Uma tentativa repetida deve retornar o resultado anterior e não criar um segundo registro.

### RN-SIM-004 — Demonstração auditável

A interface ou relatório de demonstração deve permitir visualizar a sequência completa: dados coletados, evento detectado, regra acionada, segurado selecionado, mensagem gerada e resultado da simulação.

## 13. Auditoria, segurança e governança

### RN-GOV-001 — Trilha de decisão

Para cada evento avaliado, armazenar:

| Campo | Conteúdo mínimo |
|---|---|
| `correlation_id` | Identificador único da execução. |
| `source` | Fonte meteorológica utilizada. |
| `collected_at` | Horário de coleta. |
| `event_id` | Identificador normalizado do evento. |
| `ruleset_version` | Versão das regras aplicadas. |
| `policy_decision` | Elegível ou não elegível. |
| `decision_reasons` | Regras que justificaram a decisão. |
| `message_version` | Versão do template ou do modelo. |
| `simulation_status` | Resultado da simulação. |
| `created_at` | Horário do registro. |

### RN-GOV-002 — Segredos

Chaves de API e credenciais devem ser lidas de variáveis de ambiente ou de um gerenciador de segredos. Elas não podem ser incluídas no código, no README, em exemplos, nos prompts ou nos logs.

### RN-GOV-003 — Controle de versões

Toda alteração de limiar, produto, canal, cooldown, prompt ou template deve gerar nova versão de configuração. O histórico deve permitir reproduzir a decisão original.

### RN-GOV-004 — Supervisão humana

A arquitetura deve permitir revisão humana dos limiares, dos templates, dos alertas de severidade crítica e das mensagens rejeitadas pela validação. A revisão é especialmente necessária antes de transformar a simulação em integração real.

### RN-GOV-005 — Proteção de dados pessoais

O protótipo deve adotar minimização, finalidade, controle de acesso, mascaramento e retenção limitada. O desenho deve ser compatível com os princípios de proteção de dados aplicáveis ao contexto brasileiro, incluindo a Lei Geral de Proteção de Dados Pessoais [3].

### RN-GOV-006 — Fonte e limitações

A mensagem ou a tela de demonstração deve identificar a fonte meteorológica e indicar que previsões podem sofrer atualização. O sistema não deve apresentar o alerta como garantia de ocorrência.

## 14. Fluxo de decisão de referência

```text
INÍCIO
  |
  v
Consultar fonte meteorológica
  |
  +-- falha após retentativas --> Registrar indisponibilidade --> FIM
  |
  v
Normalizar e validar dados
  |
  +-- inválido ------------------> Registrar rejeição ---------> FIM
  |
  v
Detectar evento e severidade
  |
  +-- nenhum evento relevante ---> Registrar evento informativo -> FIM
  |
  v
Buscar apólices ativas
  |
  v
Para cada apólice:
  validar produto
  validar localização
  validar canal e opt-out
  validar cooldown e limite de frequência
  |
  +-- inelegível ----------------> Registrar motivo ------------> próxima apólice
  |
  v
Calcular prioridade
  |
  v
Gerar mensagem com fatos aprovados
  |
  +-- falha de validação --------> Aplicar template de fallback
  |
  v
Simular envio
  |
  v
Registrar auditoria e métricas
  |
  v
FIM
```

## 15. Matriz de decisão do MVP

| Evento | Produto | Localização válida | Apólice ativa | Canal autorizado | Cooldown livre | Decisão |
|---|---|---:|---:|---:|---:|---|
| Chuva intensa | Residencial | Sim | Sim | Sim | Sim | Gerar mensagem de atenção. |
| Chuva intensa | Automóvel | Sim | Sim | Sim | Sim | Não comunicar, salvo regra específica de alagamento aprovada. |
| Granizo | Automóvel | Sim | Sim | Sim | Sim | Gerar mensagem de prevenção para o veículo. |
| Vento forte | Residencial | Sim | Sim | Sim | Sim | Gerar mensagem sobre objetos, aberturas e segurança. |
| Vento forte | Automóvel | Sim | Sim | Sim | Sim | Gerar mensagem sobre estacionamento e deslocamento. |
| Qualquer evento | Produto compatível | Não | Sim | Sim | Sim | Não comunicar por falta de localização. |
| Qualquer evento | Produto compatível | Sim | Não | Sim | Sim | Não comunicar por apólice inativa. |
| Qualquer evento | Produto compatível | Sim | Sim | Não | Sim | Não comunicar por ausência de canal autorizado. |
| Qualquer evento | Produto compatível | Sim | Sim | Sim | Não | Não comunicar por cooldown, salvo aumento de severidade. |
| Qualquer evento | Produto compatível | Sim | Sim | Sim | Sim | Gerar comunicação somente se a antecedência e a severidade forem elegíveis. |

## 16. Exemplos de decisões e mensagens

### 16.1. Chuva intensa para seguro residencial

**Entrada:** chuva acumulada de 63 mm em 24 horas, início previsto em três horas, risco residencial dentro da área de impacto, apólice ativa e canal de e-mail autorizado.

**Decisão:** elegível; severidade `attention`; prioridade alta; regra acionada `RN-EVT-001` e regras de elegibilidade residencial.

**Mensagem simulada:**

> **Alerta preventivo de chuva intensa**
>
> Há previsão de chuva intensa para a região do seu imóvel nas próximas horas. Se for seguro fazê-lo, verifique calhas, ralos, portas e janelas e retire objetos soltos de áreas externas. Evite contato com instalações elétricas em locais molhados. Esta é uma comunicação preventiva e não altera as condições da sua apólice. Acompanhe as atualizações nos canais oficiais.

### 16.2. Granizo para seguro automóvel

**Entrada:** fonte indica granizo, início previsto em 40 minutos, veículo com local de guarda dentro da área de impacto, apólice ativa e push não autorizado, mas SMS autorizado.

**Decisão:** elegível; severidade `critical`; canal `SMS`; regra acionada `RN-EVT-002`.

**Mensagem simulada:**

> **Alerta de granizo:** há possibilidade de granizo na região do local cadastrado do seu veículo nos próximos minutos. Se possível, estacione em local coberto e evite árvores ou estruturas instáveis. Não se desloque durante o alerta, salvo necessidade e em condições seguras. Comunicação preventiva; consulte os canais oficiais para orientações contratuais.

### 16.3. Evento duplicado dentro do cooldown

**Entrada:** a mesma fonte atualiza o volume de chuva sem alterar a severidade, a janela ou a área de impacto, seis horas após a comunicação anterior.

**Decisão:** não gerar nova mensagem; registrar `BLOCKED_BY_RULE` por `RN-SEG-008`.

### 16.4. Falha de dados de localização

**Entrada:** alerta de vento forte válido, mas a apólice não possui coordenadas nem endereço geocodificado.

**Decisão:** não comunicar; registrar `INELIGIBLE_MISSING_LOCATION`. O evento permanece disponível para diagnóstico técnico.

## 17. Critérios de aceite do MVP

| ID | Critério verificável |
|---|---|
| CA-001 | O sistema consulta uma API pública meteorológica e registra a coleta. |
| CA-002 | O sistema normaliza os dados para um contrato interno com unidades e horários consistentes. |
| CA-003 | O sistema identifica pelo menos chuva intensa, granizo e vento forte. |
| CA-004 | O sistema aplica a matriz de produto, localização, vigência, canal e cooldown. |
| CA-005 | O sistema apresenta o motivo de cada decisão positiva ou negativa. |
| CA-006 | O sistema gera mensagens diferentes para residência, automóvel, chuva, granizo e vento. |
| CA-007 | O sistema usa modelo de linguagem com saída estruturada ou template de fallback. |
| CA-008 | O sistema valida a mensagem e bloqueia promessas de cobertura, sinistro ou indenização. |
| CA-009 | O sistema simula o envio sem transmitir mensagens reais. |
| CA-010 | O fluxo completo pode ser demonstrado com dados reais ou fixtures reproduzíveis. |
| CA-011 | O sistema evita duplicidade com chave de idempotência e cooldown. |
| CA-012 | O sistema não expõe chaves de API nos arquivos versionados ou nos logs. |
| CA-013 | O README descreve instalação, configuração, execução, exemplos e licença MIT. |
| CA-014 | O relatório técnico apresenta arquitetura, agentes, tecnologias, fluxo, regras e mensagens. |

## 18. Cenários mínimos de teste

A equipe deve demonstrar pelo menos os seguintes testes:

1. Chuva intensa atingindo uma apólice residencial ativa: deve gerar comunicação.
2. Granizo atingindo uma apólice automotiva ativa: deve gerar comunicação.
3. Vento forte atingindo apólices residencial e automotiva: deve gerar mensagens específicas por produto.
4. Evento atingindo apólice vencida: não deve gerar comunicação.
5. Evento fora da área de impacto: não deve gerar comunicação.
6. Segurado sem canal autorizado: não deve gerar comunicação.
7. Evento repetido durante o cooldown: não deve gerar duplicidade.
8. Aumento de severidade durante o cooldown: deve permitir nova comunicação prioritária.
9. Falha do modelo de linguagem: deve utilizar template de fallback.
10. Payload com unidade desconhecida ou janela inválida: deve ser rejeitado.
11. Evento combinado de chuva e vento: deve gerar uma comunicação consolidada com as recomendações pertinentes.
12. API indisponível após retentativas: deve registrar falha sem produzir alerta falso.

## 19. Métricas de acompanhamento

A demonstração deve acompanhar métricas que permitam avaliar a qualidade do fluxo, e não apenas a quantidade de mensagens:

| Métrica | Finalidade |
|---|---|
| Taxa de coleta bem-sucedida | Verificar confiabilidade da fonte externa. |
| Taxa de eventos rejeitados | Identificar problemas de normalização e qualidade. |
| Quantidade de apólices avaliadas | Medir cobertura do processamento. |
| Taxa de elegibilidade | Entender o impacto da matriz de negócio. |
| Taxa de bloqueio por regra | Avaliar opt-out, cooldown, localização e vigência. |
| Taxa de fallback do modelo | Medir estabilidade da geração automática. |
| Taxa de mensagens rejeitadas na validação | Detectar alucinação ou desvio de política. |
| Tempo entre coleta e simulação | Medir a latência da comunicação preventiva. |
| Duplicidades evitadas | Demonstrar idempotência. |
| Distribuição por evento e produto | Verificar se as regras estão produzindo cenários variados. |

## 20. Configuração recomendada

Os seguintes parâmetros devem ficar fora do código de negócio, em arquivo de configuração versionado sem segredos:

```yaml
ruleset_version: "1.0.0"
source:
  provider: "configured_public_weather_api"
  request_timeout_seconds: 10
  max_retries: 3

thresholds:
  heavy_rain_mm_1h: 20
  heavy_rain_mm_24h: 50
  strong_wind_kmh: 50
  wind_gust_kmh: 70
  hail_probability_percent: 50
  impact_radius_km: 20

communication:
  min_lead_time_minutes: 15
  max_lead_time_hours: 48
  cooldown_hours: 24
  max_messages_per_7_days: 3
  sms_max_characters: 480

features:
  infer_hail_from_generic_storm: false
  allow_real_delivery: false
  use_llm_for_eligibility: false
```

Os limiares devem ser ajustados por configuração e não por alteração direta no prompt. O modo `allow_real_delivery` deve permanecer desativado no desafio.

## 21. Responsabilidades da squad e definição de pronto

A squad considera uma entrega pronta quando o fluxo pode ser executado de ponta a ponta com uma fonte meteorológica configurada, dados de segurados fictícios, regras versionadas, mensagens validadas e simulação reproduzível.

A documentação deve explicar as premissas dos limiares, as limitações da fonte, os motivos de exclusão, o uso do modelo de linguagem e a forma de reproduzir cada cenário. O código deve ser modular, possuir instruções de execução e não conter credenciais.

Para a apresentação, recomenda-se demonstrar um caso positivo, um caso bloqueado por regra, uma atualização de severidade e uma falha tratada com fallback. Isso evidencia que a solução não apenas gera texto, mas executa um fluxo de decisão auditável.

## 22. Referências

[1]: https://portal.inmet.gov.br/ "Instituto Nacional de Meteorologia — Portal oficial"

[2]: https://openweathermap.org/api "OpenWeather — documentação de APIs meteorológicas"

[3]: https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709.htm "Lei nº 13.709/2018 — Lei Geral de Proteção de Dados Pessoais"

[4]: https://www.noaa.gov/ "National Oceanic and Atmospheric Administration — Portal oficial"

> **Nota de implementação:** os limiares, a matriz de produtos e os textos deste documento são uma base de prototipação para o desafio. Antes de qualquer uso operacional, devem ser revisados por responsáveis de produto, seguros, segurança da informação, privacidade e conformidade.

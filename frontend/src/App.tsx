import { useCallback, useEffect, useState } from "react";
import { api } from "./api";
import type {
  EventType,
  EvidenceType,
  Insured,
  Measurements,
  NotifyRequest,
  ProactiveNotification,
  Rule,
  Severity,
  WeatherSnapshot,
} from "./types";

const CITIES = [
  { name: "Brasília", latitude: -15.7939, longitude: -47.8828 },
  { name: "Curitiba", latitude: -25.4284, longitude: -49.2733 },
  { name: "Belo Horizonte", latitude: -19.9167, longitude: -43.9345 },
  { name: "Porto Alegre", latitude: -30.0346, longitude: -51.2177 },
  { name: "Coordenada personalizada", latitude: NaN, longitude: NaN },
];

const EVENT_LABELS: Record<string, string> = {
  HEAVY_RAIN: "Chuva intensa",
  HAIL: "Granizo",
  STRONG_WIND: "Ventos fortes",
};

function Badge({ kind, children }: { kind: string; children: React.ReactNode }) {
  return <span className={`badge ${kind}`}>{children}</span>;
}

function formatValue(value: number | null | undefined, unit: string) {
  return value === null || value === undefined ? "—" : `${value} ${unit}`;
}

export default function App() {
  const [apiStatus, setApiStatus] = useState<"checking" | "ok" | "err">("checking");
  const [city, setCity] = useState(CITIES[0].name);
  const [latitude, setLatitude] = useState(CITIES[0].latitude);
  const [longitude, setLongitude] = useState(CITIES[0].longitude);
  const [snapshot, setSnapshot] = useState<WeatherSnapshot | null>(null);
  const [loadingWeather, setLoadingWeather] = useState(false);
  const [weatherError, setWeatherError] = useState<string | null>(null);

  const [rules, setRules] = useState<Rule[]>([]);
  const [insureds, setInsureds] = useState<Insured[]>([]);

  const [selectedEventId, setSelectedEventId] = useState<string | null>(null);
  const [manualType, setManualType] = useState<EventType>("HEAVY_RAIN");
  const [manualEvidence, setManualEvidence] = useState<EvidenceType>("ALERT");
  const [manualSeverity, setManualSeverity] = useState<Severity>("HIGH");
  const [notifications, setNotifications] = useState<ProactiveNotification[]>([]);
  const [notifying, setNotifying] = useState(false);
  const [notifyError, setNotifyError] = useState<string | null>(null);

  useEffect(() => {
    fetch("/api/health")
      .then((r) => setApiStatus(r.ok ? "ok" : "err"))
      .catch(() => setApiStatus("err"));
    api.rules().then(setRules).catch(() => setRules([]));
    api.insureds().then(setInsureds).catch(() => setInsureds([]));
  }, []);

  const queryWeather = useCallback(async () => {
    setLoadingWeather(true);
    setWeatherError(null);
    setSnapshot(null);
    setNotifications([]);
    setSelectedEventId(null);
    try {
      const data = await api.weather(latitude, longitude);
      setSnapshot(data);
      if (data.events.length === 1) setSelectedEventId(data.events[0].event_id);
    } catch (err) {
      setWeatherError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoadingWeather(false);
    }
  }, [latitude, longitude]);

  const onCityChange = (name: string) => {
    setCity(name);
    const preset = CITIES.find((c) => c.name === name);
    if (preset && Number.isFinite(preset.latitude)) {
      setLatitude(preset.latitude);
      setLongitude(preset.longitude);
    }
  };

  const runNotify = useCallback(
    async (payload: NotifyRequest) => {
      setNotifying(true);
      setNotifyError(null);
      setNotifications([]);
      try {
        setNotifications(await api.notify(payload));
      } catch (err) {
        setNotifyError(err instanceof Error ? err.message : String(err));
      } finally {
        setNotifying(false);
      }
    },
    [],
  );

  const notifySelectedEvent = () => {
    const event = snapshot?.events.find((e) => e.event_id === selectedEventId);
    if (!event) return;
    runNotify({
      event_type: event.event_type,
      evidence_type: event.evidence_type,
      severity: event.severity,
      timestamp: event.timestamp,
      location: event.location,
      measurements: event.measurements,
      source: event.source,
      description: event.description ?? undefined,
    });
  };

  const notifyManualEvent = () => {
    if (!Number.isFinite(latitude) || !Number.isFinite(longitude)) return;
    const measurements: Measurements =
      manualEvidence === "OBSERVATION" ? snapshot?.measurements ?? {} : {};
    runNotify({
      event_type: manualType,
      evidence_type: manualEvidence,
      severity: manualSeverity,
      timestamp: new Date().toISOString(),
      location: { latitude, longitude, municipality: snapshot?.location.municipality },
      measurements,
      source: "manual-demo",
    });
  };

  const selectedCity = CITIES.find((c) => c.name === city);
  const customCity = selectedCity && !Number.isFinite(selectedCity.latitude);
  const hasEvents = (snapshot?.events.length ?? 0) > 0;

  return (
    <div className="container">
      <header className="app-header">
        <div className="flow-badge">Desafio 5 — Fluxo completo de comunicação proativa</div>
        <h1>Agente do Tempo + Comunicação Proativa com o Segurado</h1>
        <p>
          Consulta ao INMET → detecção de eventos → regras de negócio → mensagem com LLM → envio
          simulado.{" "}
          <span className={`status-pill ${apiStatus === "ok" ? "ok" : apiStatus === "err" ? "err" : ""}`}>
            API: {apiStatus === "ok" ? "conectada" : apiStatus === "err" ? "offline" : "verificando…"}
          </span>
        </p>
      </header>

      <section className="panel">
        <h2>1 · Consulta meteorológica (INMET)</h2>
        <p className="hint">
          Consulta avisos oficiais e observações SYNOP do INMET para uma localização.
        </p>
        <div className="row">
          <div className="field">
            <label>Cidade</label>
            <select value={city} onChange={(e) => onCityChange(e.target.value)}>
              {CITIES.map((c) => (
                <option key={c.name} value={c.name}>
                  {c.name}
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label>Latitude</label>
            <input
              type="number"
              step="0.0001"
              value={Number.isFinite(latitude) ? latitude : ""}
              onChange={(e) => setLatitude(Number(e.target.value))}
              disabled={!customCity}
            />
          </div>
          <div className="field">
            <label>Longitude</label>
            <input
              type="number"
              step="0.0001"
              value={Number.isFinite(longitude) ? longitude : ""}
              onChange={(e) => setLongitude(Number(e.target.value))}
              disabled={!customCity}
            />
          </div>
          <button className="primary" onClick={queryWeather} disabled={loadingWeather}>
            {loadingWeather ? "Consultando…" : "Consultar tempo"}
          </button>
        </div>
        {weatherError && <div className="error-box">{weatherError}</div>}

        {snapshot && (
          <>
            <div className="measurement-grid">
              <div className="measurement">
                <div className="value">{formatValue(snapshot.measurements.temperature_celsius, "°C")}</div>
                <div className="label">Temperatura</div>
              </div>
              <div className="measurement">
                <div className="value">{formatValue(snapshot.measurements.precipitation_mm, "mm")}</div>
                <div className="label">Precipitação (1h)</div>
              </div>
              <div className="measurement">
                <div className="value">{formatValue(snapshot.measurements.wind_speed_kmh, "km/h")}</div>
                <div className="label">Vento</div>
              </div>
              <div className="measurement">
                <div className="value">{formatValue(snapshot.measurements.wind_gust_kmh, "km/h")}</div>
                <div className="label">Rajada</div>
              </div>
            </div>
            <div className="event-list">
              {snapshot.events.length === 0 && (
                <div className="empty">Nenhum evento climático relevante detectado nesta localização.</div>
              )}
              {snapshot.events.map((event) => (
                <div key={event.event_id} className="event-card">
                  <div>
                    <Badge kind={event.event_type}>{EVENT_LABELS[event.event_type]}</Badge>
                    <Badge kind={event.evidence_type}>{event.evidence_type}</Badge>
                    <Badge kind={event.severity}>{event.severity}</Badge>
                  </div>
                  <button
                    className={event.event_id === selectedEventId ? "ghost selected" : "ghost"}
                    onClick={() => setSelectedEventId(event.event_id)}
                  >
                    {event.event_id === selectedEventId ? "Selecionado" : "Selecionar"}
                  </button>
                </div>
              ))}
            </div>
            {hasEvents && (
              <div className="row" style={{ marginTop: 14 }}>
                <button className="primary" onClick={notifySelectedEvent} disabled={!selectedEventId || notifying}>
                  {notifying ? "Processando…" : "Avaliar e notificar segurados expostos"}
                </button>
              </div>
            )}
          </>
        )}
      </section>

      <section className="panel">
        <h2>2 · Evento manual (demonstração)</h2>
        <p className="hint">
          Sem eventos ao vivo? Simule um evento para demonstrar as regras e a geração de mensagens.
        </p>
        <div className="row">
          <div className="field">
            <label>Tipo de evento</label>
            <select value={manualType} onChange={(e) => setManualType(e.target.value as EventType)}>
              <option value="HEAVY_RAIN">Chuva intensa</option>
              <option value="HAIL">Granizo</option>
              <option value="STRONG_WIND">Ventos fortes</option>
            </select>
          </div>
          <div className="field">
            <label>Evidência</label>
            <select value={manualEvidence} onChange={(e) => setManualEvidence(e.target.value as EvidenceType)}>
              <option value="ALERT">ALERT (aviso oficial)</option>
              <option value="OBSERVATION">OBSERVATION (estação)</option>
            </select>
          </div>
          <div className="field">
            <label>Severidade</label>
            <select value={manualSeverity} onChange={(e) => setManualSeverity(e.target.value as Severity)}>
              <option value="LOW">LOW</option>
              <option value="MEDIUM">MEDIUM</option>
              <option value="HIGH">HIGH</option>
              <option value="EXTREME">EXTREME</option>
            </select>
          </div>
          <button
            className="primary"
            onClick={notifyManualEvent}
            disabled={notifying || !Number.isFinite(latitude)}
          >
            {notifying ? "Processando…" : "Avaliar e notificar"}
          </button>
        </div>
        {notifyError && <div className="error-box">{notifyError}</div>}

        {notifications.length > 0 && (
          <div className="event-list">
            {notifications.map((n) => (
              <div key={n.insured_id} className="notification-card">
                <div className="head">
                  <span className="name">{n.insured_name}</span>
                  <span>
                    <Badge kind={n.status}>{n.status === "SIMULATED_SENT" ? "Enviado (simulado)" : "Não enviado"}</Badge>
                    {n.message && <Badge kind={n.message.generated_by}>{n.message.generated_by === "grok" ? "Grok (LLM)" : "Template"}</Badge>}
                    {n.decision.eligible && <Badge kind={n.decision.priority}>{n.decision.priority}</Badge>}
                  </span>
                </div>
                <div className="reason">
                  {n.decision.reason}
                  {n.decision.matched_rules.length > 0 && ` Regras: ${n.decision.matched_rules.join(", ")}.`}
                </div>
                {n.message && <div className="message">{n.message.text}</div>}
              </div>
            ))}
          </div>
        )}
      </section>

      <div className="grid-2">
        <section className="panel">
          <h2>Regras de negócio (Rules Engine)</h2>
          <p className="hint">Matriz declarativa de compatibilidade evento × apólice.</p>
          <table className="data">
            <thead>
              <tr>
                <th>Evento</th>
                <th>Evidência</th>
                <th>Apólice</th>
                <th>Prioridade</th>
              </tr>
            </thead>
            <tbody>
              {rules.map((rule) => (
                <tr key={rule.rule_id}>
                  <td>{EVENT_LABELS[rule.event_type]}</td>
                  <td>{rule.evidence_type}</td>
                  <td>{rule.policy_type}</td>
                  <td>
                    <Badge kind={rule.priority}>{rule.priority}</Badge>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>

        <section className="panel">
          <h2>Segurados (dataset fictício)</h2>
          <p className="hint">Raio de exposição de 25 km a partir do evento.</p>
          <table className="data">
            <thead>
              <tr>
                <th>Nome</th>
                <th>Cidade</th>
                <th>Apólices</th>
              </tr>
            </thead>
            <tbody>
              {insureds.map((insured) => (
                <tr key={insured.insured_id}>
                  <td>{insured.name}</td>
                  <td>{insured.location.municipality ?? "—"}</td>
                  <td>
                    {insured.policies
                      .map((p) => `${p.policy_type} (${p.status === "ACTIVE" ? "ativa" : "inativa"})`)
                      .join(", ")}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      </div>

      <footer className="app-footer">
        Protótipo acadêmico — I2A2 InsurMinds · Dados: INMET (avisos ativos + WIS2 SYNOP) · Licença MIT
      </footer>
    </div>
  );
}

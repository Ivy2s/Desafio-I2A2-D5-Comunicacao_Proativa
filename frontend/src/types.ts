export type EventType = "HEAVY_RAIN" | "HAIL" | "STRONG_WIND";
export type EvidenceType = "ALERT" | "OBSERVATION";
export type Severity = "LOW" | "MEDIUM" | "HIGH" | "EXTREME";
export type Priority = "LOW" | "MEDIUM" | "HIGH";

export interface Location {
  latitude: number;
  longitude: number;
  municipality?: string | null;
}

export interface Measurements {
  temperature_celsius?: number | null;
  precipitation_mm?: number | null;
  precipitation_rate_mm_per_hour?: number | null;
  wind_speed_kmh?: number | null;
  wind_gust_kmh?: number | null;
}

export interface WeatherEvent {
  event_id: string;
  event_type: EventType;
  evidence_type: EvidenceType;
  severity: Severity;
  timestamp: string;
  location: Location;
  measurements: Measurements;
  source: string;
  source_reference?: string | null;
  description?: string | null;
}

export interface WeatherSnapshot {
  location: Location;
  observed_at: string;
  measurements: Measurements;
  events: WeatherEvent[];
  source: string;
}

export interface NotificationDecision {
  insured_id: string;
  eligible: boolean;
  reason: string;
  priority: Priority;
  matched_rules: string[];
}

export interface GeneratedMessage {
  text: string;
  generated_by: string;
}

export interface ProactiveNotification {
  insured_id: string;
  insured_name: string;
  municipality?: string | null;
  event: WeatherEvent;
  decision: NotificationDecision;
  message: GeneratedMessage | null;
  status: string;
  sent_at?: string | null;
}

export interface Rule {
  rule_id: string;
  event_type: EventType;
  evidence_type: EvidenceType;
  policy_type: "HOME" | "AUTO";
  priority: Priority;
}

export interface Policy {
  policy_id: string;
  policy_type: "HOME" | "AUTO";
  status: "ACTIVE" | "INACTIVE";
  active: boolean;
}

export interface Insured {
  insured_id: string;
  name: string;
  location: Location;
  policies: Policy[];
}

export interface NotifyRequest {
  event_type: EventType;
  evidence_type: EvidenceType;
  severity: Severity;
  timestamp?: string;
  location: Location;
  measurements?: Measurements;
  source?: string;
  description?: string;
}

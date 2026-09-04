import json
import math
import re
from datetime import datetime, timezone
from typing import Any

import httpx

from src.config.settings import Settings, get_settings
from src.domain.weather.models import (
    Location,
    Measurements,
    WeatherAlert,
    WeatherInput,
)
from src.providers.weather.base import (
    WeatherProviderHTTPError,
    WeatherProviderInvalidResponseError,
    WeatherProviderTimeoutError,
)


MISSING_SENTINELS = {9999.0, -9999.0, 999.9, -999.9, -999.0}


class INMETWeatherProvider:
    """Adapter para avisos públicos do INMET e observações SYNOP do WIS2."""

    REQUEST_HEADERS = {
        "Accept": "application/json",
        "User-Agent": "Desafio-I2A2-D5-Comunicacao-Proativa/0.1",
    }

    def __init__(
        self,
        settings: Settings | None = None,
        client: httpx.Client | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self._client = client

    def get_weather(self, latitude: float, longitude: float) -> WeatherInput:
        location = Location(latitude=latitude, longitude=longitude)
        alerts_payload = self._get_json(self.settings.inmet_alerts_url)
        alerts = self._parse_alerts(alerts_payload, latitude, longitude)
        observations = self._get_observations(latitude, longitude)
        return WeatherInput(
            location=location,
            observed_at=observations["observed_at"],
            measurements=observations["measurements"],
            alerts=alerts,
            source="INMET/WIS2",
        )

    def _get_json(self, url: str, params: dict[str, Any] | None = None) -> Any:
        try:
            if self._client is not None:
                response = self._client.get(
                    url, params=params, headers=self.REQUEST_HEADERS
                )
                response.raise_for_status()
                return response.json()
            with httpx.Client(timeout=self.settings.http_timeout_seconds) as client:
                response = client.get(
                    url, params=params, headers=self.REQUEST_HEADERS
                )
                response.raise_for_status()
                return response.json()
        except httpx.TimeoutException as exc:
            raise WeatherProviderTimeoutError(
                f"Timeout ao consultar a fonte meteorológica: {url}"
            ) from exc
        except httpx.HTTPStatusError as exc:
            raise WeatherProviderHTTPError(
                f"Erro HTTP {exc.response.status_code} ao consultar a fonte meteorológica."
            ) from exc
        except httpx.RequestError as exc:
            raise WeatherProviderHTTPError(
                f"Falha de comunicação com a fonte meteorológica: {url}"
            ) from exc
        except ValueError as exc:
            raise WeatherProviderInvalidResponseError(
                f"Resposta JSON inválida da fonte meteorológica: {url}"
            ) from exc

    def _parse_alerts(
        self,
        payload: Any,
        latitude: float,
        longitude: float,
    ) -> list[WeatherAlert]:
        if not isinstance(payload, dict):
            raise WeatherProviderInvalidResponseError(
                "O endpoint de avisos do INMET deve retornar um objeto JSON."
            )

        alerts: list[WeatherAlert] = []
        for bucket in ("hoje", "futuro"):
            entries = payload.get(bucket, [])
            if not isinstance(entries, list):
                raise WeatherProviderInvalidResponseError(
                    f"O campo '{bucket}' do INMET deve ser uma lista."
                )
            for raw_alert in entries:
                alert = self._parse_alert(raw_alert)
                geometry = self._parse_polygon(raw_alert.get("poligono"))
                if _point_in_geometry(longitude, latitude, geometry):
                    alerts.append(alert)
        return alerts

    def _parse_alert(self, raw_alert: Any) -> WeatherAlert:
        if not isinstance(raw_alert, dict):
            raise WeatherProviderInvalidResponseError(
                "Cada aviso do INMET deve ser um objeto JSON."
            )
        required = ("descricao", "poligono", "severidade")
        missing = [field for field in required if not raw_alert.get(field)]
        if not raw_alert.get("id") and not raw_alert.get("codigo"):
            missing.append("id/codigo")
        if not raw_alert.get("inicio") and not raw_alert.get("data_inicio"):
            missing.append("inicio/data_inicio")
        if missing:
            raise WeatherProviderInvalidResponseError(
                f"Aviso do INMET sem campos obrigatórios: {', '.join(missing)}"
            )

        start = _parse_datetime(
            raw_alert.get("inicio")
            or _combine_date_time(raw_alert.get("data_inicio"), raw_alert.get("hora_inicio"))
        )
        end_value = raw_alert.get("fim") or _combine_date_time(
            raw_alert.get("data_fim"), raw_alert.get("hora_fim")
        )
        risks = raw_alert.get("riscos") or []
        if not isinstance(risks, list) or not all(isinstance(item, str) for item in risks):
            raise WeatherProviderInvalidResponseError(
                "O campo 'riscos' do aviso do INMET deve ser uma lista de textos."
            )

        alert_id = str(raw_alert.get("id") or raw_alert["codigo"])
        return WeatherAlert(
            alert_id=alert_id,
            phenomenon=str(raw_alert["descricao"]),
            severity=str(raw_alert.get("severidade")) if raw_alert.get("severidade") else None,
            starts_at=start,
            ends_at=_parse_datetime(end_value) if end_value else None,
            description=" ".join(risks),
            risks=risks,
            measurements=_measurements_from_alert_text(" ".join(risks)),
            source_reference=str(raw_alert.get("codigo") or alert_id),
        )

    def _parse_polygon(self, value: Any) -> dict[str, Any]:
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except json.JSONDecodeError as exc:
                raise WeatherProviderInvalidResponseError(
                    "O polígono do aviso do INMET não é um JSON válido."
                ) from exc
        if not isinstance(value, dict) or value.get("type") not in {"Polygon", "MultiPolygon"}:
            raise WeatherProviderInvalidResponseError(
                "O polígono do aviso do INMET deve ser Polygon ou MultiPolygon."
            )
        if not value.get("coordinates"):
            raise WeatherProviderInvalidResponseError(
                "O polígono do aviso do INMET não possui coordenadas."
            )
        return value

    def _get_observations(self, latitude: float, longitude: float) -> dict[str, Any]:
        delta = self.settings.station_search_delta_degrees
        params = {
            "f": "json",
            "bbox": f"{longitude - delta},{latitude - delta},{longitude + delta},{latitude + delta}",
            "limit": 200,
            "sortby": "-reportTime",
        }
        payload = self._get_json(self.settings.wis2_synop_url, params=params)
        if not isinstance(payload, dict) or not isinstance(payload.get("features"), list):
            raise WeatherProviderInvalidResponseError(
                "A coleção SYNOP do WIS2 deve retornar um FeatureCollection."
            )
        features = payload["features"]
        if not features:
            raise WeatherProviderInvalidResponseError(
                "A coleção SYNOP do WIS2 não contém uma observação meteorológica."
            )

        station_features: dict[
            str, list[tuple[dict[str, Any], tuple[float, float]]]
        ] = {}
        for feature in features:
            if not isinstance(feature, dict):
                raise WeatherProviderInvalidResponseError(
                    "Feature inválida na coleção SYNOP do WIS2."
                )
            properties = feature.get("properties")
            geometry = feature.get("geometry")
            coordinates = geometry.get("coordinates") if isinstance(geometry, dict) else None
            if not isinstance(properties, dict) or not isinstance(coordinates, list) or len(coordinates) < 2:
                raise WeatherProviderInvalidResponseError(
                    "Feature SYNOP sem properties ou coordenadas obrigatórias."
                )
            if not properties.get("reportTime") or not properties.get("reportId"):
                raise WeatherProviderInvalidResponseError(
                    "Feature SYNOP sem reportTime ou reportId."
                )
            try:
                station_coordinates = (float(coordinates[0]), float(coordinates[1]))
            except (TypeError, ValueError) as exc:
                raise WeatherProviderInvalidResponseError(
                    "Coordenadas inválidas na feature SYNOP do WIS2."
                ) from exc
            if (
                not all(math.isfinite(coordinate) for coordinate in station_coordinates)
                or not -180 <= station_coordinates[0] <= 180
                or not -90 <= station_coordinates[1] <= 90
            ):
                raise WeatherProviderInvalidResponseError(
                    "Coordenadas fora do intervalo na feature SYNOP do WIS2."
                )
            station_id = _station_identity(properties)
            station_features.setdefault(station_id, []).append(
                (feature, station_coordinates)
            )

        nearest_station_id = min(
            station_features,
            key=lambda station_id: _distance_to_latest_station_report(
                station_features[station_id], latitude, longitude
            ),
        )
        selected_station_features = station_features[nearest_station_id]
        latest_feature, _ = max(
            selected_station_features,
            key=lambda item: _parse_datetime(item[0]["properties"]["reportTime"]),
        )
        latest_report_id = latest_feature["properties"]["reportId"]
        latest_report = [
            feature
            for feature, _coordinates in selected_station_features
            if feature["properties"]["reportId"] == latest_report_id
        ]
        measurements = _measurements_from_synop(latest_report)
        return {
            "observed_at": _parse_datetime(latest_feature["properties"]["reportTime"]),
            "measurements": measurements,
        }


def _station_identity(properties: dict[str, Any]) -> str:
    """Obtém o identificador estável da estação, não sua coordenada do relatório."""
    for field in (
        "wigos_station_identifier",
        "station_id",
        "station",
        "wigos_id",
    ):
        value = properties.get(field)
        if value is not None and str(value).strip():
            return str(value)

    report_id = str(properties["reportId"])
    match = re.match(r"^(?P<station>.+)-\d{12}$", report_id)
    return match.group("station") if match else report_id


def _distance_to_latest_station_report(
    features: list[tuple[dict[str, Any], tuple[float, float]]],
    latitude: float,
    longitude: float,
) -> float:
    """Usa a posição do relatório mais recente para escolher a estação próxima."""
    _, coordinates = max(
        features,
        key=lambda item: _parse_datetime(item[0]["properties"]["reportTime"]),
    )
    return (coordinates[0] - longitude) ** 2 + (coordinates[1] - latitude) ** 2


def _combine_date_time(date_value: Any, time_value: Any) -> str | None:
    if not date_value:
        return None
    date_text = str(date_value).replace("Z", "")
    if time_value:
        return f"{date_text[:10]} {time_value}"
    return date_text


def _parse_datetime(value: Any) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise WeatherProviderInvalidResponseError("Data/hora meteorológica inválida.")
    text = value.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise WeatherProviderInvalidResponseError(
            f"Data/hora meteorológica inválida: {value}"
        ) from exc
    return parsed.replace(tzinfo=parsed.tzinfo or timezone.utc)


def _numeric(value: Any, field: str) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise WeatherProviderInvalidResponseError(
            f"Valor inválido para a medição '{field}'."
        ) from exc
    if not math.isfinite(number):
        raise WeatherProviderInvalidResponseError(
            f"Valor não finito para a medição '{field}'."
        )
    if number in MISSING_SENTINELS:
        return None
    return number


def _measurements_from_alert_text(text: str) -> Measurements:
    normalized = text.lower().replace(",", ".")
    rain_rate: float | None = None
    daily_rain: float | None = None
    wind_speed: float | None = None

    rain_match = re.search(
        r"chuva.*?(\d+(?:\.\d+)?)\s*(?:a|e|-)\s*(\d+(?:\.\d+)?)\s*mm\s*/\s*h",
        normalized,
    )
    if rain_match:
        rain_rate = float(rain_match.group(2))
    daily_match = re.search(r"ate\s*(\d+(?:\.\d+)?)\s*mm\s*/\s*dia", normalized)
    if daily_match:
        daily_rain = float(daily_match.group(1))
    wind_match = re.search(
        r"(?:vento|rajada).*?(\d+(?:\.\d+)?)\s*(?:a|e|-)\s*(\d+(?:\.\d+)?)\s*km\s*/\s*h",
        normalized,
    )
    if wind_match:
        wind_speed = float(wind_match.group(2))
    return Measurements(
        precipitation_mm=daily_rain,
        precipitation_rate_mm_per_hour=rain_rate,
        wind_speed_kmh=wind_speed,
    )


def _measurements_from_synop(features: list[dict[str, Any]]) -> Measurements:
    values: dict[str, float | None] = {}
    for feature in features:
        properties = feature["properties"]
        name = properties.get("name")
        value = properties.get("value")
        if value is None or value == "" or str(value).lower() == "null":
            continue
        if name == "air_temperature":
            converted = _convert_temperature(value, properties.get("units"))
            if converted is not None:
                values["temperature_celsius"] = converted
        elif name == "total_precipitation_or_total_water_equivalent":
            converted = _convert_precipitation(value, properties.get("units"))
            if converted is not None:
                values["precipitation_mm"] = converted
        elif name == "wind_speed":
            converted = _convert_speed(value, properties.get("units"))
            if converted is not None:
                values["wind_speed_kmh"] = converted
        elif name == "maximum_wind_gust_speed":
            converted = _convert_speed(value, properties.get("units"))
            if converted is not None:
                values["wind_gust_kmh"] = converted
    return Measurements(**values)


def _convert_temperature(value: Any, units: Any) -> float | None:
    number = _numeric(value, "temperature")
    if number is None:
        return None
    unit = str(units or "").lower()
    if unit in {"c", "celsius", "°c"}:
        return number
    if unit in {"k", "kelvin"}:
        return number - 273.15
    raise WeatherProviderInvalidResponseError(f"Unidade de temperatura não suportada: {units}")


def _convert_precipitation(value: Any, units: Any) -> float | None:
    number = _numeric(value, "precipitation")
    if number is None:
        return None
    if number < 0:
        raise WeatherProviderInvalidResponseError(
            "Precipitação não pode ser negativa."
        )
    unit = str(units or "").lower().replace("²", "2")
    if unit in {"mm", "kg m-2", "kg/m2", "kg m-2"}:
        return number
    if unit in {"m", "metre", "meter"}:
        return number * 1000
    raise WeatherProviderInvalidResponseError(f"Unidade de precipitação não suportada: {units}")


def _convert_speed(value: Any, units: Any) -> float | None:
    number = _numeric(value, "wind")
    if number is None:
        return None
    if number < 0:
        raise WeatherProviderInvalidResponseError(
            "Velocidade do vento não pode ser negativa."
        )
    unit = str(units or "").lower().replace(" ", "")
    if unit in {"km/h", "kmh"}:
        return number
    if unit in {"m/s", "ms-1", "ms"}:
        return number * 3.6
    raise WeatherProviderInvalidResponseError(f"Unidade de velocidade não suportada: {units}")


def _point_in_geometry(longitude: float, latitude: float, geometry: dict[str, Any]) -> bool:
    if geometry["type"] == "Polygon":
        return any(_point_in_ring(longitude, latitude, ring) for ring in geometry["coordinates"])
    return any(
        any(_point_in_ring(longitude, latitude, ring) for ring in polygon)
        for polygon in geometry["coordinates"]
    )


def _point_in_ring(longitude: float, latitude: float, ring: Any) -> bool:
    if not isinstance(ring, list) or len(ring) < 3:
        raise WeatherProviderInvalidResponseError("Anel poligonal inválido no aviso do INMET.")
    inside = False
    previous = ring[-1]
    for current in ring:
        if not isinstance(current, list) or len(current) < 2:
            raise WeatherProviderInvalidResponseError("Coordenada poligonal inválida no aviso do INMET.")
        try:
            x1, y1 = float(previous[0]), float(previous[1])
            x2, y2 = float(current[0]), float(current[1])
        except (TypeError, ValueError) as exc:
            raise WeatherProviderInvalidResponseError(
                "Valores inválidos nas coordenadas do polígono do INMET."
            ) from exc
        intersects = ((y1 > latitude) != (y2 > latitude)) and (
            longitude < (x2 - x1) * (latitude - y1) / ((y2 - y1) or 1e-12) + x1
        )
        if intersects:
            inside = not inside
        previous = current
    return inside

from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from src.domain.insurance.location_matcher import (
    CoordinateRadiusMatcher,
    haversine_distance_km,
)
from src.domain.insurance.models import Insured, Policy
from src.domain.insurance.enums import PolicyStatus, PolicyType
from src.domain.location import Location
from src.domain.weather.enums import EventType, EvidenceType, Severity
from src.domain.weather.models import Measurements, WeatherEvent


def make_event(latitude: float = -15.79, longitude: float = -47.93) -> WeatherEvent:
    return WeatherEvent(
        event_id="event-1",
        event_type=EventType.HEAVY_RAIN,
        evidence_type=EvidenceType.ALERT,
        severity=Severity.HIGH,
        timestamp=datetime(2026, 9, 2, 13, tzinfo=timezone.utc),
        location=Location(latitude=latitude, longitude=longitude),
        measurements=Measurements(),
        source="test",
    )


def make_insured(latitude: float = -15.79, longitude: float = -47.93) -> Insured:
    return Insured(
        insured_id="insured-1",
        name="Pessoa Fictícia",
        location=Location(latitude=latitude, longitude=longitude),
        policies=[
            Policy(
                policy_id="policy-1",
                policy_type=PolicyType.HOME,
                status=PolicyStatus.ACTIVE,
            )
        ],
    )


def test_same_location_has_zero_distance():
    location = Location(latitude=-15.79, longitude=-47.93)

    assert haversine_distance_km(location, location) == pytest.approx(0)


def test_location_inside_radius_matches():
    matcher = CoordinateRadiusMatcher(radius_km=25)
    insured = make_insured(latitude=-15.90, longitude=-47.93)

    assert matcher.matches(make_event(), insured) is True


def test_location_at_exact_radius_matches():
    event = make_event()
    insured = make_insured(latitude=-15.90, longitude=-47.93)
    distance = haversine_distance_km(event.location, insured.location)
    matcher = CoordinateRadiusMatcher(radius_km=distance)

    assert matcher.matches(event, insured) is True


def test_location_outside_radius_does_not_match():
    matcher = CoordinateRadiusMatcher(radius_km=25)
    insured = make_insured(latitude=-16.50, longitude=-47.93)

    assert matcher.matches(make_event(), insured) is False


def test_coordinates_in_different_hemispheres_are_calculated():
    distance = haversine_distance_km(
        Location(latitude=-15.79, longitude=-47.93),
        Location(latitude=15.79, longitude=47.93),
    )

    assert distance > 0
    assert distance == pytest.approx(11087, rel=0.01)


def test_missing_or_invalid_coordinates_are_not_exposed():
    matcher = CoordinateRadiusMatcher(radius_km=25)
    insured = make_insured()
    missing_location_event = SimpleNamespace(location=SimpleNamespace())
    invalid_location_insured = SimpleNamespace(
        location=SimpleNamespace(latitude=float("nan"), longitude=-47.93)
    )

    assert matcher.matches(missing_location_event, insured) is False
    assert matcher.matches(make_event(), invalid_location_insured) is False


def test_radius_must_be_positive_and_finite():
    with pytest.raises(ValueError):
        CoordinateRadiusMatcher(0)
    with pytest.raises(ValueError):
        CoordinateRadiusMatcher(float("inf"))

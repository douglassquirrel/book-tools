from datetime import datetime, timedelta, timezone

import pytest

from booktools.clock import revision_dates

pytestmark = pytest.mark.tier1


def at(text):
    return datetime.fromisoformat(text).replace(tzinfo=timezone.utc)


def test_writes_london_clock_time_with_a_z_and_the_true_utc_beside_it():
    # The case seen in a file Word saved: a change made at 14:46 British Summer Time.
    assert revision_dates(at("2026-10-03T13:46:31")) == (
        "2026-10-03T14:46:00Z",
        "2026-10-03T13:46:00Z",
    )
    assert revision_dates(at("2026-01-15T09:05:00")) == (
        "2026-01-15T09:05:00Z",
        "2026-01-15T09:05:00Z",
    )


def test_summer_time_runs_from_the_last_sunday_of_march_to_the_last_of_october():
    assert revision_dates(at("2026-03-29T00:59:00"))[0] == "2026-03-29T00:59:00Z"
    assert revision_dates(at("2026-03-29T01:00:00"))[0] == "2026-03-29T02:00:00Z"
    assert revision_dates(at("2026-10-25T00:59:00"))[0] == "2026-10-25T01:59:00Z"
    assert revision_dates(at("2026-10-25T01:00:00"))[0] == "2026-10-25T01:00:00Z"
    assert revision_dates(at("2027-03-28T01:00:00"))[0] == "2027-03-28T02:00:00Z"


def test_an_instant_given_in_another_zone_is_converted():
    instant = datetime(2026, 7, 1, 8, 0, tzinfo=timezone(timedelta(hours=-4)))
    assert revision_dates(instant) == ("2026-07-01T13:00:00Z", "2026-07-01T12:00:00Z")


def test_with_utc_both_dates_are_utc():
    assert revision_dates(at("2026-10-03T13:46:31"), utc=True) == (
        "2026-10-03T13:46:00Z",
        "2026-10-03T13:46:00Z",
    )

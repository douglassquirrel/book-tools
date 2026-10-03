"""Dates as Word writes them on a tracked change."""

from datetime import datetime, timedelta, timezone


def revision_dates(instant, utc=False):
    """Return (w:date, w16du:dateUtc) for a change made at `instant`, an aware datetime.

    Word writes the local clock time in w:date, to the minute, with a "Z" although
    it is not UTC, and the true UTC time in w16du:dateUtc. Local is London time
    unless `utc` is true.
    """
    true = instant.astimezone(timezone.utc).replace(second=0, microsecond=0)
    local = true if utc else london(true)
    form = "%Y-%m-%dT%H:%M:%SZ"
    return local.strftime(form), true.strftime(form)


def london(instant):
    """The London clock time of a UTC `instant`, by the rule in force since 1996:
    one hour ahead from 01:00 UTC on the last Sunday of March to 01:00 UTC on the
    last Sunday of October. Worked out here so that no time-zone data is needed."""
    start = _last_sunday(instant.year, 3)
    end = _last_sunday(instant.year, 10)
    return instant + timedelta(hours=1) if start <= instant < end else instant


def _last_sunday(year, month):
    """01:00 UTC on the last Sunday of the month."""
    day = datetime(year, month, 31, 1, 0, tzinfo=timezone.utc)
    return day - timedelta(days=(day.weekday() + 1) % 7)

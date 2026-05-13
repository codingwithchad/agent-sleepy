"""Pull sleep and activity data from Garmin Connect."""

from __future__ import annotations

import logging
import os
from collections.abc import Callable
from datetime import date, datetime, timedelta, timezone

from dotenv import find_dotenv, load_dotenv
from garminconnect import Garmin

from sleepy.models.sleep import GarminSleepNight, SleepNight
from sleepy.models.workout import GarminActivity, Workout

# Walk up from the repo root until a .env is found — works whether it lives
# inside the repo or one level above it (the preferred location).
load_dotenv(find_dotenv(raise_error_if_not_found=False, usecwd=True))
logger = logging.getLogger(__name__)

# Keys from dailySleepDTO that we actively use. Anything else gets logged
# on the first call so we know what we might be missing.
_USED_KEYS = {
    "calendarDate",
    "sleepStartTimestampGMT",
    "sleepEndTimestampGMT",
    "deepSleepSeconds",
    "lightSleepSeconds",
    "remSleepSeconds",
    "awakeSleepSeconds",
    "sleepScores",
    "averageHrvValue",
    "averageRespirationValue",
    "restlessMomentsCount",
    "sleepStartLatencySeconds",
}

_extra_keys_logged = False
_extra_activity_keys_logged = False

# Keys from activity records that we actively use.
_USED_ACTIVITY_KEYS = {
    "activityId",
    "activityName",
    "activityType",
    "startTimeGMT",
    "duration",
    "averageHR",
    "maxHR",
    "calories",
    "aerobicTrainingEffect",
    "anaerobicTrainingEffect",
    "hrTimeInZone_1",
    "hrTimeInZone_2",
    "hrTimeInZone_3",
    "hrTimeInZone_4",
    "hrTimeInZone_5",
}


def _log_extra_keys(dto: dict) -> None:
    """Log any keys in the DTO we don't currently use. Runs once per process."""
    global _extra_keys_logged
    if _extra_keys_logged:
        return
    _extra_keys_logged = True
    extras = sorted(set(dto.keys()) - _USED_KEYS)
    if extras:
        logger.info("Unused dailySleepDTO keys (consider adding to model): %s", extras)


def _parse_night(raw: dict) -> GarminSleepNight | None:
    """Parse one Garmin sleep response dict into a GarminSleepNight.

    Returns None if the response has no usable data (didn't wear the device,
    or Garmin returned an empty DTO).
    """
    dto = raw.get("dailySleepDTO")
    if not dto:
        return None

    start_ms = dto.get("sleepStartTimestampGMT")
    end_ms = dto.get("sleepEndTimestampGMT")
    if not start_ms or not end_ms:
        return None

    _log_extra_keys(dto)

    start_utc = datetime.fromtimestamp(start_ms / 1000, tz=timezone.utc)
    end_utc = datetime.fromtimestamp(end_ms / 1000, tz=timezone.utc)

    deep_s = dto.get("deepSleepSeconds") or 0
    light_s = dto.get("lightSleepSeconds") or 0
    rem_s = dto.get("remSleepSeconds") or 0
    awake_s = dto.get("awakeSleepSeconds") or 0

    # Score lives at sleepScores.overall.value
    score: int | None = None
    scores = dto.get("sleepScores") or {}
    overall = scores.get("overall") or {}
    if isinstance(overall, dict):
        raw_score = overall.get("value")
        score = int(raw_score) if raw_score is not None else None

    latency_s = dto.get("sleepStartLatencySeconds")

    return GarminSleepNight(
        date=date.fromisoformat(dto["calendarDate"]),
        sleep_start_utc=start_utc,
        sleep_end_utc=end_utc,
        duration_min=(deep_s + light_s + rem_s) // 60,
        score=score,
        deep_min=deep_s // 60 if deep_s else None,
        light_min=light_s // 60 if light_s else None,
        rem_min=rem_s // 60 if rem_s else None,
        awake_min=awake_s // 60 if awake_s else None,
        avg_hrv=dto.get("averageHrvValue"),
        avg_respiration=dto.get("averageRespirationValue"),
        restless_moments=dto.get("restlessMomentsCount"),
        sleep_latency_min=latency_s // 60 if latency_s else None,
    )


def fetch_sleep_nights(
    days: int = 7,
    prompt_mfa: Callable[[], str] | None = None,
) -> list[GarminSleepNight]:
    """Pull the last `days` nights of sleep from Garmin Connect.

    Reads GARMIN_EMAIL and GARMIN_PASSWORD from env (via .env).
    To cache session tokens and avoid re-auth on every run, set
    GARMINTOKENS to a writable file path (e.g. ~/.garmin_tokens).

    If your account has 2FA enabled, pass a callable for `prompt_mfa` that
    returns the one-time code as a string. Defaults to an interactive
    `input()` prompt — fine for manual runs, not for cron.

    Nights where no data exists (device not worn, API gap) are silently
    skipped. Fetch errors per-night are logged as warnings.
    """
    email = os.environ["GARMIN_EMAIL"]
    password = os.environ["GARMIN_PASSWORD"]

    if prompt_mfa is None:
        prompt_mfa = lambda: input("Garmin 2FA code: ")  # noqa: E731

    garmin = Garmin(email=email, password=password, prompt_mfa=prompt_mfa)
    garmin.login()  # uses GARMINTOKENS env var automatically if set

    today = date.today()
    nights: list[GarminSleepNight] = []

    for i in range(1, days + 1):
        target = today - timedelta(days=i)
        date_str = target.isoformat()
        try:
            raw = garmin.get_sleep_data(date_str)
            night = _parse_night(raw)
            if night is None:
                logger.info("No sleep data for %s — skipping", date_str)
                continue
            nights.append(night)
        except Exception:
            logger.warning("Failed to fetch %s", date_str, exc_info=True)

    return nights


def garmin_to_sleep_night(night: GarminSleepNight) -> SleepNight:
    """Map a Garmin-specific sleep record to the canonical SleepNight model.

    This is the seam between device-specific ingest and the device-agnostic
    store. Oura, Whoop, etc. would each have their own equivalent function.
    """
    return SleepNight(
        date=night.date,
        source="garmin",
        sleep_start_utc=night.sleep_start_utc,
        sleep_end_utc=night.sleep_end_utc,
        duration_min=night.duration_min,
        score=night.score,
        deep_min=night.deep_min,
        light_min=night.light_min,
        rem_min=night.rem_min,
        awake_min=night.awake_min,
        avg_hrv=night.avg_hrv,
        avg_respiration=night.avg_respiration,
        restless_moments=night.restless_moments,
        sleep_latency_min=night.sleep_latency_min,
    )


def _log_extra_activity_keys(raw: dict) -> None:
    """Log any activity keys we don't currently use. Runs once per process."""
    global _extra_activity_keys_logged
    if _extra_activity_keys_logged:
        return
    _extra_activity_keys_logged = True
    extras = sorted(set(raw.keys()) - _USED_ACTIVITY_KEYS)
    if extras:
        logger.info("Unused activity keys (consider adding to model): %s", extras)


def _parse_activity(raw: dict) -> GarminActivity | None:
    """Parse one Garmin activity dict into a GarminActivity.

    Returns None if the record is missing required fields (e.g. manual entries
    with no timestamp).
    """
    activity_id = raw.get("activityId")
    start_gmt = raw.get("startTimeGMT")
    if not activity_id or not start_gmt:
        return None

    _log_extra_activity_keys(raw)

    # Garmin returns "YYYY-MM-DD HH:MM:SS" in GMT — attach UTC explicitly.
    start_utc = datetime.strptime(start_gmt, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
    duration_s = int(raw.get("duration") or 0)
    end_utc = start_utc + timedelta(seconds=duration_s)

    activity_type_dict = raw.get("activityType") or {}
    activity_type = activity_type_dict.get("typeKey") or "unknown"

    avg_hr = raw.get("averageHR")
    max_hr = raw.get("maxHR")
    calories = raw.get("calories")

    def _zone_min(key: str) -> int | None:
        val = raw.get(key)
        return int(val) // 60 if val is not None else None

    return GarminActivity(
        activity_id=int(activity_id),
        date=start_utc.date(),
        name=raw.get("activityName"),
        activity_type=activity_type,
        start_time_utc=start_utc,
        end_time_utc=end_utc,
        duration_min=duration_s // 60,
        avg_hr=int(avg_hr) if avg_hr is not None else None,
        max_hr=int(max_hr) if max_hr is not None else None,
        calories=int(calories) if calories is not None else None,
        aerobic_te=raw.get("aerobicTrainingEffect"),
        anaerobic_te=raw.get("anaerobicTrainingEffect"),
        hr_zone_1_min=_zone_min("hrTimeInZone_1"),
        hr_zone_2_min=_zone_min("hrTimeInZone_2"),
        hr_zone_3_min=_zone_min("hrTimeInZone_3"),
        hr_zone_4_min=_zone_min("hrTimeInZone_4"),
        hr_zone_5_min=_zone_min("hrTimeInZone_5"),
    )


def fetch_activities(
    days: int = 7,
    prompt_mfa: Callable[[], str] | None = None,
) -> list[GarminActivity]:
    """Pull the last `days` worth of activities from Garmin Connect.

    Uses the same auth pattern as fetch_sleep_nights — shares credentials
    from .env, caches session via GARMINTOKENS if set.

    Activities with missing required fields are silently skipped and logged.
    """
    email = os.environ["GARMIN_EMAIL"]
    password = os.environ["GARMIN_PASSWORD"]

    if prompt_mfa is None:
        prompt_mfa = lambda: input("Garmin 2FA code: ")  # noqa: E731

    garmin = Garmin(email=email, password=password, prompt_mfa=prompt_mfa)
    garmin.login()

    today = date.today()
    start_date = today - timedelta(days=days)

    logger.info("Fetching activities from %s to %s", start_date.isoformat(), today.isoformat())

    try:
        raw_list = garmin.get_activities_by_date(start_date.isoformat(), today.isoformat())
    except Exception:
        logger.warning("Failed to fetch activities", exc_info=True)
        return []

    activities: list[GarminActivity] = []
    for raw in raw_list:
        activity = _parse_activity(raw)
        if activity is None:
            logger.info("Skipping activity with missing required fields: %s", raw.get("activityId"))
            continue
        activities.append(activity)

    return activities


def garmin_to_workout(activity: GarminActivity) -> Workout:
    """Map a Garmin-specific activity to the canonical Workout model.

    The seam between device-specific ingest and the device-agnostic store.
    """
    return Workout(
        activity_id=activity.activity_id,
        source="garmin",
        date=activity.date,
        name=activity.name,
        activity_type=activity.activity_type,
        start_time_utc=activity.start_time_utc,
        end_time_utc=activity.end_time_utc,
        duration_min=activity.duration_min,
        avg_hr=activity.avg_hr,
        max_hr=activity.max_hr,
        calories=activity.calories,
        aerobic_te=activity.aerobic_te,
        anaerobic_te=activity.anaerobic_te,
        hr_zone_1_min=activity.hr_zone_1_min,
        hr_zone_2_min=activity.hr_zone_2_min,
        hr_zone_3_min=activity.hr_zone_3_min,
        hr_zone_4_min=activity.hr_zone_4_min,
        hr_zone_5_min=activity.hr_zone_5_min,
    )

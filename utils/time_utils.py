import re
from datetime import datetime, timezone, timedelta
from typing import Optional


def parse_time_to_timestamp(time_str: str) -> Optional[int]:
    if not time_str:
        return None
    
    if re.match(r"^\d+$", time_str):
        ts = int(time_str)
        if ts > 10**12:
            return ts
        return ts * 1000
    
    formats = [
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S.%f%z",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
    ]
    
    for fmt in formats:
        try:
            dt = datetime.strptime(time_str, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone(timedelta(hours=8)))
            return int(dt.timestamp() * 1000)
        except ValueError:
            continue
    
    return None


def timestamp_to_iso8601(timestamp: int | str) -> str:
    if isinstance(timestamp, str):
        timestamp = int(timestamp)
    
    if timestamp > 10**12:
        timestamp = timestamp // 1000
    
    dt = datetime.fromtimestamp(timestamp, tz=timezone(timedelta(hours=8)))
    return dt.strftime("%Y-%m-%dT%H:%M:%S+08:00")


def timestamp_to_datetime_str(timestamp: int | str) -> str:
    if isinstance(timestamp, str):
        timestamp = int(timestamp)
    
    if timestamp > 10**12:
        timestamp = timestamp // 1000
    
    dt = datetime.fromtimestamp(timestamp, tz=timezone(timedelta(hours=8)))
    return dt.strftime("%Y-%m-%d %H:%M:%S")

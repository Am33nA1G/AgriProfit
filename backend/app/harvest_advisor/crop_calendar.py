"""Crop calendar -- sowing/harvest windows per crop and season."""
from __future__ import annotations
import calendar

CROP_CALENDAR: dict[str, dict] = {
    "rice":        {"seasons": ["kharif"],          "sow": [6, 7],    "harvest": [10, 11]},
    "wheat":       {"seasons": ["rabi"],             "sow": [10, 11],  "harvest": [3, 4]},
    "maize":       {"seasons": ["kharif", "rabi"],   "sow": [6, 7],    "harvest": [9, 10]},
    "cotton":      {"seasons": ["kharif"],           "sow": [5, 6],    "harvest": [10, 12]},
    "onion":       {"seasons": ["rabi", "kharif"],   "sow": [10, 11],  "harvest": [2, 3]},
    "tomato":      {"seasons": ["kharif", "rabi", "zaid"], "sow": [6, 7], "harvest": [9, 10]},
    "potato":      {"seasons": ["rabi"],             "sow": [10, 11],  "harvest": [1, 2]},
    "brinjal":     {"seasons": ["kharif", "rabi"],   "sow": [6, 7],    "harvest": [9, 10]},
    "cauliflower": {"seasons": ["rabi"],             "sow": [9, 10],   "harvest": [12, 1]},
    "carrot":      {"seasons": ["rabi"],             "sow": [10, 11],  "harvest": [1, 2]},
    "mustard":     {"seasons": ["rabi"],             "sow": [10, 11],  "harvest": [2, 3]},
    "groundnut":   {"seasons": ["kharif"],           "sow": [6, 7],    "harvest": [10, 11]},
    "soybean":     {"seasons": ["kharif"],           "sow": [6, 7],    "harvest": [10, 11]},
    "sunflower":   {"seasons": ["kharif", "rabi"],   "sow": [6, 7],    "harvest": [10, 11]},
    "arhar":       {"seasons": ["kharif"],           "sow": [6, 7],    "harvest": [11, 12]},
    "moong":       {"seasons": ["kharif", "zaid"],   "sow": [6, 7],    "harvest": [9, 10]},
    "urad":        {"seasons": ["kharif"],           "sow": [6, 7],    "harvest": [9, 10]},
    "chana":       {"seasons": ["rabi"],             "sow": [10, 11],  "harvest": [2, 3]},
    "mango":       {"seasons": ["kharif", "annual"], "sow": [7, 8],    "harvest": [4, 6]},
    "banana":      {"seasons": ["annual"],           "sow": [6, 7],    "harvest": [12, 2]},
}

def get_crops_for_season(season: str) -> list[str]:
    """Return crops eligible for the given season."""
    if season == "annual":
        return list(CROP_CALENDAR.keys())
    return [c for c, v in CROP_CALENDAR.items() if season in v["seasons"]]


def format_window(months: list[int]) -> str:
    """Format [6, 7] -> 'Jun – Jul' using standard month abbreviations."""
    return f"{calendar.month_abbr[months[0]]} \u2013 {calendar.month_abbr[months[1]]}"

"""Dataset taxonomy helpers aligned with the Phase 3 contracts."""

from __future__ import annotations

from collections.abc import Mapping

PHASE3_OBJECT_TYPES: frozenset[str] = frozenset(
    {
        "wall",
        "door",
        "window",
        "column",
        "beam",
        "slab",
        "stair",
        "room",
        "dimension",
        "text",
        "symbol",
        "furniture",
        "plumbing",
        "electrical",
        "opening",
        "unknown",
    }
)

STRUCTURAL_CATEGORIES: frozenset[str] = frozenset(
    {"wall", "railing", "column", "beam", "slab", "chimney"}
)
OPENING_CATEGORIES: frozenset[str] = frozenset({"door", "front_door", "window", "opening"})
SPACE_CATEGORIES: frozenset[str] = frozenset(
    {
        "room",
        "living",
        "bedroom",
        "bathroom",
        "kitchen",
        "dining",
        "hallway",
        "entry",
        "storage",
        "garage",
        "balcony",
        "outdoor",
        "other_room",
        "stair",
        "sauna",
        "closet",
        "utility",
    }
)
FIXTURE_CATEGORIES: frozenset[str] = frozenset(
    {"furniture", "plumbing", "electrical", "fixture", "appliance", "symbol"}
)

CUBICASA_SPACE_CATEGORY_MAP: Mapping[str, str] = {
    "Alcove": "room",
    "Attic": "storage",
    "Ballroom": "room",
    "Bar": "room",
    "Basement": "storage",
    "Bath": "bathroom",
    "Bathroom": "bathroom",
    "Bedroom": "bedroom",
    "Below150cm": "storage",
    "CarPort": "garage",
    "Church": "room",
    "Closet": "closet",
    "ConferenceRoom": "room",
    "Conservatory": "room",
    "Counter": "fixture",
    "Den": "room",
    "Dining": "dining",
    "DraughtLobby": "entry",
    "Entry": "entry",
    "ExerciseRoom": "room",
    "Garage": "garage",
    "Hall": "hallway",
    "HallWay": "hallway",
    "Kitchen": "kitchen",
    "Library": "room",
    "LivingRoom": "living",
    "Lounge": "living",
    "MediaRoom": "room",
    "MeetingRoom": "room",
    "Nook": "room",
    "Office": "room",
    "OpenToBelow": "room",
    "Outdoor": "outdoor",
    "Pantry": "storage",
    "Reception": "room",
    "RecreationRoom": "room",
    "Sauna": "sauna",
    "Storage": "storage",
    "Stairs": "stair",
    "TechnicalRoom": "utility",
    "Undefined": "unknown",
    "Utility": "utility",
    "Wall": "wall",
    "Wardrobe": "closet",
    "WC": "bathroom",
}

CUBICASA_ICON_CATEGORY_MAP: Mapping[str, str] = {
    "Bathtub": "plumbing",
    "Cabinet": "furniture",
    "Chimney": "chimney",
    "Closet": "closet",
    "CoatCloset": "closet",
    "CookingCounter": "fixture",
    "Dishwasher": "appliance",
    "ElectricalAppliance": "electrical",
    "FirePlace": "fixture",
    "Fireplace": "fixture",
    "GeneralAppliance": "appliance",
    "IntegratedStove": "appliance",
    "KitchenCabinet": "furniture",
    "SaunaBench": "furniture",
    "Shower": "plumbing",
    "Sink": "plumbing",
    "Sofa": "furniture",
    "Stove": "appliance",
    "Toilet": "plumbing",
    "WashingMachine": "appliance",
}

RESPLAN_CATEGORY_MAP: Mapping[str, str] = {
    "balacony": "balcony",
    "balcony": "balcony",
    "bath": "bathroom",
    "bathroom": "bathroom",
    "bedroom": "bedroom",
    "door": "door",
    "front_door": "front_door",
    "garden": "outdoor",
    "inner": "room",
    "inner_polygon": "room",
    "kitchen": "kitchen",
    "land": "outdoor",
    "living": "living",
    "neighbor": "outdoor",
    "stair": "stair",
    "stairs": "stair",
    "storage": "storage",
    "wall": "wall",
    "window": "window",
}


def normalize_label(label: str) -> str:
    """Normalize external annotation labels for comparisons and filenames."""
    stripped = label.strip().replace("-", "_").replace(" ", "_")
    chars = [char if char.isalnum() or char == "_" else "_" for char in stripped]
    normalized = "".join(chars).strip("_").lower()
    while "__" in normalized:
        normalized = normalized.replace("__", "_")
    return normalized or "unknown"


def cubicasa_category_from_group(group_id: str | None, class_name: str | None) -> str:
    """Map a CubiCasa SVG group to a Phase 3-compatible dataset category."""
    if group_id == "Wall":
        return "wall"
    if group_id == "Railing":
        return "railing"
    if group_id == "Door":
        return "door"
    if group_id == "Window":
        return "window"

    if not class_name:
        return "unknown"

    class_tokens = class_name.split()
    if "Space" in class_tokens:
        index = class_tokens.index("Space")
        source_label = class_tokens[index + 1] if len(class_tokens) > index + 1 else "Undefined"
        return CUBICASA_SPACE_CATEGORY_MAP.get(source_label, "room")

    if "FixedFurniture" in class_tokens:
        index = class_tokens.index("FixedFurniture")
        source_label = class_tokens[index + 1] if len(class_tokens) > index + 1 else "Misc"
        return CUBICASA_ICON_CATEGORY_MAP.get(source_label, "fixture")

    return "unknown"


def resplan_category_from_key(key: str) -> str:
    """Map a ResPlan record key to a normalized dataset category."""
    return RESPLAN_CATEGORY_MAP.get(normalize_label(key), normalize_label(key))


def phase3_object_type(category: str) -> str:
    """Return the closest Phase 3 perception object type for a dataset category."""
    normalized = normalize_label(category)
    if normalized in PHASE3_OBJECT_TYPES:
        return normalized
    if normalized in STRUCTURAL_CATEGORIES:
        return "wall"
    if normalized in OPENING_CATEGORIES:
        return "opening"
    if normalized in SPACE_CATEGORIES:
        return "room"
    if normalized in FIXTURE_CATEGORIES:
        return "furniture"
    return "unknown"

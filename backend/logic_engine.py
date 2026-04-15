import math
from datetime import datetime


def calculate_bay_spacing_details(total_length, max_bay=8.0):
    """
    Calculates number of bays and spacing string (e.g., '4@7.50').
    """
    if total_length <= 0:
        return 0, "0@0.00"
    num_bays = math.ceil(total_length / max_bay)
    if num_bays == 0:
        num_bays = 1
    spacing = round(total_length / num_bays, 2)
    return num_bays, f"{num_bays}@{spacing:.2f}"


def safe_float(value, default=0.0):
    """Safe float conversion with fallback."""
    try:
        return float(value) if value is not None else default
    except (ValueError, TypeError):
        return default


def process_specifications(raw_data):
    """
    Logic Engine: Reads the nested JSON from extractor and produces
    a flat dict with all computed values ready for excel_filler.py.

    FIX 1: Reads from nested keys (raw_data['dimensions']['length_m'])
    instead of flat keys (raw_data['length']) to match the extractor output schema.

    FIX 2: Height logic uses left/right eave heights from extractor.
    Old code used raw_data.get('height') and raw_data.get('height_type') which no
    longer exist in the new schema.

    FIX 3: design_code default changed to "AISC" (was "IS Code" — wrong default
    per spec sheet which says AISC unless client requests IS).

    FIX 4: canopy_height logic fixed. Old code was eave_height - 1.0 which is wrong.
    Spec says canopy clear top height = door_height + 500mm.

    FIX 5: building_type threshold fixed to 30m (was 40m — spec says >30m gets interior columns).
    """
    if not raw_data:
        raw_data = {}

    # ── Pull nested sub-dicts safely ─────────────────────────────────────────
    dims   = raw_data.get("dimensions", {})
    loads  = raw_data.get("loads", {})
    sheet  = raw_data.get("sheeting", {})
    opens  = raw_data.get("openings", {})
    crane  = raw_data.get("crane", {})
    mezz   = raw_data.get("mezzanine", {})
    canopy = raw_data.get("canopy", {})
    acc    = raw_data.get("accessories", {})
    mats   = raw_data.get("material_grades", {})
    defl   = raw_data.get("deflection_limits", {})

    # ── Dimensions ────────────────────────────────────────────────────────────
    length = safe_float(dims.get("length_m"), 0.0)
    width  = safe_float(dims.get("width_m"),  0.0)

    # FIX 2: Use left/right eave heights from extractor (was raw_data.get('height'))
    left_eave  = safe_float(dims.get("left_eave_height_m"),  0.0)
    right_eave = safe_float(dims.get("right_eave_height_m"), left_eave)

    block_wall    = safe_float(dims.get("block_wall_m"), 3.0)
    ridge_dist    = safe_float(dims.get("ridge_line_distance_m"), round(width / 2, 3) if width else 0.0)
    roof_slope    = dims.get("roof_slope", "10/100")
    building_type = dims.get("building_type", "Clear Span" if width <= 30 else "Multi-Span")

    # ── Date Parsing (YYYYMMDD → dd-Mon-yy) ──────────────────────────────────
    raw_date_str = str(raw_data.get("raw_date", ""))
    parsed_date  = datetime.now().strftime("%d-%b-%y")
    if len(raw_date_str) == 8 and raw_date_str.isdigit():
        try:
            parsed_date = datetime.strptime(raw_date_str, "%Y%m%d").strftime("%d-%b-%y")
        except ValueError:
            pass

    # ── Proposal ID ───────────────────────────────────────────────────────────
    proposal_id = str(raw_data.get("proposal_id", "PROPOSAL")).strip()
    location    = str(raw_data.get("location", "Site")).strip()
    if not proposal_id or proposal_id in ("None", "FAILED"):
        proposal_id = "PROPOSAL"

    # ── Bay Calculations ──────────────────────────────────────────────────────
    num_side_bays, side_bay_str = calculate_bay_spacing_details(length, max_bay=8.0)
    num_end_bays,  end_bay_str  = calculate_bay_spacing_details(width,  max_bay=8.0)

    # ── Accessories (skylights/ventilators per bay rule) ─────────────────────
    per_bay = 2 if 15 <= width <= 30 else (4 if width > 30 else 0)
    total_skylights   = per_bay * num_side_bays
    total_ventilators = per_bay * num_side_bays

    # ── Loads ─────────────────────────────────────────────────────────────────
    design_code = raw_data.get("design_code", "AISC")  # FIX 3: default was "IS Code"
    dead_load   = safe_float(loads.get("dead_load_kn_m2"),   0.15 if design_code == "IS" else 0.1)
    live_load   = safe_float(loads.get("live_load_kn_m2"),   0.75 if design_code == "IS" else 0.57)
    coll_load   = safe_float(loads.get("collateral_load_kn_m2"), 0.0)
    wind_speed  = safe_float(loads.get("max_wind_speed_m_s"), 39)
    rainfall    = safe_float(loads.get("max_rainfall_mm_hr"), 150)
    exposure    = loads.get("exposure_category", "B")
    seismic     = safe_float(loads.get("seismic_zone_coefficient"), 0.16)
    temp_var    = safe_float(loads.get("max_temp_variation"), 20)

    # ── Openings ──────────────────────────────────────────────────────────────
    door_size = opens.get("door_size", "3x3")
    # FIX 4: Parse door height from "WxH" string for canopy calc
    door_height = 3.0  # default
    try:
        door_height = float(str(door_size).split("x")[1])
    except (IndexError, ValueError):
        pass

    # ── Canopy ────────────────────────────────────────────────────────────────
    canopy_present = canopy.get("present", False)
    canopy_ext     = safe_float(canopy.get("extension_m"), 0.0)
    # FIX 4: Spec says "Always 500mm above the door" — not eave_height - 1.0
    canopy_height  = round(door_height + 0.5, 3) if canopy_present else 0.0

    # ── Crane ─────────────────────────────────────────────────────────────────
    crane_count    = int(safe_float(crane.get("crane_count"), 0))
    crane_capacity = safe_float(crane.get("crane_capacity_kn"), 0.0)
    crane_top_ht   = safe_float(crane.get("crane_beam_top_height_m"), 0.0)

    # ── Mezzanine ─────────────────────────────────────────────────────────────
    mezz_present = mezz.get("present", False)
    mezz_height  = safe_float(mezz.get("top_of_floor_m"), 0.0)

    # ── Braced Bays ───────────────────────────────────────────────────────────
    braced_bays_count = 0
    if length > 0:
        braced_bays_count = max(2, math.ceil(length / 40.0) + 1)

    # ── Assemble output (flat dict for excel_filler) ──────────────────────────
    processed = {
        # Metadata
        "date":          parsed_date,
        "project":       str(raw_data.get("structure_application", "Industrial Facility")).strip(),
        "location":      location,
        "proposal_id":   proposal_id,
        "building_no":   int(raw_data.get("building_no", 1)),
        "option":        int(raw_data.get("option", 1)),
        "revision":      int(raw_data.get("revision", 0)),
        "design_software": raw_data.get("design_software", "MBS"),
        "design_code":   design_code,

        # Dimensions
        "area":          round(length * width, 2),
        "building_type": building_type,
        "length":        length,
        "width":         width,
        "left_height":   left_eave,
        "right_height":  right_eave,
        "ridge_dist":    ridge_dist,
        "roof_slope":    roof_slope,
        "block_wall":    block_wall,
        "end_bay":       end_bay_str,
        "side_bay":      side_bay_str,

        # Bracing & Sheeting
        "wall_bracing":  acc.get("wall_bracing_type", "Rod"),
        "roof_bracing":  acc.get("roof_bracing_type", "Rod"),
        "roof_sheeting": sheet.get("roof_sheeting", "0.45mm aluzinc"),
        "wall_sheeting": sheet.get("wall_sheeting",  "0.45mm aluzinc"),

        # Openings
        "doors":   door_size,
        "windows": opens.get("windows", "As required"),

        # Loads
        "dead_load":   dead_load,
        "live_load":   live_load,
        "collateral_load": coll_load,
        "wind_speed":  wind_speed,
        "rainfall":    rainfall,
        "exposure":    exposure,
        "seismic":     seismic,
        "temp_var":    temp_var,

        # Accessories
        "canopy_ext":        canopy_ext if canopy_present else 0,
        "canopy_height":     canopy_height,
        "braced_bays":       braced_bays_count,
        "skylights":         total_skylights,
        "turbo_ventilators": total_ventilators,

        # Crane
        "crane_count":    crane_count,
        "crane_capacity": crane_capacity,
        "crane_top_ht":   crane_top_ht,
        "crane_class":    crane.get("crane_class",  "II (Normal duty)"),
        "crane_type":     crane.get("crane_type",   "Top running"),
        "girder_type":    crane.get("girder_type",  "Single"),

        # Mezzanine
        "mezzanine_present": mezz_present,
        "mezzanine_height":  mezz_height,
        "mezzanine_length":  safe_float(mezz.get("length_m"), 0.0),
        "mezzanine_width":   safe_float(mezz.get("width_m"),  0.0),

        # Deflections
        "v_deflection": defl.get("frame_vertical",  "Span/150"),
        "h_deflection": defl.get("frame_horizontal", "Height/100"),
        "purlin_defl":  defl.get("purlins",          "Span/150"),
        "girt_defl":    defl.get("girts",            "Span/120"),

        # Material grades
        "hr_grade":           int(safe_float(mats.get("hot_rolled_mpa"),    250)),
        "cf_grade":           int(safe_float(mats.get("cold_form_mpa"),     350)),
        "primary_grade":      int(safe_float(mats.get("primary_section_mpa"), 350)),
        "min_web_thickness":  safe_float(mats.get("min_web_thickness_mm"),  4),
        "min_flange_thickness": safe_float(mats.get("min_flange_thickness_mm"), 5),
        "min_flange_width":   safe_float(mats.get("min_flange_width_mm"),   125),
        "min_web_depth":      safe_float(mats.get("min_web_depth_mm"),      250),
        "connection_bolts":   mats.get("connection_bolts", "High strength bolts (ASTM A325 or equivalent)"),

        "notes": raw_data.get("notes", ""),
    }

    return processed
import os
import json
import base64
import re
import pandas as pd
import pdfplumber
from google import genai
from PIL import Image 
import PIL.Image

class PEBExtractor:
    def __init__(self, api_key=None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
          raise ValueError("PEBExtractor: GEMINI_API_KEY is missing.")
          print("DEBUG: PEBExtractor missing GEMINI_API_KEY")
        
        # New SDK Client
        self.client = genai.Client(api_key=self.api_key)
        self.model_id = "gemini-2.5-flash"
        
        print(f"DEBUG: PEBExtractor initialized with {self.model_id} via new SDK")
        print("DEBUG API KEY PRESENT:", bool(self.api_key))

    def get_system_prompt(self):
        base_prompt = """
You are an expert Structural Engineering AI for Pre-Engineered Buildings (PEB) at Infiniti Structures.
Your task is to perform a DEEP INTENT ANALYSIS of client inquiries and extract precise engineering specifications.

═══════════════════════════════════════════════════════
PHASE 1: PROPOSAL ID CONSTRUCTION
═══════════════════════════════════════════════════════
- The Proposal ID is ALWAYS alphanumeric (e.g., Q-1516, C533-013, REF-2024-07).
- Found in email SUBJECT LINE or document REFERENCE NUMBER — not in the body text.
- The LOCATION is extracted separately from the document body (e.g., "Location: Palghar").
- COMBINE them as: <ProposalID>-<Location>
  Example: Subject "Q-1516" + Location "Palghar" → proposal_id = "Q-1516-Palghar"


═══════════════════════════════════════════════════════
PHASE 2: DATE EXTRACTION
═══════════════════════════════════════════════════════
- Extract received date from email/document header.
- Format as: YYYYMMDD (e.g., April 9 2026 → 20260409)
- If no date found, use today's date in YYYYMMDD format.

═══════════════════════════════════════════════════════
PHASE 3: UNIT CONVERSION — MANDATORY
═══════════════════════════════════════════════════════
ALL dimensions MUST be in METERS in the final output.
  - Feet to meters: value × 0.3048
  - Inches to meters: value × 0.0254
  - If already in meters: use as-is
Show conversion steps in reasoning before the JSON.

═══════════════════════════════════════════════════════
PHASE 4: HEIGHT LOGIC
═══════════════════════════════════════════════════════
Two height types:
  A) EAVE HEIGHT: Floor to top of eave (column top). Use directly.
  B) CLEAR HEIGHT: Usable interior clearance.
     Eave Height = Clear Height + 1m (rafter+ purlin) = Clear Height + 1m
     Example: 25 ft clear → 7.62m + 1m = 8.62m eave height

ALWAYS record:
  - "height_type_given": "clear" or "eave"
  - "left_eave_height_m": final eave height (left)
  - "right_eave_height_m": final eave height (right — same as left unless stated)

═══════════════════════════════════════════════════════
PHASE 5: AREA CALCULATION
═══════════════════════════════════════════════════════
  Area (sqm) = Length (m) × Width (m)  [make are area in whole number ,calculated area = 464.51  , consider it as 465 plan area only, NOT L×W×H] 

═══════════════════════════════════════════════════════
PHASE 6: STRUCTURAL APPLICATION
═══════════════════════════════════════════════════════
Extract purpose: Warehouse, Factory, Workshop, Office, Car Parking, Cold Storage, etc.
Infer from context if not explicitly stated.

═══════════════════════════════════════════════════════
PHASE 7: DEFAULTS — Apply ONLY when client has NOT specified
═══════════════════════════════════════════════════════
GENERAL:
  - design_code: "AISC" (use "IS" only if client specifically requests)
  - building_type: "Clear Span" (Multi-Span only if width > 31m)
  - building_no: 1, option: 1, revision: 0, design_software: "MBS"

LOADS:
  - dead_load_kn_m2: 0.1 (AISC), 0.15 (IS)
  - live_load_kn_m2: 0.57 (AISC), 0.75 (IS)
  - collateral_load_kn_m2: 0.0, max_wind_speed_m_s: 39
  - max_rainfall_mm_hr: 150, exposure_category: "B"
  - seismic_zone_coefficient: 0.16, max_temp_variation: 20

GEOMETRY:
  - roof_slope: "10/100"
  - ridge_line_distance_m: width_m / 2 (from backside wall)
  - wall_bracing_type: "Rod", roof_bracing_type: "Rod", block_wall_m: 3.0

SHEETING: roof_sheeting: "0.45mm aluzinc", wall_sheeting: "0.45mm aluzinc"
DOORS: door_size: "3x3"
ACCESSORIES: skylights/turbo_ventilators: 0
             braced bays: 0
CANOPY: present: false; slope: "10/100"; clear_top_height = door_height + 0.5m
MEZZANINE: present: false unless mentioned
CRANE: crane_count: 0; crane_class: "II (Normal duty)"; crane_type: "Top running"; girder_type: "Single"

MATERIAL GRADES:
  - hot_rolled_mpa: 250, cold_form_mpa: 350, primary_section_mpa: 350
  - min_web_thickness_mm: 4, min_flange_thickness_mm: 5
  - min_flange_width_mm: 125, min_web_depth_mm: 250, min_cold_form_thickness_mm: 1.5
  - connection_bolts: "High strength bolts (ASTM A325 or equivalent)"

DEFLECTION LIMITS:
  - frame_vertical: "Span/150", frame_horizontal: "Height/100"
  - purlins: "Span/150", girts: "Span/120"
  - crane_beams: "Span/600", mezzanine_beams: "Span/240"

═══════════════════════════════════════════════════════
PHASE 8: OUTPUT — STRICT JSON FORMAT
═══════════════════════════════════════════════════════
Return ONLY a valid JSON object. No prose, no markdown fences, no explanation outside the JSON.
All numeric fields must be numbers (not strings). Null fields use null (not the string "null").

{
  "proposal_id": "string",
  "raw_date": "YYYYMMDD",
  "location": "string",
  "structure_application": "string",
  "design_code": "AISC or IS",
  "design_software": "MBS",
  "building_no": 1,
  "option": 1,
  "revision": 0,

  "dimensions": {
    "length_m": 0.0,
    "width_m": 0.0,
    "left_eave_height_m": 0.0,
    "right_eave_height_m": 0.0,
    "height_type_given": "clear or eave",
    "area_sqm": 0.0,
    "roof_slope": "10/100",
    "ridge_line_distance_m": 0.0,
    "block_wall_m": 3.0,
    "building_type": "Clear Span or Multi-Span"
  },

  "loads": {
    "dead_load_kn_m2": 0.1,
    "live_load_kn_m2": 0.57,
    "collateral_load_kn_m2": 0.0,
    "max_wind_speed_m_s": 39,
    "max_rainfall_mm_hr": 150,
    "exposure_category": "B",
    "seismic_zone_coefficient": 0.16,
    "max_temp_variation": 20
  },

  "sheeting": {
    "roof_sheeting": "0.45mm aluzinc",
    "wall_sheeting": "0.45mm aluzinc",
    "full_height_cladding_sides": 0,
    "open_endwall": false
  },

  "openings": {
    "door_size": "3x3",
    "door_count": 1,
    "windows": null
  },

  "crane": {
    "crane_count": 0,
    "crane_capacity_kn": null,
    "crane_beam_top_height_m": null,
    "crane_span_m": null,
    "crane_running_length_m": null,
    "crane_class": "II (Normal duty)",
    "crane_type": "Top running",
    "girder_type": "Single"
  },

  "mezzanine": {
    "present": false,
    "location": null,
    "length_m": null,
    "width_m": null,
    "top_of_floor_m": null,
    "slab_depth_mm": null,
    "live_load_kn_m2": null,
    "dead_load_kn_m2": null,
    "collateral_load_kn_m2": null
  },

  "canopy": {
    "present": false,
    "extension_m": null,
    "slope": "10/100",
    "clear_top_height_m": null
  },

  "accessories": {
    "skylights": "string describing count/rule",
    "turbo_ventilators": "string describing count/rule",
    "braced_bays": "string describing bracing layout",
    "wall_bracing_type": "Rod",
    "roof_bracing_type": "Rod"
  },

  "material_grades": {
    "hot_rolled_mpa": 250,
    "cold_form_mpa": 350,
    "primary_section_mpa": 350,
    "connection_bolts": "High strength bolts (ASTM A325 or equivalent)",
    "min_web_thickness_mm": 4,
    "min_flange_thickness_mm": 5,
    "min_flange_width_mm": 125,
    "min_web_depth_mm": 250,
    "min_cold_form_thickness_mm": 1.5
  },

  "deflection_limits": {
    "frame_vertical": "Span/150",
    "frame_horizontal": "Height/100",
    "purlins": "Span/150",
    "girts": "Span/120",
    "crane_beams": "Span/600",
    "mezzanine_beams": "Span/240"
  },

  "notes": "Any additional remarks or ambiguities detected"
}
CRITICAL:
You MUST return ONLY valid JSON.
DO NOT include reasoning.
DO NOT include markdown.
DO NOT include explanations.
If you include anything other than JSON, the output will be rejected.
"""

        rules_text = ""
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            rules_path = os.path.join(current_dir, "golden_rules.txt")
            if os.path.exists(rules_path):
                with open(rules_path, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                if content:
                    rules_text = "\n\n═══════════════════════════════════════════════════════\n"
                    rules_text += "PHASE 9: TEAM GOLDEN RULES (CRITICAL OVERRIDES)\n"
                    rules_text += "═══════════════════════════════════════════════════════\n"
                    rules_text += "The following rules are mandatory overrides based on past feedback:\n"
                    rules_text += content + "\n"
        except Exception as e:
            print(f"DEBUG: Could not read golden_rules.txt: {e}")
            
        return base_prompt + rules_text

    def _strip_think_tags(self, text):
        """Gemini returns reasoning in <think> tags; remove before JSON parsing."""
        return re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()

    def _parse_json_response(self, text):
      try:
        clean_text = self._strip_think_tags(text)

        # 🔥 NEW FIX — remove markdown + junk before/after JSON
        clean_text = re.sub(r'```(?:json)?', '', clean_text)
        clean_text = clean_text.replace('```', '').strip()

        # 🔥 NEW FIX — extract ONLY first valid JSON block
        match = re.search(r'\{.*\}', clean_text, re.DOTALL)
        if not match:
            print("DEBUG: No JSON found in response")
            print(clean_text[:500])
            return None

        json_str = match.group(0)

        # 🔥 NEW FIX — remove trailing commas (very common LLM bug)
        json_str = re.sub(r',\s*}', '}', json_str)
        json_str = re.sub(r',\s*]', ']', json_str)
        return json.loads(json_str)
      except Exception as e:
        print(f"DEBUG: JSON parsing failed: {e}")
        return None
    def _generate_with_fallback(self, contents):
        """Helper to try primary model, then fallback on failure (e.g., High Demand)."""
        try:
            return self.client.models.generate_content(model=self.model_id, contents=contents)
        except Exception as primary_e:
            print(f"DEBUG: Primary model {self.model_id} failed: {primary_e}. Trying fallback 'gemini-1.5-flash'...")
            try:
                return self.client.models.generate_content(model="gemini-1.5-flash", contents=contents)
            except Exception as fallback_e:
                print(f"DEBUG: Fallback model also failed: {fallback_e}")
                raise fallback_e

    def extract_from_image(self, image_path):
      try:
        from PIL import Image
        image = Image.open(image_path)
        prompt = f"""
        {self.get_system_prompt()}
        CRITICAL:
        Return ONLY JSON.
        Analyze this PEB drawing/image and extract all details.
        """

        response = self._generate_with_fallback(contents=[prompt, image])

        full_response = response.text
        print("FULL GEMINI IMAGE RESPONSE:\n", full_response[:10000])

        return self._parse_json_response(full_response)

      except Exception as e:
        print(f"DEBUG: Image Error: {e}")
        return self.get_mock_data("image_error")

    def extract_from_pdf(self, pdf_path):
        if not self.api_key:
            return self.get_mock_data("no_api_key")
        try:
            full_text = ""
            with pdfplumber.open(pdf_path) as pdf:
                for i, page in enumerate(pdf.pages):
                    page_text = page.extract_text()
                    if page_text:
                        full_text += f"[Page {i + 1}]\n{page_text}\n"

            if not full_text.strip():
                print("DEBUG: PDF has no extractable text (scanned image PDF).")
                return self.get_mock_data("pdf_no_text")

            print(f"DEBUG: PDF extraction done. {len(full_text)} chars.")
            return self.extract_from_text(full_text)
        except Exception as e:
            print(f"DEBUG: PDF Extraction Error: {e}")
            return self.get_mock_data("pdf_error")

    def extract_from_excel(self, excel_path):
        if not self.api_key:
            return self.get_mock_data("no_api_key")
        try:
            df_dict = pd.read_excel(excel_path, sheet_name=None, header=None)
            combined_text = self._excel_to_structured_text(df_dict)
            print(f"DEBUG: Excel structured text: {len(combined_text)} chars.")
            return self.extract_from_text(combined_text)
        except Exception as e:
            print(f"DEBUG: Excel Extraction Error: {e}")
            return self.get_mock_data("excel_error")

    def _excel_to_structured_text(self, df_dict):
        """
        FIX 7 (CRITICAL): Original had 'return text' INSIDE the inner for-loop,
        so it returned after processing only the very first non-empty row.
        The model never saw 99% of the Excel content.
        Fixed: return is now after all loops complete.
        """
        text = "CLIENT INQUIRY DATA FROM EXCEL:\n"
        for sheet_name, df in df_dict.items():
            text += f"\n\n=== SHEET: {sheet_name} ===\n"
            for _, row in df.iterrows():
                values = [str(v).strip() for v in row if str(v).strip() not in ('nan', 'None', '')]
                if len(values) >= 2:
                    text += " | ".join(values) + "\n"
        return text  # FIX: was indented inside the inner loop in original code

    def extract_from_text(self, text):
      try:
        prompt = f"""
        {self.get_system_prompt()}
        CRITICAL:
              - Return ONLY valid JSON
              - No explanation
              - No markdown
              - No reasoning

        INPUT:
        {text}
        """
        response = self._generate_with_fallback(contents=prompt)
        full_response = response.text
        print("FULL GEMINI RESPONSE:\n", full_response[:10000])
        result = self._parse_json_response(full_response)

        if result is None:
            print("DEBUG: JSON parse failed")
            return self.get_mock_data("parse_failed")
        return result
      except Exception as e:
        print(f"DEBUG: Gemini Error: {e}")
        return self.get_mock_data("inference_error")

    def get_mock_data(self, source_type):
        """
        FIX 9: Updated mock data keys to match the nested JSON schema.
        Old keys (manual_id, length, width, height) no longer match what
        logic_engine expects, causing KeyError crashes downstream.
        """
        return {
            "proposal_id": "FAILED",
            "raw_date": "00000000",
            "location": "N/A",
            "structure_application": f"Extraction Failed: {source_type}",
            "design_code": "AISC",
            "design_software": "MBS",
            "building_no": 1,
            "option": 1,
            "revision": 0,
            "dimensions": {
                "length_m": 0.0, "width_m": 0.0,
                "left_eave_height_m": 0.0, "right_eave_height_m": 0.0,
                "height_type_given": "eave", "area_sqm": 0.0,
                "roof_slope": "10/100", "ridge_line_distance_m": 0.0,
                "block_wall_m": 3.0, "building_type": "Clear Span"
            },
            "loads": {
                "dead_load_kn_m2": 0.1, "live_load_kn_m2": 0.57,
                "collateral_load_kn_m2": 0.0, "max_wind_speed_m_s": 39,
                "max_rainfall_mm_hr": 150, "exposure_category": "B",
                "seismic_zone_coefficient": 0.16, "max_temp_variation": 20
            },
            "sheeting": {
                "roof_sheeting": "0.45mm aluzinc", "wall_sheeting": "0.45mm aluzinc",
                "full_height_cladding_sides": 0, "open_endwall": False
            },
            "openings": {"door_size": "3x3", "door_count": 1, "windows": None},
            "crane": {
                "crane_count": 0, "crane_capacity_kn": None, "crane_beam_top_height_m": None,
                "crane_span_m": None, "crane_running_length_m": None,
                "crane_class": "II (Normal duty)", "crane_type": "Top running", "girder_type": "Single"
            },
            "mezzanine": {
                "present": False, "location": None, "length_m": None, "width_m": None,
                "top_of_floor_m": None, "slab_depth_mm": None,
                "live_load_kn_m2": None, "dead_load_kn_m2": None, "collateral_load_kn_m2": None
            },
            "canopy": {"present": False, "extension_m": None, "slope": "10/100", "clear_top_height_m": None},
            "accessories": {
                "skylights": "2/bay", "turbo_ventilators": "2/bay",
                "braced_bays": "As per rule", "wall_bracing_type": "Rod", "roof_bracing_type": "Rod"
            },
            "material_grades": {
                "hot_rolled_mpa": 250, "cold_form_mpa": 350, "primary_section_mpa": 350,
                "connection_bolts": "High strength bolts (ASTM A325 or equivalent)",
                "min_web_thickness_mm": 4, "min_flange_thickness_mm": 5,
                "min_flange_width_mm": 125, "min_web_depth_mm": 250, "min_cold_form_thickness_mm": 1.5
            },
            "deflection_limits": {
                "frame_vertical": "Span/150", "frame_horizontal": "Height/100",
                "purlins": "Span/150", "girts": "Span/120",
                "crane_beams": "Span/600", "mezzanine_beams": "Span/240"
            },
            "notes": f"Extraction failed: {source_type}"
        }
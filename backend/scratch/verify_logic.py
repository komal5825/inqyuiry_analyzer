import math
import sys
import os

# Set up paths
backend_dir = r"c:\Users\User\Desktop\projectanti\inquire_anti\backend"
sys.path.append(backend_dir)

from logic_engine import process_specifications

def test_logic():
    print("--- Testing PEB Logic Enhancements ---")
    
    # Mock raw data from extractor
    raw_data = {
        "proposal_id": "Q-1234",
        "location": "",
        "dimensions": {
            "length_m": 60.96,
            "width_m": 30.48,
            "left_eave_height_m": 12.892,
            "block_wall_m": 2.54,
            "building_type": "Clear Span"
        },
        "accessories": {
            "skylights": "2/bay", # should be overridden to 0
            "turbo_ventilators": "2/bay", # should be overridden to 0
            "braced_bays": "4" # should be overridden to 0
        }
    }
    
    processed = process_specifications(raw_data)
    
    # 1. Area rounding (464.51 -> 465)
    area = processed['area']
    expected_area = math.ceil(60.96 * 30.48)
    print(f"Area: {area} (Expected: {expected_area})")
    assert area == expected_area
    
    # 2. Block wall rounding (2.54 -> 3)
    block_wall = processed['block_wall']
    print(f"Block Wall: {block_wall} (Expected: 3)")
    assert block_wall == 3
    
    # 3. Bay spacing rounding (30.48 / 4 = 7.62 -> 7.6)
    end_bay = processed['end_bay']
    print(f"End Bay: {end_bay} (Expected contains 7.6)")
    assert "7.6" in end_bay
    
    # 4. Multi-span logic (Width 30.48 <= 31 -> Clear Span)
    print(f"Building Type (30.48m): {processed['building_type']} (Expected: Clear Span)")
    assert processed['building_type'] == "Clear Span"
    
    # width > 31 test
    raw_data['dimensions']['width_m'] = 32.0
    processed_ms = process_specifications(raw_data)
    print(f"Building Type (32.0m): {processed_ms['building_type']} (Expected: Multi-Span)")
    assert processed_ms['building_type'] == "Multi-Span"
    
    # 5. Accessories forced to 0
    print(f"Skylights: {processed['skylights']} (Expected: 0)")
    print(f"Turbo Ventilators: {processed['turbo_ventilators']} (Expected: 0)")
    print(f"Braced Bays: {processed['braced_bays']} (Expected: 0)")
    assert processed['skylights'] == 0
    assert processed['turbo_ventilators'] == 0
    assert processed['braced_bays'] == 0
    
    # 6. Proposal ID logic
    print(f"Proposal ID: {processed['proposal_id']} (Expected: Q-1234)")
    assert processed['proposal_id'] == "Q-1234"
    assert processed['location'] == ""

    print("\n✅ Verification SUCCESS!")

if __name__ == "__main__":
    test_logic()

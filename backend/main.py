import sys
import os
from datetime import datetime

# Add current folder to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from extractor import PEBExtractor
    from logic_engine import process_specifications
    from excel_filler import fill_excel_template
except ImportError:
    from .extractor import PEBExtractor
    from .logic_engine import process_specifications
    from .excel_filler import fill_excel_template

# Path Configuration
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BASE_DIR)
TEMPLATE_PATH = os.path.join(ROOT_DIR, "Infiniti Specification.xlsx")

def main(input_file):
    print(f"--- Starting PEB Extraction Agent ---")
    
    if not os.path.exists(input_file):
        alt_path = os.path.join(ROOT_DIR, input_file)
        if os.path.exists(alt_path):
            input_file = alt_path
        else:
            print(f"Error: File {input_file} not found.")
            return

    api_key = os.getenv("GEMINI_API_KEY")
    extractor = PEBExtractor(api_key=api_key)
    
    print(f"Step 1: Extracting data from {input_file}...")
    if input_file.lower().endswith(('.png', '.jpg', '.jpeg')):
        raw_data = extractor.extract_from_image(input_file)
    else:
        with open(input_file, 'r') as f:
            text = f.read()
        raw_data = extractor.extract_from_text(text)
    
    raw_data['date'] = datetime.now().strftime("%d-%b-%y")
    
    print(f"Step 2: Applying PEB logic and defaults...")
    processed_data = process_specifications(raw_data)
    
    output = f"Agent_Final_Output_{processed_data['proposal_id']}.xlsx"
    output_path = os.path.join(BASE_DIR, "uploads", output)
    
    if not os.path.exists(os.path.join(BASE_DIR, "uploads")):
        os.makedirs(os.path.join(BASE_DIR, "uploads"))
    
    print(f"Step 3: Populating template...")
    final_file = fill_excel_template(TEMPLATE_PATH, output_path, processed_data)
    
    print(f"\nSUCCESS! Final specification ready: {final_file}")
    print(f"Proposal ID: {processed_data['proposal_id']}")

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT_DIR, "IMG_20260407_190835.jpg")
    main(target)

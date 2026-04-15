import os
import shutil
import uuid
import re
from fastapi import FastAPI, UploadFile, File, Form, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.orm import Session
from datetime import datetime
from dotenv import load_dotenv

try:
    from .database import SessionLocal, Inquiry
    from .extractor import PEBExtractor
    from .logic_engine import process_specifications
    from .excel_filler import fill_excel_template
except ImportError:
    import sys
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from database import SessionLocal, Inquiry
    from extractor import PEBExtractor
    from logic_engine import process_specifications
    from excel_filler import fill_excel_template

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BASE_DIR)
FRONTEND_DIR = os.path.join(ROOT_DIR, "frontend")
UPLOADS_DIR = os.path.join(BASE_DIR, "uploads")
TEMPLATE_PATH = os.path.join(ROOT_DIR, "Infiniti Specification.xlsx")

if not os.path.exists(UPLOADS_DIR):
    os.makedirs(UPLOADS_DIR)

load_dotenv(os.path.join(ROOT_DIR, ".env"))

app = FastAPI()
app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def sanitize_filename(name):
    return re.sub(r'[^\w\s-]', '', str(name)).strip().replace(' ', '_')


@app.get("/")
async def read_index():
    return FileResponse(os.path.join(FRONTEND_DIR, 'index.html'))


@app.post("/analyze")
async def analyze_inquiry(
    file: UploadFile = File(None),
    text: str = Form(None),
    db: Session = Depends(get_db)
):
    db_inquiry = Inquiry(status="Extracting")
    db.add(db_inquiry)
    db.commit()
    db.refresh(db_inquiry)

    # Switched back to Gemini for high-precision extraction
    api_key = os.getenv("GEMINI_API_KEY")
    print(f"DEBUG: Analyze requested. Gemini API Key Present: {bool(api_key)}")
    extractor = PEBExtractor(api_key=api_key)

    temp_path = None
    raw_data = {}

    if file and file.filename:
        ext = os.path.splitext(file.filename)[1].lower()
        temp_path = os.path.join(UPLOADS_DIR, f"temp_{uuid.uuid4().hex[:8]}{ext}")
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        if ext in ['.png', '.jpg', '.jpeg', '.webp']:
            raw_data = extractor.extract_from_image(temp_path)
        elif ext == '.pdf':
            raw_data = extractor.extract_from_pdf(temp_path)
        elif ext in ['.xlsx', '.xls']:
            raw_data = extractor.extract_from_excel(temp_path)
        elif ext == '.txt':
            with open(temp_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            raw_data = extractor.extract_from_text(content)
        else:
            raw_data = extractor.get_mock_data("unsupported_format")
    elif text:
        raw_data = extractor.extract_from_text(text)
    else:
        raw_data = extractor.get_mock_data("no_input")

    # Guard: ensure raw_data is a dict (model might return None on failure)
    if not isinstance(raw_data, dict):
        raw_data = extractor.get_mock_data("invalid_response")

    # Process through Logic Engine
    processed_data = process_specifications(raw_data)

    # Dynamic file renaming
    if file and file.filename and temp_path and os.path.exists(temp_path):
        project_sanitized  = sanitize_filename(processed_data.get('project', 'Project'))
        location_sanitized = sanitize_filename(processed_data.get('location', 'Site'))
        date_str = processed_data.get('date', datetime.now().strftime("%d-%b-%y"))
        ext = os.path.splitext(file.filename)[1]

        new_filename = f"{project_sanitized}_{location_sanitized}_{date_str}{ext}"
        final_path   = os.path.join(UPLOADS_DIR, new_filename)

        if os.path.exists(final_path):
            new_filename = f"{project_sanitized}_{location_sanitized}_{date_str}_{uuid.uuid4().hex[:4]}{ext}"
            final_path   = os.path.join(UPLOADS_DIR, new_filename)

        os.rename(temp_path, final_path)
        db_inquiry.filename = new_filename

    db_inquiry.raw_text      = text
    db_inquiry.extracted_data  = raw_data
    db_inquiry.processed_data  = processed_data
    db_inquiry.status          = "Ready"
    db.commit()

    return {
        "id": db_inquiry.id,
        "data": processed_data,
        "upload_feedback": {
            "name": db_inquiry.filename if file and file.filename else "Direct Inquiry",
            "type": file.content_type if file and file.filename else "text/plain"
        }
    }


@app.post("/generate/{inquiry_id}")
async def generate_excel(inquiry_id: int, verified_data: dict, db: Session = Depends(get_db)):
    inquiry = db.query(Inquiry).filter(Inquiry.id == inquiry_id).first()
    if not inquiry:
        raise HTTPException(status_code=404, detail="Inquiry not found")

    if not os.path.exists(TEMPLATE_PATH):
        raise HTTPException(status_code=500, detail=f"Template not found at {TEMPLATE_PATH}")

    project_name    = sanitize_filename(verified_data.get('project', 'Spec'))
    date_str        = verified_data.get('date', datetime.now().strftime("%d-%b-%y"))
    output_filename = f"Final_Spec_{project_name}_{date_str}.xlsx"
    output_path     = os.path.join(UPLOADS_DIR, output_filename)

    fill_excel_template(TEMPLATE_PATH, output_path, verified_data)

    return {"download_url": f"/download/{inquiry_id}/{output_filename}"}


@app.get("/download/{inquiry_id}/{filename}")
async def download_file(inquiry_id: int, filename: str):
    # Sanitize to prevent path traversal
    safe_filename = os.path.basename(filename)
    file_path = os.path.join(UPLOADS_DIR, safe_filename)
    if os.path.exists(file_path):
        return FileResponse(file_path, filename=safe_filename)
    raise HTTPException(status_code=404, detail="File not found")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
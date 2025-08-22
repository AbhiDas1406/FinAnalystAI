
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
import shutil
import os
import uuid
from utils.llmhandler import generate_code_from_query
from utils.pythonexecutor import run_generated_code
from utils.processdata import extract_csv_metadata_and_sample

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
UPLOAD_DIR = "uploaded_csvs"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.post("/analyze/")
async def analyze_csv(
    file: UploadFile = File(...),
    user_query: str = Form(...)
):
    # Save uploaded file
    file_id = str(uuid.uuid4())
    file_path = os.path.join(UPLOAD_DIR, f"{file_id}_{file.filename}")
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Extract CSV metadata and sample
    csv_info = extract_csv_metadata_and_sample(file_path)

    # Generate code from LLM
    code = generate_code_from_query(file_path, user_query)

    # Run the generated code and get flags
    output, error, flags = run_generated_code(code, file_path)

    response = {
        "metadata_and_sample": csv_info,
        "generated_code": code,
        "stdout": output,
        "stderr": error,
        "flags": flags
    }

    return JSONResponse(content=response)

@app.get("/get_image/")
async def get_image():
    image_path = "output.png"
    if os.path.exists(image_path):
        return FileResponse(image_path, media_type="image/png", filename="output.png")
    return JSONResponse(content={"error": "No image found"}, status_code=404)
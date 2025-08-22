
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
SESSION_DIR = "uploaded_csvs"
os.makedirs(SESSION_DIR, exist_ok=True)

@app.post("/upload/")
async def upload_csv(file: UploadFile = File(...)):
    session_id = str(uuid.uuid4())
    session_path = os.path.join(SESSION_DIR, session_id)
    os.makedirs(session_path, exist_ok=True)
    file_path = os.path.join(session_path, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    return {"session_id": session_id, "file_name": file.filename}

@app.post("/analyze/")
async def analyze_csv(
    session_id: str = Form(...),
    user_query: str = Form(...)
):
    # GET uploaded file
    session_path = os.path.join(SESSION_DIR, session_id)
    files = os.listdir(session_path) if os.path.exists(session_path) else []
    if not files:
        return JSONResponse(content={"error": "No file found for session"}, status_code=404)
    file_path = os.path.join(session_path, files[0])

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

@app.post("/clear_session/")
async def clear_session(session_id: str = Form(...)):
    session_path = os.path.join(SESSION_DIR, session_id)
    if os.path.exists(session_path):
        shutil.rmtree(session_path)
    return JSONResponse(content={"status": "session cleared"})


@app.get("/get_image/")
async def get_image():
    image_path = "output.png"
    if os.path.exists(image_path):
        return FileResponse(image_path, media_type="image/png", filename="output.png")
    return JSONResponse(content={"error": "No image found"}, status_code=404)
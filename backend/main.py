from fastapi import FastAPI, UploadFile, File, Form, Query
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
import os
import uuid
import boto3
from utils.llmhandler import generate_code_from_query
from utils.pythonexecutor import run_generated_code
from utils.processdata import extract_csv_metadata_and_sample

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For production, restrict to your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

S3_BUCKET = os.environ["S3_BUCKET_NAME"]
s3 = boto3.client("s3")

@app.post("/upload/")
async def upload_csv(file: UploadFile = File(...)):
    session_id = str(uuid.uuid4())
    s3_key = f"sessions/{session_id}/{file.filename}"
    s3.upload_fileobj(file.file, S3_BUCKET, s3_key)
    return {"session_id": session_id, "file_name": file.filename}

@app.post("/analyze/")
async def analyze_csv(
    session_id: str = Form(...),
    user_query: str = Form(...)
):
    prefix = f"sessions/{session_id}/"
    response = s3.list_objects_v2(Bucket=S3_BUCKET, Prefix=prefix)
    files = response.get("Contents", [])
    if not files:
        return JSONResponse(content={"error": "No file found for session"}, status_code=404)
    s3_key = files[0]["Key"]

    # Download file to /tmp for processing
    local_path = "/tmp/" + os.path.basename(s3_key)
    s3.download_file(S3_BUCKET, s3_key, local_path)

    # Extract CSV metadata and sample
    csv_info = extract_csv_metadata_and_sample(local_path)

    # Generate code from LLM
    code = generate_code_from_query(local_path, user_query)

    # Run the generated code and get flags
    output, error, flags = run_generated_code(code, local_path)

    # If an image was generated, upload it to S3 (overwrite previous)
    image_path = "output.png"
    image_s3_key = f"sessions/{session_id}/output.png"
    if os.path.exists(image_path):
        s3.upload_file(image_path, S3_BUCKET, image_s3_key)

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
    prefix = f"sessions/{session_id}/"
    response = s3.list_objects_v2(Bucket=S3_BUCKET, Prefix=prefix)
    files = response.get("Contents", [])
    for obj in files:
        s3.delete_object(Bucket=S3_BUCKET, Key=obj["Key"])
    return JSONResponse(content={"status": "session cleared"})

@app.get("/get_image/")
async def get_image(session_id: str = Query(...)):
    image_s3_key = f"sessions/{session_id}/output.png"
    local_path = f"/tmp/output_{session_id}.png"
    try:
        s3.download_file(S3_BUCKET, image_s3_key, local_path)
        return FileResponse(local_path, media_type="image/png", filename="output.png")
    except Exception:
        return JSONResponse(content={"error": "No image found"}, status_code=404)
from fastapi import FastAPI, UploadFile, File, Form, Query
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
import os
import uuid
import boto3
from utils.llmhandler import generate_code_from_query
from utils.pythonexecutor import run_generated_code
from utils.processdata import extract_csv_metadata_and_sample
from datetime import datetime

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
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    image_s3_key = f"sessions/{session_id}/output_{timestamp}.png"
    image_url = None
    if os.path.exists(image_path):
        s3.upload_file(image_path, S3_BUCKET, image_s3_key)
        image_url = image_s3_key # Save the S3 key for frontend to fetch

    response = {
        "metadata_and_sample": csv_info,
        "generated_code": code,
        "stdout": output,
        "stderr": error,
        "flags": flags,
        "image_key": image_url,  # Pass this to frontend
        "image_timestamp": timestamp if image_url else None
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
async def get_image(session_id: str = Query(...), timestamp: str = Query(...)):
    image_s3_key = f"sessions/{session_id}/output_{timestamp}.png"
    local_path = f"/tmp/output_{session_id}_{timestamp}.png"
    try:
        s3.download_file(S3_BUCKET, image_s3_key, local_path)
        return FileResponse(local_path, media_type="image/png", filename=f"output_{timestamp}.png")
    except Exception:
        return JSONResponse(content={"error": "No image found"}, status_code=404)
    

# Optional: Background task to clean up old sessions
# Uncomment the following code to enable automatic cleanup of old sessions
# import threading
# import time
# from datetime import datetime, timezone, timedelta

# SESSION_TIMEOUT_HOURS = 1  # Change to 24 for 1 day

# def cleanup_old_sessions():
#     while True:
#         try:
#             response = s3.list_objects_v2(Bucket=S3_BUCKET, Prefix="sessions/")
#             now = datetime.now(timezone.utc)
#             for obj in response.get("Contents", []):
#                 last_modified = obj["LastModified"]
#                 if (now - last_modified) > timedelta(hours=SESSION_TIMEOUT_HOURS):
#                     s3.delete_object(Bucket=S3_BUCKET, Key=obj["Key"])
#                     print(f"Deleted old session file: {obj['Key']}")
#         except Exception as e:
#             print(f"Cleanup error: {e}")
#         time.sleep(3600)  # Run every hour

# # Start the cleanup thread when the app starts
# threading.Thread(target=cleanup_old_sessions, daemon=True).start()
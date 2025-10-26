from flask import Flask, request, jsonify, render_template

## Add required imports
from azure.storage.blob import BlobServiceClient, PublicAccess, ContentSettings
from datetime import datetime
from dotenv import load_dotenv
import os
from pathlib import Path
import requests
from werkzeug.utils import secure_filename

# load_dotenv()

AZURE_CONNECTION_STRING=os.getenv("AZURE_CONNECTION_STRING")
STORAGE_ACCOUNT_URL=os.getenv("STORAGE_ACCOUNT_URL")
CONTAINER_NAME = "lanternfly-images"

bsc = BlobServiceClient.from_connection_string(AZURE_CONNECTION_STRING)
cc  = bsc.get_container_client(CONTAINER_NAME)
app = Flask(__name__)
cc.set_container_access_policy(public_access='container', signed_identifiers={})




@app.post("/api/v1/upload")
def upload():
    ALLOWED_IMAGE_TYPES = {"image/png", "image/jpeg", "image/jpg", "image/gif", "image/webp"}
    MAX_FILE_SIZE_MB = 10
    f = request.files["file"]
    filename = f.filename

    if "file" not in request.files:
        return jsonify(ok=False, error="No file uploaded"), 400
    
    if f.filename == "":
        return jsonify(ok=False, error="Empty filename"), 400
    
    if f.mimetype not in ALLOWED_IMAGE_TYPES:
        return jsonify(ok=False, error="Invalid file type. Only image files are allowed."), 400

    f.seek(0, os.SEEK_END)
    size_mb = f.tell() / (1024 * 1024)
    f.seek(0)
    if size_mb > MAX_FILE_SIZE_MB:
        return jsonify(ok=False, error="File exceeds 10 MB limit"), 400

    safe_name = secure_filename(f.filename)
    timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%S")
    blob_name = f"{timestamp}-{safe_name}"

    try:
        blob_client = cc.get_blob_client(blob_name)
        blob_client.upload_blob(
            f,
            overwrite=True,
            content_settings=ContentSettings(content_type=f.mimetype)
        )
        return jsonify(ok=True, url=f"{cc.url}/{f.filename}"), 200
    except Exception as e:
        return jsonify(ok=False, error=str(e)), 500

## Add other API end points. (/api/v1/gallery)  and (/api/v1/health)

@app.get("/api/v1/gallery")
def gallery():
    blob_list = cc.list_blobs()
    gallery_urls = [f"{cc.url}/{blob.name}" for blob in blob_list]
    request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html
    return jsonify(ok=True, gallery=gallery_urls), 200

@app.get("/api/v1/health")
def health():
    try:
        _ = cc.get_container_properties()
        return jsonify(ok=True, status="healthy", container=CONTAINER_NAME), 200
    except Exception as e:
        return jsonify(ok=False, status="unhealthy", error=str(e)), 500

@app.get("/")
def index():
    return render_template("index.html")

if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=True)
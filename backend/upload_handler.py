import os
import shutil
from fastapi import UploadFile

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

async def save_upload_file(upload_file: UploadFile) -> str:
    """Saves an uploaded image file to the temporary upload directory."""
    file_location = os.path.join(UPLOAD_DIR, upload_file.filename)
    with open(file_location, "wb+") as file_object:
        shutil.copyfileobj(upload_file.file, file_object)
    return file_location

import asyncio
import logging
import cv2
import numpy as np
import time
import json
import socket
import threading
from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse, FileResponse
from typing import Optional
import os

class BBox(BaseModel):
    x: int
    y: int
    w: int
    h: int

class TransformParams(BaseModel):
    scale: float = 1.0
    rotation: float = 0.0
    x_offset: float = 0.0
    y_offset: float = 0.0

class PrintOptions(BaseModel):
    file_path: str = None
    transform: TransformParams = None

class SelectDesignRequest(BaseModel):
    type: str = "single"
    filename: Optional[str] = None
    set_data: Optional[dict] = None

class SetFingers(BaseModel):
    Thumb: str
    Index: str
    Middle: str
    Ring: str
    Pinky: str

class DesignSet(BaseModel):
    name: str
    fingers: SetFingers

from upload_handler import save_upload_file
from serial_comm import SerialManager
from cv_pipeline import run_pipeline

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Nail Printer Backend")

# Allow CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

serial_manager = SerialManager(mock=True)

class CameraManager:
    def __init__(self):
        self.cap = None
        self.lock = threading.Lock()

    def get_frame(self):
        with self.lock:
            if self.cap is None or not self.cap.isOpened():
                # Index 1 is usually the external/Continuity camera on Mac
                self.cap = cv2.VideoCapture(1)
                time.sleep(0.5) # warmup
            success, frame = self.cap.read()
            if not success:
                return None
            return frame

    def release(self):
        if self.cap is not None:
            self.cap.release()
            self.cap = None

camera_manager = CameraManager()

# Global state
app.state.last_uploaded_file = None
app.state.last_alignment = None
app.state.active_type = "single"
app.state.active_set = None

SETS_FILE = "sets.json"

def load_sets():
    if os.path.exists(SETS_FILE):
        with open(SETS_FILE, 'r') as f:
            return json.load(f)
    return []

def save_sets(sets_data):
    with open(SETS_FILE, 'w') as f:
        json.dump(sets_data, f)

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP

@app.get("/api/system/ip")
async def get_ip():
    return {"ip": get_local_ip()}

@app.post("/api/upload")
async def upload_image(file: UploadFile = File(...)):
    if not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="File must be an image.")
    
    file_path = await save_upload_file(file)
    app.state.last_uploaded_file = file_path
    logger.info(f"Image saved to {file_path}")
    return JSONResponse(content={"message": "Upload successful", "file_path": file_path})

@app.get("/api/design")
async def get_latest_design():
    if app.state.last_uploaded_file and os.path.exists(app.state.last_uploaded_file):
        return FileResponse(app.state.last_uploaded_file)
    else:
        raise HTTPException(status_code=404, detail="No design uploaded yet")

@app.get("/api/designs")
async def list_designs():
    upload_dir = "uploads"
    if not os.path.exists(upload_dir):
        return []
    files = [f for f in os.listdir(upload_dir) if os.path.isfile(os.path.join(upload_dir, f))]
    # Return newest first
    files.sort(key=lambda x: os.path.getmtime(os.path.join(upload_dir, x)), reverse=True)
    return [{"filename": f, "url": f"/uploads/{f}"} for f in files if f.lower().endswith(('.png', '.jpg', '.jpeg'))]

@app.post("/api/designs/select")
async def select_design(req: SelectDesignRequest):
    if req.type == "single":
        if not req.filename:
            raise HTTPException(status_code=400, detail="Filename required")
        file_path = os.path.join("uploads", req.filename)
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="File not found")
        app.state.last_uploaded_file = file_path
        app.state.active_type = "single"
        app.state.active_set = None
        logger.info(f"Active single design set to {file_path}")
    elif req.type == "set":
        if not req.set_data:
            raise HTTPException(status_code=400, detail="Set data required")
        app.state.active_type = "set"
        app.state.active_set = req.set_data
        # Initialize first finger? We don't need to track current finger on backend, frontend does that.
        logger.info(f"Active design set configured to: {req.set_data['name']}")
    return {"message": "Design selected"}

@app.get("/api/designs/active")
async def get_active_design():
    if app.state.active_type == "single":
        filename = os.path.basename(app.state.last_uploaded_file) if app.state.last_uploaded_file else None
        return {"type": "single", "filename": filename, "url": f"/uploads/{filename}" if filename else None}
    else:
        return {"type": "set", "set": app.state.active_set}

@app.get("/api/sets")
async def get_sets():
    return load_sets()

@app.post("/api/sets")
async def create_set(design_set: DesignSet):
    sets = load_sets()
    new_set = design_set.dict()
    sets.insert(0, new_set) # Add to beginning
    save_sets(sets)
    return {"message": "Set saved successfully"}

def gen_frames():
    while True:
        frame = camera_manager.get_frame()
        if frame is not None:
            ret, buffer = cv2.imencode('.jpg', frame)
            frame_bytes = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        time.sleep(0.05)

@app.get("/api/stream")
def video_stream():
    return StreamingResponse(gen_frames(), media_type="multipart/x-mixed-replace; boundary=frame")

@app.post("/api/home")
async def home_printer():
    logger.info("Homing printer requested.")
    await serial_manager.home()
    return {"message": "Homing sequence started"}

@app.post("/api/align")
async def align_printer(bbox: BBox):
    logger.info(f"Manual align requested with bbox: {bbox}")
    app.state.last_alignment = bbox.dict()
    return {"message": "Alignment coordinates saved successfully", "bbox": bbox.dict()}

@app.post("/api/print")
async def start_print_job(options: PrintOptions = None):
    if options is None:
        options = PrintOptions()
        
    target_file = options.file_path or app.state.last_uploaded_file
    if not target_file:
        raise HTTPException(status_code=400, detail="No file provided and no previous upload found.")

    logger.info(f"Starting print job for {target_file}")
    try:
        # Run CV Pipeline
        transform_dict = options.transform.dict() if options.transform else None
        packets = run_pipeline(target_file, app.state.last_alignment, transform_dict)
        
        # Communicate with hardware
        await serial_manager.start_print()
        for packet in packets:
            success = await serial_manager.send_line(packet)
            if not success:
                logger.error("Failed to send line to hardware.")
                raise HTTPException(status_code=500, detail="Hardware communication failed.")
                
        logger.info("Print job completed successfully.")
        return {"message": "Print job started successfully"}
    except Exception as e:
        logger.error(f"Print job failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Mount uploads directory
if os.path.exists("uploads"):
    app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# Mount static files for the frontend (Vue build output)
import os
frontend_dist = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")
if os.path.exists(frontend_dist):
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")
else:
    logger.warning("Frontend dist directory not found. UI will not be served.")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

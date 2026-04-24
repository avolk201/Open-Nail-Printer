import asyncio
import logging
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .upload_handler import save_upload_file
from .serial_comm import SerialManager
from .cv_pipeline import run_pipeline

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

@app.post("/api/upload")
async def upload_image(file: UploadFile = File(...)):
    if not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="File must be an image.")
    
    file_path = await save_upload_file(file)
    logger.info(f"Image saved to {file_path}")
    return JSONResponse(content={"message": "Upload successful", "file_path": file_path})

@app.post("/api/print")
async def start_print_job(file_path: str):
    logger.info(f"Starting print job for {file_path}")
    try:
        # Run CV Pipeline
        packets = run_pipeline(file_path)
        
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

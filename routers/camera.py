import os
import shutil
import logging
from datetime import datetime
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from db.database import save_camera_image, get_latest_camera_image

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

router = APIRouter()

# Define base directory for image storage with support for Render persistent disk
RENDER_DISK_BASE = "/var/lib/data"

# Check if running on Render with persistent disk
if os.path.exists(RENDER_DISK_BASE):
    UPLOAD_DIR = os.path.join(RENDER_DISK_BASE, "images")
    logger.info(f"[STORAGE] Running in cloud. Using Render persistent disk: {UPLOAD_DIR}")
else:
    # Fallback to local storage
    UPLOAD_DIR = os.path.join(os.getcwd(), "static", "images")
    logger.info(f"[STORAGE] Running locally. Using local directory: {UPLOAD_DIR}")

# Ensure the upload directory exists
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/upload-image")
async def upload_image(
    file: UploadFile = File(...),
    yolo_result: str = Form(None)
):
    """
    Handle image upload from ESP32-Cam or similar IoT device.
    
    Parameters:
    - file: JPEG image file
    - yolo_result: Optional YOLO classification result as JSON string
    
    Returns:
    - status: 'success' or error message
    - image_url: Path to access the image
    - filename: Stored filename
    """
    try:
        # Ensure upload directory exists
        if not os.path.exists(UPLOAD_DIR):
            os.makedirs(UPLOAD_DIR, exist_ok=True)
            logger.info(f"[CAMERA] Created missing directory: {UPLOAD_DIR}")

        # Generate unique filename with millisecond precision to prevent collisions
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:19]
        extension = file.filename.split(".")[-1] if "." in file.filename else "jpg"
        filename = f"{timestamp}.{extension}"
        file_path = os.path.join(UPLOAD_DIR, filename)

        # Write file to disk
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Construct relative URL for frontend access
        image_url = f"/static/images/{filename}"
        storage_type = "render_disk" if os.path.exists(RENDER_DISK_BASE) else "local"

        # Save metadata to database
        save_camera_image(
            image_url=image_url,
            storage_type=storage_type,
            yolo_result=yolo_result
        )

        logger.info(f"[CAMERA] Image uploaded successfully: {filename} ({storage_type})")
        
        return {
            "status": "success",
            "image_url": image_url,
            "filename": filename,
            "storage_type": storage_type
        }

    except Exception as e:
        logger.error(f"[CAMERA] Upload failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Image upload failed: {str(e)}"
        )

@router.post("/upload")
async def upload_image_legacy(
    file: UploadFile = File(...),
    yolo_result: str = Form(None)
):
    """
    Legacy endpoint for backward compatibility.
    Redirects to the new /upload-image endpoint.
    """
    return await upload_image(file=file, yolo_result=yolo_result)

@router.get("/latest")
async def get_latest_image():
    """
    Retrieve the latest camera image metadata and URL.
    
    Returns:
    - status: 'success', 'empty', or error
    - data: Image metadata including URL, YOLO result, capture time
    """
    try:
        image_data = get_latest_camera_image()
        
        if not image_data:
            logger.warning("[CAMERA] No images found in database")
            return {
                "status": "empty",
                "message": "No images found in the database.",
                "data": None
            }

        return {
            "status": "success",
            "data": {
                "id": image_data["id"],
                "image_url": image_data["image_url"],
                "storage_type": image_data["storage_type"],
                "captured_at": image_data["captured_at"],
                "yolo_result": image_data["yolo_result"],
                "note": image_data["note"]
            }
        }

    except Exception as e:
        logger.error(f"[CAMERA] Failed to retrieve latest image: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve the latest image."
        )

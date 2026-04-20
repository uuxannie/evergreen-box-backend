import os
import shutil
import glob
import json
import logging
from datetime import datetime
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from backend.db.database import save_camera_image, get_latest_camera_image
from backend.services.timelapse_service import enforce_image_cap, generate_timelapse_video

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
    Handle image upload from USB webcam connected to macbook.
    Enforces a hard cap of 500 images; older images are deleted FIFO.
    
    Parameters:
    - file: JPEG image file captured from USB webcam
    - yolo_result: Optional YOLO classification result as JSON string
    
    Returns:
    - status: 'success' or error message
    - image_url: Path to access the image
    - filename: Stored filename
    - image_count: Current number of images stored (max 500)
    """
    try:
        # Ensure upload directory exists
        if not os.path.exists(UPLOAD_DIR):
            os.makedirs(UPLOAD_DIR, exist_ok=True)
            logger.info(f"[CAMERA] Created missing directory: {UPLOAD_DIR}")

        # Enforce the 500 image hard cap before saving new image
        enforce_image_cap()

        # Generate unique filename with millisecond precision to prevent collisions
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:19]
        extension = file.filename.split(".")[-1] if file.filename and "." in file.filename else "jpg"
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

        # Count current images in directory
        image_count = len(glob.glob(os.path.join(UPLOAD_DIR, "*.jpg")))
        image_count += len(glob.glob(os.path.join(UPLOAD_DIR, "*.jpeg")))

        logger.info(f"[CAMERA] Image uploaded successfully: {filename} ({storage_type}). Total: {image_count}/500")
        
        return {
            "status": "success",
            "image_url": image_url,
            "filename": filename,
            "storage_type": storage_type,
            "image_count": image_count
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

@router.get("/detection")
async def get_latest_detection():
    """
    Retrieve the latest camera image's parsed YOLO detection result.
    Extracts plant type, confidence, and health status from stored YOLO result.
    
    Returns:
    - status: 'success', 'empty', or error
    - data: Parsed detection data
        - plant_type: Detected plant species (e.g., "pothos")
        - confidence: Detection confidence as percentage string (e.g., "95%")
        - health_status: Plant health status (e.g., "Healthy", "Yellowing", "Rot Risk")
        - disease_class: Disease classification if any (e.g., "Healthy", "Leaf Spot")
        - recommendation: Care recommendation based on detection
        - captured_at: When the image was captured
    """
    try:
        image_data = get_latest_camera_image()
        
        if not image_data or not image_data.get("yolo_result"):
            logger.warning("[CAMERA] No YOLO results found")
            return {
                "status": "empty",
                "message": "No detection results available yet.",
                "data": {
                    "plant_type": "Unknown",
                    "confidence": "0%",
                    "health_status": "Monitoring...",
                    "disease_class": "Unknown",
                    "recommendation": "Waiting for first detection...",
                    "captured_at": None
                }
            }
        
        # Parse YOLO result from JSON string
        try:
            yolo_data = json.loads(image_data["yolo_result"])
        except (json.JSONDecodeError, TypeError):
            logger.warning("[CAMERA] Invalid YOLO JSON format, returning defaults")
            yolo_data = {}
        
        # Extract detection data with safe fallbacks
        plant_type = yolo_data.get("plant", "Unknown")
        confidence = yolo_data.get("confidence", 0)
        disease_class = yolo_data.get("disease", "Healthy")
        
        # Convert confidence to percentage if it's a decimal
        if isinstance(confidence, float) and confidence <= 1.0:
            confidence_str = f"{int(confidence * 100)}%"
        else:
            confidence_str = f"{int(confidence)}%"
        
        # Map disease class to health status
        health_status_map = {
            "Healthy": "Healthy",
            "Yellowing": "Warning",
            "Dark-spot": "Alert",
            "Rot Risk": "Alert",
            "Leaf Spot": "Alert"
        }
        health_status = health_status_map.get(disease_class, "Monitoring")
        
        # Generate recommendation based on disease
        recommendation_map = {
            "Healthy": "No action needed",
            "Yellowing": "Check watering conditions and adjust if needed",
            "Dark-spot": "Reduce watering and improve ventilation",
            "Rot Risk": "Reduce watering immediately and improve air circulation",
            "Leaf Spot": "Isolate plant and reduce leaf moisture"
        }
        recommendation = recommendation_map.get(disease_class, "Continue monitoring")
        
        return {
            "status": "success",
            "data": {
                "plant_type": plant_type.lower() if plant_type != "Unknown" else "Unknown",
                "confidence": confidence_str,
                "health_status": health_status,
                "disease_class": disease_class,
                "recommendation": recommendation,
                "captured_at": image_data.get("captured_at")
            }
        }

    except Exception as e:
        logger.error(f"[CAMERA] Failed to parse detection result: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve detection results."
        )

@router.post("/generate-demo-video")
async def generate_demo_video():
    """
    Manually trigger timelapse video generation from all available images captured by USB webcam.
    For demo mode, compiles all images (capped at 500) into a 30 FPS MP4.
    
    Returns:
    - success: Boolean indicating whether generation succeeded
    - video_path: Full path to the generated video file
    - video_url: Relative URL to access the video via /static/videos
    - frame_count: Number of frames compiled into the video
    - skipped_frames: Number of images that could not be read
    - file_size_mb: Size of the generated video in megabytes
    - error: Error message if generation failed
    """
    try:
        logger.info("[CAMERA] Demo video generation requested...")
        result = generate_timelapse_video()
        
        if result["success"]:
            logger.info(f"[CAMERA] Demo video generated successfully: {result['video_path']}")
            return result
        else:
            logger.warning(f"[CAMERA] Demo video generation failed: {result['error']}")
            return result
            
    except Exception as e:
        logger.error(f"[CAMERA] Error during video generation: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": f"Video generation failed: {str(e)}"
        }

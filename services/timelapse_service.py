import os
import time
import logging
from datetime import datetime
import cv2
import glob
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Define base paths with support for Render persistent disk
RENDER_DISK_BASE = "/var/lib/data"
MAX_IMAGES = 500  # Hard cap for demo version

def get_storage_paths():
    """
    Determine storage paths based on deployment environment.
    Returns a tuple of (IMAGE_DIR, VIDEO_DIR, STORAGE_TYPE)
    """
    if os.path.exists(RENDER_DISK_BASE):
        image_dir = os.path.join(RENDER_DISK_BASE, "images")
        video_dir = os.path.join(RENDER_DISK_BASE, "videos")
        storage_type = "render_disk"
        logger.info(f"[STORAGE] Running in cloud. Using Render persistent disk: {RENDER_DISK_BASE}")
    else:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        image_dir = os.path.join(base_dir, "static", "images")
        video_dir = os.path.join(base_dir, "static", "videos")
        storage_type = "local"
        logger.info(f"[STORAGE] Running locally. Using static directories.")
    
    # Ensure directories exist
    Path(image_dir).mkdir(parents=True, exist_ok=True)
    Path(video_dir).mkdir(parents=True, exist_ok=True)
    
    return image_dir, video_dir, storage_type

IMAGE_DIR, VIDEO_DIR, STORAGE_TYPE = get_storage_paths()

def enforce_image_cap():
    """
    Enforce hard cap on image count (500 images max).
    If the limit is exceeded, delete the oldest images (FIFO) until count is at MAX_IMAGES - 1.
    
    This function should be called BEFORE saving a new image.
    """
    try:
        # Collect all image files
        image_files = glob.glob(os.path.join(IMAGE_DIR, "*.jpg"))
        image_files.extend(glob.glob(os.path.join(IMAGE_DIR, "*.jpeg")))
        
        current_count = len(image_files)
        
        if current_count >= MAX_IMAGES:
            logger.info(f"[CAP_ENFORCEMENT] Image count ({current_count}) reached limit. Deleting oldest images...")
            
            # Sort by modification time to get oldest first
            image_files.sort(key=lambda x: os.path.getmtime(x))
            
            # Delete until we have MAX_IMAGES - 1 remaining
            images_to_delete = current_count - (MAX_IMAGES - 1)
            deleted_count = 0
            
            for img_path in image_files[:images_to_delete]:
                try:
                    os.remove(img_path)
                    deleted_count += 1
                    logger.info(f"[CAP_ENFORCEMENT] Deleted oldest image: {os.path.basename(img_path)}")
                except OSError as e:
                    logger.warning(f"[CAP_ENFORCEMENT] Failed to delete {img_path}: {e}")
            
            logger.info(f"[CAP_ENFORCEMENT] Freed space by deleting {deleted_count} images.")
    
    except Exception as e:
        logger.error(f"[CAP_ENFORCEMENT] Error enforcing image cap: {e}", exc_info=True)

def generate_timelapse_video():
    """
    Generate an MP4 timelapse video from all available images in the directory.
    
    For demo mode, this reads all currently stored images (capped at 500),
    sorts them chronologically, and compiles them into an H.264 MP4 (30 FPS).
    
    Returns:
        dict: {"success": True, "video_path": "...", "frame_count": N} or 
              {"success": False, "error": "..."}
    """
    try:
        # Collect all image files
        all_images = glob.glob(os.path.join(IMAGE_DIR, "*.jpg"))
        all_images.extend(glob.glob(os.path.join(IMAGE_DIR, "*.jpeg")))
        
        if not all_images:
            logger.warning("[TIMELAPSE] No images found in IMAGE_DIR.")
            return {"success": False, "error": "No images available"}
        
        # Sort images chronologically by filename (timestamp-based naming)
        all_images.sort()
        logger.info(f"[TIMELAPSE] Found {len(all_images)} images for video generation.")
        
        # Read the first image to determine dimensions
        first_frame = cv2.imread(all_images[0])
        if first_frame is None:
            logger.error(f"[TIMELAPSE] Failed to read first image: {all_images[0]}")
            return {"success": False, "error": "Cannot read first image"}
        
        height, width = first_frame.shape[:2]
        size = (width, height)
        logger.info(f"[TIMELAPSE] Video dimensions: {width}x{height}")
        
        # Generate output filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = os.path.join(VIDEO_DIR, f"timelapse_{timestamp}.mp4")
        
        # Initialize VideoWriter with H.264 codec
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        fps = 30.0
        
        out = cv2.VideoWriter(output_path, fourcc, fps, size)
        
        if not out.isOpened():
            logger.error("[TIMELAPSE] VideoWriter failed to open.")
            return {"success": False, "error": "VideoWriter initialization failed"}
        
        # Write frames to video
        frame_count = 0
        failed_frames = 0
        
        for img_path in all_images:
            try:
                frame = cv2.imread(img_path)
                if frame is None:
                    logger.warning(f"[TIMELAPSE] Skipped unreadable frame: {os.path.basename(img_path)}")
                    failed_frames += 1
                    continue
                
                # Resize frame if dimensions don't match
                if frame.shape[:2] != (height, width):
                    frame = cv2.resize(frame, size)
                
                out.write(frame)
                frame_count += 1
                
            except Exception as e:
                logger.warning(f"[TIMELAPSE] Error processing frame {img_path}: {e}")
                failed_frames += 1
        
        # Release VideoWriter and clean up
        out.release()
        
        if frame_count == 0:
            logger.error("[TIMELAPSE] No frames were successfully written to video.")
            os.remove(output_path)
            return {"success": False, "error": "No valid frames to write"}
        
        file_size_mb = os.path.getsize(output_path) / (1024 * 1024)
        logger.info(
            f"[TIMELAPSE] Video generated successfully: {output_path} "
            f"({frame_count} frames, {failed_frames} skipped, {file_size_mb:.2f} MB)"
        )
        
        return {
            "success": True,
            "video_path": output_path,
            "video_url": f"/static/videos/{os.path.basename(output_path)}",
            "frame_count": frame_count,
            "skipped_frames": failed_frames,
            "file_size_mb": round(file_size_mb, 2)
        }
        
    except Exception as e:
        logger.error(f"[TIMELAPSE] Error during video generation: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


import os
import time
import logging
from datetime import datetime, timedelta
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

def clean_old_files():
    """
    Delete old files based on retention policies:
    - Images older than 7 days
    - Videos older than 30 days
    
    This function is designed to be called by APScheduler daily.
    """
    try:
        current_time = time.time()
        
        # Calculate retention thresholds in seconds
        image_retention_seconds = 7 * 24 * 60 * 60  # 7 days
        video_retention_seconds = 30 * 24 * 60 * 60  # 30 days
        
        # Clean old images
        deleted_images = 0
        image_files = glob.glob(os.path.join(IMAGE_DIR, "*.jpg"))
        image_files.extend(glob.glob(os.path.join(IMAGE_DIR, "*.jpeg")))
        
        for img_path in image_files:
            try:
                if os.stat(img_path).st_mtime < current_time - image_retention_seconds:
                    os.remove(img_path)
                    deleted_images += 1
                    logger.info(f"[CLEANUP] Deleted old image: {os.path.basename(img_path)}")
            except OSError as e:
                logger.warning(f"[CLEANUP] Failed to delete image {img_path}: {e}")
        
        # Clean old videos
        deleted_videos = 0
        video_files = glob.glob(os.path.join(VIDEO_DIR, "*.mp4"))
        
        for vid_path in video_files:
            try:
                if os.stat(vid_path).st_mtime < current_time - video_retention_seconds:
                    os.remove(vid_path)
                    deleted_videos += 1
                    logger.info(f"[CLEANUP] Deleted old video: {os.path.basename(vid_path)}")
            except OSError as e:
                logger.warning(f"[CLEANUP] Failed to delete video {vid_path}: {e}")
        
        logger.info(f"[CLEANUP] Task completed: {deleted_images} images, {deleted_videos} videos deleted.")
        return {"images_deleted": deleted_images, "videos_deleted": deleted_videos}
        
    except Exception as e:
        logger.error(f"[CLEANUP] Error during cleanup task: {e}", exc_info=True)
        return {"error": str(e)}

def generate_timelapse_video():
    """
    Generate an MP4 timelapse video from images captured in the last 3 days.
    
    - Reads JPEG images from IMAGE_DIR
    - Sorts them chronologically
    - Compiles into H.264 MP4 (30 FPS)
    - Handles edge cases gracefully (no images, unreadable images, etc.)
    
    Returns:
        dict: {"success": True, "video_path": "...", "frame_count": N} or 
              {"success": False, "error": "..."}
    """
    try:
        current_time = time.time()
        three_days_ago = current_time - (3 * 24 * 60 * 60)  # 3 days in seconds
        
        # Collect images from the last 3 days
        all_images = glob.glob(os.path.join(IMAGE_DIR, "*.jpg"))
        all_images.extend(glob.glob(os.path.join(IMAGE_DIR, "*.jpeg")))
        
        if not all_images:
            logger.warning("[TIMELAPSE] No images found in IMAGE_DIR.")
            return {"success": False, "error": "No images available"}
        
        # Filter images by modification time (last 3 days)
        recent_images = []
        for img_path in all_images:
            try:
                if os.stat(img_path).st_mtime >= three_days_ago:
                    recent_images.append(img_path)
            except OSError as e:
                logger.warning(f"[TIMELAPSE] Cannot stat file {img_path}: {e}")
        
        if not recent_images:
            logger.warning("[TIMELAPSE] No images from the last 3 days.")
            return {"success": False, "error": "No images from the last 3 days"}
        
        # Sort images chronologically by filename/timestamp
        recent_images.sort()
        logger.info(f"[TIMELAPSE] Found {len(recent_images)} images for video generation.")
        
        # Read the first image to determine dimensions
        first_frame = cv2.imread(recent_images[0])
        if first_frame is None:
            logger.error(f"[TIMELAPSE] Failed to read first image: {recent_images[0]}")
            return {"success": False, "error": "Cannot read first image"}
        
        height, width = first_frame.shape[:2]
        size = (width, height)
        logger.info(f"[TIMELAPSE] Video dimensions: {width}x{height}")
        
        # Generate output filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = os.path.join(VIDEO_DIR, f"timelapse_{timestamp}.mp4")
        
        # Initialize VideoWriter with H.264 codec
        # Fallback codecs: 'mp4v' or 'avc1' depending on OpenCV build
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        fps = 30.0
        
        out = cv2.VideoWriter(output_path, fourcc, fps, size)
        
        if not out.isOpened():
            logger.error("[TIMELAPSE] VideoWriter failed to open.")
            return {"success": False, "error": "VideoWriter initialization failed"}
        
        # Write frames to video
        frame_count = 0
        failed_frames = 0
        
        for img_path in recent_images:
            try:
                frame = cv2.imread(img_path)
                if frame is None:
                    logger.warning(f"[TIMELAPSE] Skipped unreadable frame: {os.path.basename(img_path)}")
                    failed_frames += 1
                    continue
                
                # Resize frame to match output dimensions (in case of size mismatch)
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
        
        logger.info(
            f"[TIMELAPSE] Video generated successfully: {output_path} "
            f"({frame_count} frames, {failed_frames} skipped)"
        )
        
        return {
            "success": True,
            "video_path": output_path,
            "frame_count": frame_count,
            "skipped_frames": failed_frames,
            "file_size_mb": os.path.getsize(output_path) / (1024 * 1024)
        }
        
    except Exception as e:
        logger.error(f"[TIMELAPSE] Error during video generation: {e}", exc_info=True)
        return {"success": False, "error": str(e)}

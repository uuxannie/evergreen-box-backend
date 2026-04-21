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

def clean_old_files(days_to_keep=30):
    """
    Clean up old image and video files older than specified days.
    
    Args:
        days_to_keep (int): Number of days to retain files. Default is 30 days.
    
    Returns:
        dict: {"deleted_images": N, "deleted_videos": M, "freed_space_mb": X.XX}
    """
    try:
        import shutil
        from datetime import timedelta
        
        current_time = time.time()
        cutoff_time = current_time - (days_to_keep * 86400)  # Convert days to seconds
        
        deleted_images = 0
        deleted_videos = 0
        freed_space_mb = 0.0
        
        # Clean up old images
        for img_path in glob.glob(os.path.join(IMAGE_DIR, "*.jpg")):
            if os.path.getmtime(img_path) < cutoff_time:
                try:
                    file_size = os.path.getsize(img_path) / (1024 * 1024)
                    os.remove(img_path)
                    deleted_images += 1
                    freed_space_mb += file_size
                    logger.info(f"[CLEANUP] Deleted old image: {os.path.basename(img_path)}")
                except OSError as e:
                    logger.warning(f"[CLEANUP] Failed to delete {img_path}: {e}")
        
        for img_path in glob.glob(os.path.join(IMAGE_DIR, "*.jpeg")):
            if os.path.getmtime(img_path) < cutoff_time:
                try:
                    file_size = os.path.getsize(img_path) / (1024 * 1024)
                    os.remove(img_path)
                    deleted_images += 1
                    freed_space_mb += file_size
                    logger.info(f"[CLEANUP] Deleted old image: {os.path.basename(img_path)}")
                except OSError as e:
                    logger.warning(f"[CLEANUP] Failed to delete {img_path}: {e}")
        
        # Clean up old videos
        for vid_path in glob.glob(os.path.join(VIDEO_DIR, "*.mp4")):
            if os.path.getmtime(vid_path) < cutoff_time:
                try:
                    file_size = os.path.getsize(vid_path) / (1024 * 1024)
                    os.remove(vid_path)
                    deleted_videos += 1
                    freed_space_mb += file_size
                    logger.info(f"[CLEANUP] Deleted old video: {os.path.basename(vid_path)}")
                except OSError as e:
                    logger.warning(f"[CLEANUP] Failed to delete {vid_path}: {e}")
        
        result = {
            "deleted_images": deleted_images,
            "deleted_videos": deleted_videos,
            "freed_space_mb": round(freed_space_mb, 2)
        }
        
        logger.info(
            f"[CLEANUP] Cleanup complete: {deleted_images} images, {deleted_videos} videos deleted, "
            f"{freed_space_mb:.2f} MB freed"
        )
        
        return result
        
    except Exception as e:
        logger.error(f"[CLEANUP] Error during cleanup: {e}", exc_info=True)
        return {
            "deleted_images": 0,
            "deleted_videos": 0,
            "freed_space_mb": 0.0,
            "error": str(e)
        }

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

def generate_timelapse_video(use_existing_data=False, hours_back=24):
    """
    Generate an MP4 timelapse video from available images in the directory.
    
    For demo mode, this reads stored images (capped at 500) from the USB webcam capture,
    sorts them chronologically, and compiles them into an H.264 MP4 (30 FPS).
    
    Args:
        use_existing_data (bool): If False (default), only use recent images (within hours_back).
                                 If True, use all available historical images.
        hours_back (int): Number of hours to look back for "new" data. Default is 24 hours.
    
    Returns:
        dict: {
            "success": True,
            "video_path": "...",
            "video_url": "...",
            "frame_count": N,
            "skipped_frames": M,
            "file_size_mb": X.XX,
            "data_source": "new" or "existing"
        } or
        {
            "success": False,
            "error": "...",
            "data_source": None
        }
    """
    try:
        # Collect all image files
        all_images = glob.glob(os.path.join(IMAGE_DIR, "*.jpg"))
        all_images.extend(glob.glob(os.path.join(IMAGE_DIR, "*.jpeg")))
        
        if not all_images:
            logger.warning("[TIMELAPSE] No images found in IMAGE_DIR.")
            return {
                "success": False,
                "error": "No image frames available (new or existing)",
                "data_source": None
            }
        
        # Filter images based on use_existing_data flag
        if not use_existing_data:
            # Only use recent images (within hours_back hours)
            current_time = time.time()
            cutoff_time = current_time - (hours_back * 3600)
            
            recent_images = [
                img for img in all_images
                if os.path.getmtime(img) >= cutoff_time
            ]
            
            if not recent_images:
                logger.warning(f"[TIMELAPSE] No images found within last {hours_back} hours.")
                return {
                    "success": False,
                    "error": f"No new frames available (last {hours_back} hours)",
                    "data_source": None
                }
            
            selected_images = recent_images
            data_source = "new"
            logger.info(f"[TIMELAPSE] Using NEW frames: {len(selected_images)} images from last {hours_back} hours")
        else:
            # Use all available images
            selected_images = all_images
            data_source = "existing"
            logger.info(f"[TIMELAPSE] Using EXISTING frames: {len(selected_images)} total images from history")
        
        # Sort images chronologically by filename (timestamp-based naming)
        selected_images.sort()
        logger.info(f"[TIMELAPSE] Found {len(selected_images)} images for video generation.")
        
        # Read the first image to determine dimensions
        first_frame = cv2.imread(selected_images[0])
        if first_frame is None:
            logger.error(f"[TIMELAPSE] Failed to read first image: {selected_images[0]}")
            return {
                "success": False,
                "error": "Cannot read first image",
                "data_source": data_source
            }
        
        height, width = first_frame.shape[:2]
        size = (width, height)
        logger.info(f"[TIMELAPSE] Video dimensions: {width}x{height}")
        
        # Generate output filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = os.path.join(VIDEO_DIR, f"timelapse_{timestamp}.mp4")
        
        # Initialize VideoWriter with H.264 codec
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')  # type: ignore[attr-defined]
        fps = 30.0
        
        out = cv2.VideoWriter(output_path, fourcc, fps, size)
        
        if not out.isOpened():
            logger.error("[TIMELAPSE] VideoWriter failed to open.")
            return {
                "success": False,
                "error": "VideoWriter initialization failed",
                "data_source": data_source
            }
        
        # Write frames to video
        frame_count = 0
        failed_frames = 0
        
        for img_path in selected_images:
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
            return {
                "success": False,
                "error": "No valid frames to write",
                "data_source": data_source
            }
        
        file_size_mb = os.path.getsize(output_path) / (1024 * 1024)
        logger.info(
            f"[TIMELAPSE] Video generated successfully ({data_source} data): {output_path} "
            f"({frame_count} frames, {failed_frames} skipped, {file_size_mb:.2f} MB)"
        )
        
        return {
            "success": True,
            "video_path": output_path,
            "video_url": f"/static/videos/{os.path.basename(output_path)}",
            "frame_count": frame_count,
            "skipped_frames": failed_frames,
            "file_size_mb": round(file_size_mb, 2),
            "data_source": data_source
        }

        
    except Exception as e:
        logger.error(f"[TIMELAPSE] Error during video generation: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


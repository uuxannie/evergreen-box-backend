import os
import shutil
from datetime import datetime
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from db.database import save_camera_image, get_latest_camera_image

router = APIRouter()

# Define the base directory for image storage
RENDER_DISK_BASE = "/var/lib/data"

# Check if the directory for Render mounting exists
if os.path.exists(RENDER_DISK_BASE):
    UPLOAD_DIR = os.path.join(RENDER_DISK_BASE, "images")
    print(f"[STORAGE] Running in Cloud. Using Render Disk: {UPLOAD_DIR}")
else:
    # if not, fallback to local storage
    UPLOAD_DIR = os.path.join(os.getcwd(), "static", "images")
    print(f"[STORAGE] Running Locally. Using fallback directory: {UPLOAD_DIR}")

# Ensure that the final images directory exists regardless of where you run it
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/upload")
async def upload_image(file: UploadFile = File(...), yolo_result: str = Form(None)):
    try:
        # 1. 【安全加固】确保上传目录一定存在
        if not os.path.exists(UPLOAD_DIR):
            os.makedirs(UPLOAD_DIR, exist_ok=True)
            print(f"[SYSTEM] 已创建缺失的目录: {UPLOAD_DIR}")

        # 2. 生成唯一文件名 (加入更精确的毫秒，防止并发冲突)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:19] # 20260414_103000_123
        extension = file.filename.split(".")[-1] if "." in file.filename else "jpg"
        filename = f"{timestamp}.{extension}"
        file_path = os.path.join(UPLOAD_DIR, filename)

        # 3. 【隐私保护逻辑】上传新图前，你可以选择是否清理旧图
        # 如果你只想保留最新的一张，可以取消下面这段注释：
        """
        for old_file in os.listdir(UPLOAD_DIR):
            old_path = os.path.join(UPLOAD_DIR, old_file)
            if os.path.isfile(old_path):
                os.remove(old_path)
        """

        # 4. 写入物理磁盘
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # 5. 构造 URL 
        image_url = f"/static/images/{filename}"
        storage_type = "render_disk" if os.path.exists(RENDER_DISK_BASE) else "local"

        # 6. 存入数据库 (确保 database.py 里的函数正常)
        save_camera_image(image_url=image_url, storage_type=storage_type, yolo_result=yolo_result)

        print(f"[SUCCESS] 照片已保存至: {file_path}")
        return {
            "status": "success",
            "image_url": image_url,
            "filename": filename
        }

    except Exception as e:
        # 把具体的报错打印出来，这样你在 Render 日志里一眼就能看到原因
        print(f"[CAMERA ERROR] 上传失败，原因: {str(e)}")
        raise HTTPException(status_code=500, detail=f"内部服务器错误: {str(e)}")
'''
@router.post("/upload")
async def upload_image(file: UploadFile = File(...), yolo_result: str = Form(None)):
    try:
        # Generate a unique filename using the current timestamp, such as "20260411_103000.jpg"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # get the file extension, default to jpg if not provided
        extension = file.filename.split(".")[-1] if "." in file.filename else "jpg"
        filename = f"{timestamp}.{extension}"
        
        # complete file path for storage, for example: "/var/lib/data/images/20260411_103000.jpg"
        file_path = os.path.join(UPLOAD_DIR, filename)

        # write to physical disk (Render disk or local)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Construct the external URL path (relative path used by the frontend)
        # Regardless of whether the file actually exists in the Render or locally, the URL exposed to the frontend will always be consistent.
        image_url = f"/static/images/{filename}"

        # Determining the storage type facilitates future database maintenance.
        storage_type = "render_disk" if os.path.exists(RENDER_DISK_BASE) else "local"

        # Write to database
        save_camera_image(image_url=image_url, storage_type=storage_type, yolo_result=yolo_result)

        return {
            "status": "success",
            "message": "Image uploaded successfully",
            "image_url": image_url
        }

    except Exception as e:
        print(f"[CAMERA ERROR] Upload failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to process and save the image.")
'''

@router.get("/latest")
async def get_latest_image():
    try:
        image_data = get_latest_camera_image()
        
        if not image_data:
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
        print(f"[CAMERA ERROR] Fetch latest failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve the latest image.")
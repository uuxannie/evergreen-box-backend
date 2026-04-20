"""
EverGreen Box - Plant Monitoring System for M1 MacBook
Real-time YOLO detection + async backend upload + Twilio alerts + Arduino control
"""

import cv2
import threading
import time
import json
import requests
import logging
import serial
import os
from datetime import datetime, date
from collections import deque
from dotenv import load_dotenv
from ultralytics import YOLO
from twilio.rest import Client

load_dotenv()

# ================= Configuration =================
RENDER_BACKEND_URL = os.getenv('RENDER_BACKEND_URL', "https://evergreen-box-backend.onrender.com")
UPLOAD_INTERVAL_SECONDS = 15  # Upload interval in seconds
UPLOAD_TIMEOUT_SECONDS = 5

CAMERA_INDEX = 0
WINDOW_SIZE = 30
MIN_SPOTTED_FRAMES = 15

# YOLO model paths
MODEL_A_PATH = "cactus_pothos_succulent_training_150epoches.pt"  # Plant species detection
MODEL_B_PATH = "health_best.pt"  # Plant health detection

# ================= Twilio Configuration =================
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID', '')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN', '')
TWILIO_WHATSAPP_NUMBER = os.getenv('TWILIO_WHATSAPP_NUMBER', 'whatsapp:+14155238886')
YOUR_WHATSAPP_NUMBER = os.getenv('YOUR_WHATSAPP_NUMBER', 'whatsapp:+85297050549')

# ================= Arduino Serial Configuration =================
SERIAL_PORT = '/dev/ttyUSB0'  # macOS: /dev/cu.usbserial-* or /dev/ttyUSB0
BAUD_RATE = 9600
SERIAL_SEND_INTERVAL = 0.5  # Send interval in seconds

# ================= Logging Configuration =================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

# ================= Global Variables =================
# YOLO detection results
# Format: confidence is float 0-1 (e.g., 0.985), not percentage string
latest_yolo_result = {
    "plant": "Unknown",
    "health_status": "Healthy",
    "confidence": 0.0,
    "timestamp": None
}
yolo_result_lock = threading.Lock()

# Detection history
detection_history = deque(maxlen=WINDOW_SIZE)
last_alert_date = None
last_serial_send_time = time.time()

# Thread control
upload_thread = None
should_exit = False

# Arduino serial port
ser = None

# ================= Arduino Initialization =================
def initialize_serial():
    """Initialize Arduino serial connection"""
    global ser
    
    logger.info(f"Attempting to connect Arduino ({SERIAL_PORT}, {BAUD_RATE} baud)...")
    try:
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
        logger.info(f"Arduino connected: {SERIAL_PORT}")
        time.sleep(2)  # Wait for Arduino initialization
    except Exception as e:
        logger.warning(f"Arduino connection failed: {e}")
        logger.warning("Running in vision-only mode (no hardware control)")
        ser = None

def send_to_arduino(command):
    """Send command to Arduino"""
    global ser, last_serial_send_time
    
    if time.time() - last_serial_send_time < SERIAL_SEND_INTERVAL:
        return
    
    if ser is None or not ser.is_open:
        return
    
    try:
        ser.write(command.encode('utf-8'))
        logger.debug(f"Sent to Arduino: {command}")
        last_serial_send_time = time.time()
    except Exception as e:
        logger.warning(f"Arduino send failed: {e}")

# ================= Twilio Alerts =================
def send_whatsapp_alert(plant_name):
    """
    Background thread task: Send Twilio WhatsApp alert
    """
    try:
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        msg_body = f"🌿 AIoT Plant Alert: Unhealthy leaves detected on your {plant_name} at {current_time}. Please check the environment parameters!"
        
        logger.info("Attempting to send WhatsApp message via Twilio...")
        message = client.messages.create(
            from_=TWILIO_WHATSAPP_NUMBER,
            body=msg_body,
            to=YOUR_WHATSAPP_NUMBER
        )
        logger.info(f"WhatsApp message sent! SID: {message.sid}")
    except Exception as e:
        logger.error(f"WhatsApp send failed: {e}")

# ================= YOLO Initialization =================
def initialize_models():
    """Initialize YOLO models with M1 GPU acceleration"""
    logger.info("Loading YOLO models...")
    try:
        # Use mps device (M1 GPU) for accelerated inference
        model_a = YOLO(MODEL_A_PATH)
        model_a.to("mps")  # M1 GPU acceleration
        logger.info("Model A (plant species) loaded successfully - using MPS device")
        
        model_b = YOLO(MODEL_B_PATH)
        model_b.to("mps")  # M1 GPU acceleration
        logger.info("Model B (plant health) loaded successfully - using MPS device")
        
        return model_a, model_b
    except Exception as e:
        logger.error(f"Model loading failed: {e}")
        raise

def initialize_camera():
    """Initialize camera"""
    logger.info(f"Initializing camera (index: {CAMERA_INDEX})...")
    cap = cv2.VideoCapture(CAMERA_INDEX)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    
    if not cap.isOpened():
        logger.error("Failed to open camera")
        raise Exception("Camera initialization failed")
    
    logger.info("Camera initialized successfully")
    return cap

# ================= YOLO Detection Logic =================
def run_yolo_detection(frame, model_a, model_b):
    """
    Run YOLO detection and update global YOLO result variable.
    Return annotated frame and detection results.
    """
    global latest_yolo_result
    
    annotated_frame = None
    spot_detected_this_frame = False
    detected_plant_name = "Unknown"
    detected_health_status = "Unknown"
    arduino_command = 'N'
    
    try:
        # Model A: Plant species detection
        results_a = model_a(frame, conf=0.7, verbose=False)
        annotated_frame = results_a[0].plot()
        
        if len(results_a[0].boxes) > 0:
            best_box_idx = results_a[0].boxes.conf.argmax()
            best_box_a = results_a[0].boxes[best_box_idx]
            
            x1, y1, x2, y2 = map(int, best_box_a.xyxy[0])
            plant_cls = int(best_box_a.cls[0])
            detected_plant_name = model_a.names[plant_cls]
            confidence_a = float(best_box_a.conf[0])
            
            # Arduino command based on plant class
            arduino_command = str(int(plant_cls))
            
            # Crop plant region for health detection
            cropped_plant = frame[y1:y2, x1:x2]
            
            if cropped_plant.shape[0] > 10 and cropped_plant.shape[1] > 10:
                # Model B: Plant health state detection
                results_b = model_b(cropped_plant, conf=0.9, verbose=False)
                
                for box_b in results_b[0].boxes:
                    health_cls = int(box_b.cls[0])
                    health_name = model_b.names[health_cls]
                    confidence_b = float(box_b.conf[0])
                    
                    bx1, by1, bx2, by2 = map(int, box_b.xyxy[0])
                    real_x1, real_y1 = x1 + bx1, y1 + by1
                    real_x2, real_y2 = x1 + bx2, y1 + by2
                    
                    # Draw annotation on frame
                    color = (0, 0, 255) if health_name.upper() == 'UNHEALTHY' else (0, 255, 0)
                    cv2.rectangle(annotated_frame, (real_x1, real_y1), (real_x2, real_y2), color, 2)
                    cv2.putText(annotated_frame, f"STATUS: {health_name}", (real_x1, real_y1 - 10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
                    
                    if health_name.upper() == 'UNHEALTHY':
                        spot_detected_this_frame = True
                    
                    detected_health_status = health_name
                    
                    # Update global YOLO result
                    # Format: confidence is float 0-1 (e.g., 0.985)
                    with yolo_result_lock:
                        latest_yolo_result = {
                            "plant": detected_plant_name,
                            "health_status": detected_health_status,
                            "confidence": round(confidence_b, 3),  # Keep as float 0-1
                            "timestamp": datetime.now().isoformat()
                        }
        
    except Exception as e:
        logger.error(f"YOLO detection error: {e}")
    
    return annotated_frame, spot_detected_this_frame, detected_plant_name, arduino_command

# ================= Background Upload Thread =================
def upload_to_backend(current_frame):
    """
    Background thread task: Periodically upload current frame and YOLO results to backend
    """
    global latest_yolo_result
    
    while not should_exit:
        time.sleep(UPLOAD_INTERVAL_SECONDS)
        
        if current_frame is None:
            continue
        
        try:
            # Get latest YOLO result
            with yolo_result_lock:
                yolo_data = latest_yolo_result.copy()
            
            # Encode image as JPEG
            ret, buffer = cv2.imencode('.jpg', current_frame)
            if not ret:
                logger.warning("Image encoding failed")
                continue
            
            # Build upload data
            files = {
                "file": ("plant_frame.jpg", buffer.tobytes(), "image/jpeg")
            }
            data = {
                "yolo_result": json.dumps(yolo_data)
            }
            
            # Send POST request
            response = requests.post(
                f"{RENDER_BACKEND_URL}/api/camera/upload-image",
                files=files,
                data=data,
                timeout=UPLOAD_TIMEOUT_SECONDS
            )
            
            if response.status_code == 200:
                logger.info(f"Upload successful - {yolo_data['plant']} ({yolo_data['disease']})")
            else:
                logger.warning(f"Upload returned status code: {response.status_code}")
        
        except requests.exceptions.Timeout:
            logger.warning(f"Upload timeout (>{UPLOAD_TIMEOUT_SECONDS}s)")
        except requests.exceptions.RequestException as e:
            logger.warning(f"Network error: {e}")
        except Exception as e:
            logger.error(f"Upload error: {e}")

# ================= Main Program =================
def main():
    global upload_thread, should_exit, latest_yolo_result, ser
    
    # Initialize variables to prevent UnboundLocalError in finally block
    cap = None
    model_a = None
    model_b = None
    upload_thread = None
    
    logger.info("=" * 60)
    logger.info("EverGreen Box - M1 Plant Monitoring System")
    logger.info("YOLO detection + backend upload + Twilio alerts + Arduino control")
    logger.info("=" * 60)
    
    try:
        # Initialize components
        model_a, model_b = initialize_models()
        cap = initialize_camera()
        initialize_serial()
        
        # Start background upload thread
        logger.info("Starting background upload thread...")
        should_exit = False
        upload_thread = threading.Thread(target=upload_to_backend, args=(None,), daemon=False)
        upload_thread.start()
        
        logger.info("System started. Press 'q' to stop.\n")
        
        current_frame = None
        frame_count = 0
        
        while True:
            ret, frame = cap.read()
            if not ret:
                logger.error("Failed to read from camera")
                break
            
            # Horizontal flip (selfie mode)
            frame = cv2.flip(frame, 1)
            
            # 3x zoom center region
            zoom_factor = 3
            h, w = frame.shape[:2]
            center_x, center_y = w / 2, h / 2
            new_w, new_h = w / zoom_factor, h / zoom_factor
            
            zx1 = int(center_x - new_w / 2)
            zx2 = int(center_x + new_w / 2)
            zy1 = int(center_y - new_h / 2)
            zy2 = int(center_y + new_h / 2)
            
            cropped_frame = frame[zy1:zy2, zx1:zx2]
            frame = cv2.resize(cropped_frame, (w, h))
            
            # Run YOLO detection
            annotated_frame, spot_detected, plant_name, arduino_cmd = run_yolo_detection(frame, model_a, model_b)
            
            if annotated_frame is None:
                annotated_frame = frame
            
            # Update detection history
            if spot_detected:
                detection_history.append(1)
            else:
                detection_history.append(0)
            
            spotted_count = sum(detection_history)
            
            # Send Arduino command
            send_to_arduino(arduino_cmd)
            
            # Check if WhatsApp alert needs to be sent
            if spotted_count >= MIN_SPOTTED_FRAMES:
                today = date.today()
                if last_alert_date != today:
                    logger.warning(f"Unhealthy plant detected! Sending alert...")
                    threading.Thread(target=send_whatsapp_alert, args=(plant_name,), daemon=True).start()
                    last_alert_date = today
                    detection_history.clear()
                    cv2.putText(annotated_frame, "WHATSAPP ALERT SENT TODAY!", (20, 50),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 165, 255), 2)
            
            # Display detection info on frame
            cv2.putText(annotated_frame, f"Plant: {plant_name}", (20, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            cv2.putText(annotated_frame, f"Diagnosis: {spotted_count}/{MIN_SPOTTED_FRAMES}", (20, 70),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            
            # Show upload status
            with yolo_result_lock:
                status_text = f"Status: {latest_yolo_result['health_status']} (Conf: {latest_yolo_result['confidence']})"
            cv2.putText(annotated_frame, status_text, (20, 110),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            
            # Arduino status
            arduino_status = "Arduino: OK" if ser is not None and ser.is_open else "Arduino: DISCONNECTED"
            cv2.putText(annotated_frame, arduino_status, (20, 150),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0) if ser else (0, 0, 255), 2)
            
            # Update current frame for background upload
            current_frame = frame
            
            # Display frame
            cv2.imshow('EverGreen Box - M1 Plant Monitor', annotated_frame)
            
            frame_count += 1
            if frame_count % 30 == 0:
                logger.info(f"Processed {frame_count} frames")
            
            # Exit key
            if cv2.waitKey(1) & 0xFF == ord('q'):
                logger.info("\nUser pressed 'q', shutting down...")
                break
    
    except Exception as e:
        logger.error(f"Program error: {e}")
    
    finally:
        # Clean up resources
        logger.info("Cleaning up resources...")
        should_exit = True
        
        if upload_thread is not None and upload_thread.is_alive():
            logger.info("Waiting for upload thread to complete...")
            upload_thread.join(timeout=10)
            if upload_thread.is_alive():
                logger.warning("Upload thread did not terminate properly")
        
        if ser is not None and ser.is_open:
            ser.close()
            logger.info("Arduino serial port closed")
        
        # Safely release camera
        if cap is not None:
            cap.release()
            cv2.destroyAllWindows()
        
        logger.info("Program closed safely")
        logger.info("=" * 60 + "\n")

# ================= Entry Point =================
if __name__ == "__main__":
    main()

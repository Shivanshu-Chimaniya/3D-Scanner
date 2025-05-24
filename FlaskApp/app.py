from flask import Flask, render_template, request, jsonify, Response, send_from_directory, stream_with_context
from flask_socketio import SocketIO, emit
import os
import logging
import json
import threading
import time
import queue
import cv2
import re
import datetime
import shutil

# from config import *
from modules.image_processor import extract_metadata, preprocess_and_extract_line, extract_laser_points, crop_images
from modules.esp32_controller import esp32_laser_on, esp32_laser_off, esp32_step_motor, esp32_check_status
from modules.utils import generate_qr_code
from modules.storage import get_all_scans, create_scan_directory, delete_scan 
from modules.point_cloud import convert_to_3d, save_ply
from config import SECRET_KEY, HOST, PORT, DEBUG, ESP32_IP, TIME_DELAY, TOTAL_STEPS, IMAGES_FOLDER 

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = SECRET_KEY
socketio = SocketIO(app, cors_allowed_origins="*")

# Global variables
ESP32_IP = ESP32_IP  
esp32_connected = False
connected_phones = set()
scanning = False
scan_thread = None
current_step = 0
total_steps = TOTAL_STEPS
images_captured = 0
current_mode = "Idle"
laser_status = False
TIME_DELAY=TIME_DELAY

# Processing status tracking
processing_status = {}
processing_results = {}

# Path for saving images
IMAGES_FOLDER = IMAGES_FOLDER
os.makedirs(IMAGES_FOLDER, exist_ok=True)

# Scanning Process
def start_scan():
    global scanning, current_step, total_steps, images_captured, current_mode, scan_thread
    
    scanning = True
    current_step = 0
    total_steps = 400
    images_captured = 0
    
    # Create a new directory for this scan
    scan_dir = create_scan_directory()
    
    try:
        # First 200 steps with laser ON
        current_mode = "Laser ON"
        esp32_laser_on()
        laser_status = True
        esp32_step_motor()
        
        for i in range(200):
            if not scanning:
                break
            
            current_step = i + 1
            
            # Wait briefly for image capture
            time.sleep(TIME_DELAY)

            # Capture image via WebSocket
            socketio.emit('capture_request', {
                'step': current_step,
                'mode': 'laser_on'
            })
        
            
            images_captured += 1
            
            # Update progress
            progress = (current_step / total_steps) * 100
            socketio.emit('scan_progress', {
                'step': current_step,
                'total': total_steps,
                'progress': progress,
                'images': images_captured,
                'mode': current_mode
            })
            
            # Small delay between steps
            time.sleep(TIME_DELAY)
        
        # Next 200 steps with laser OFF
        if scanning:
            current_mode = "Laser OFF"
            esp32_laser_off()
            laser_status = True
            esp32_step_motor()
            
            for i in range(200):
                if not scanning:
                    break
                
                current_step = i + 201
                
                # Wait briefly for image capture
                time.sleep(TIME_DELAY)

                # Capture image via WebSocket
                socketio.emit('capture_request', {
                    'step': current_step,
                    'mode': 'laser_off'
                })
                
                
                images_captured += 1
                
                # Update progress
                progress = (current_step / total_steps) * 100
                socketio.emit('scan_progress', {
                    'step': current_step,
                    'total': total_steps,
                    'progress': progress,
                    'images': images_captured,
                    'mode': current_mode
                })
                
                # Small delay between steps
                time.sleep(TIME_DELAY)
        
        # Scan completed
        if scanning:
            socketio.emit('log_message', {'message': "Scan completed successfully!"})
            socketio.emit('scan_completed', {'images_captured': images_captured})
        else:
            socketio.emit('log_message', {'message': "Scan was stopped manually"})
            socketio.emit('scan_stopped', {})
    
    except Exception as e:
        logger.error(f"Scan error: {str(e)}")
        socketio.emit('log_message', {'message': f"Error during scan: {str(e)}"})
    
    finally:
        # Make sure laser is off when done
        esp32_laser_off()
        scanning = False
        current_mode = "Idle"
        socketio.emit('update_mode', {'mode': current_mode})
        socketio.emit('scan_stopped', {})
        # Update the scans list
        socketio.emit('update_scans_list', {'scans': get_all_scans()})

# Processing worker function
def process_scan_images(scan_id, status_queue):
    try:
        # Define paths
        scan_dir = os.path.join(IMAGES_FOLDER, scan_id)
        laser_on_dir = os.path.join(scan_dir, "laser_on")
        laser_off_dir = os.path.join(scan_dir, "laser_off")
        processed_dir = os.path.join(scan_dir, "processed")
        cropped_dir = os.path.join(scan_dir, "cropped")
        
        # Check if cropped images exist and use those instead
        if os.path.exists(cropped_dir) and os.path.exists(os.path.join(cropped_dir, "laser_on")):
            laser_on_dir = os.path.join(cropped_dir, "laser_on")
            laser_off_dir = os.path.join(cropped_dir, "laser_off")
            status_queue.put({"status": "info", "message": "Using cropped images for processing"})
        else:
            laser_on_dir = os.path.join(scan_dir, "laser_on")
            laser_off_dir = os.path.join(scan_dir, "laser_off")

        # Create processed directory if it doesn't exist
        os.makedirs(processed_dir, exist_ok=True)
        
        # Get matching image pairs
        laser_on_files = sorted([f for f in os.listdir(laser_on_dir) if f.endswith(('.jpg', '.jpeg', '.png'))])
        laser_off_files = sorted([f for f in os.listdir(laser_off_dir) if f.endswith(('.jpg', '.jpeg', '.png'))])
        
        # Ensure we have matching pairs
        if len(laser_on_files) != len(laser_off_files):
            status_queue.put({"status": "error", "message": "Mismatched number of images in laser_on and laser_off folders"})
            return
        
        # Initialize all 3D points array
        all_points_3d = []
        
        # Update status
        status_queue.put({
            "status": "starting", 
            "message": f"Starting processing of {len(laser_on_files)} image pairs", 
            "total_images": len(laser_on_files),
            "processed_images": 0
        })
        
        # Process each image pair
        for i, (on_file, off_file) in enumerate(zip(laser_on_files, laser_off_files)):
            try:
                # Extract image number and calculate angle
                img_num, angle = extract_metadata(on_file)
                
                # Update status
                status_queue.put({
                    "status": "processing", 
                    "message": f"Processing image pair {i+1}/{len(laser_on_files)} (angle: {angle:.1f}°)",
                    "processed_images": i,
                    "current_angle": angle
                })
                
                # Load images
                laser_on_path = os.path.join(laser_on_dir, on_file)
                laser_off_path = os.path.join(laser_off_dir, off_file)
                
                laser_on = cv2.imread(laser_on_path)
                laser_off = cv2.imread(laser_off_path)
                
                if laser_on is None or laser_off is None:
                    status_queue.put({"status": "warning", "message": f"Could not read images: {on_file} or {off_file}"})
                    continue
                
                # Get image dimensions
                height, width = laser_on.shape[:2]
                
                # Process images# Process images
                processed_image, diff = preprocess_and_extract_line(laser_on, laser_off, scan_dir,img_num, angle)
                
                # Extract 2D points
                points_2d = extract_laser_points(processed_image)
                
                # Convert to 3D
                points_3d = convert_to_3d(points_2d, angle, width, height, img_num)
                
                # Add to all points
                if len(points_3d) > 0:
                    all_points_3d.extend(points_3d)
                
                # Save intermediate results
                if len(points_2d) > 0:
                    # Save processed image
                    processed_path = os.path.join(processed_dir, f"processed_angle_{angle:.1f}.jpg")
                    cv2.imwrite(processed_path, processed_image)
                    
                    # Visualize laser line on original image
                    vis_img = laser_on.copy()
                    for x, y in points_2d:
                        cv2.circle(vis_img, (int(x), int(y)), 1, (0, 255, 0), -1)
                        
                    vis_path = os.path.join(processed_dir, f"detected_line_angle_{angle:.1f}.jpg")
                    cv2.imwrite(vis_path, vis_img)
                    
                    # Update status with image info
                    status_queue.put({
                        "status": "image_processed",
                        "angle": angle,
                        "points_detected": len(points_2d),
                        "processed_image_path": processed_path,
                        "visualization_path": vis_path
                    })
                
                # Small delay to allow for better visualization of progress
                time.sleep(0.1)
            except Exception as e:
                status_queue.put({"status": "warning", "message": f"Error processing image pair {on_file}/{off_file}: {str(e)}"})
        
        # Save final point cloud
        if all_points_3d:
            output_ply = os.path.join(processed_dir, "reconstructed_model.ply")
            ply_result = save_ply(all_points_3d, output_ply)
            
            # Create processing_info.txt file
            with open(os.path.join(processed_dir, "processing_info.txt"), 'w') as f:
                f.write(f"Processed on {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Total points: {len(all_points_3d)}\n")
                f.write(f"Total images processed: {len(laser_on_files)}\n")
            
            status_queue.put({
                "status": "completed", 
                "message": ply_result,
                "total_points": len(all_points_3d),
                "ply_path": output_ply
            })
        else:
            status_queue.put({
                "status": "warning", 
                "message": "No 3D points were generated. Check your image processing parameters."
            })
            
    except Exception as e:
        status_queue.put({"status": "error", "message": f"Error during processing: {str(e)}"})

# Flask Routes
@app.route('/')
def index():
    # Generate QR code for phone connection
    host = request.host
    protocol = "https" if request.is_secure else "http"
    phone_url = f"{protocol}://{host}/phone"
    qr_code = generate_qr_code(phone_url)
    
    # Get all existing scans
    scans = get_all_scans()
    
    return render_template('index.html', 
                        esp32_connected=esp32_connected,
                        phones_connected=len(connected_phones),
                        phone_url=phone_url,
                        qr_code=qr_code,
                        scans=scans)

@app.route('/phone')
def phone():
    return render_template('phone.html')

@app.route('/process/<scan_id>')
def process_view(scan_id):
    return render_template('processing.html', scan_id=scan_id)

@app.route('/check_esp32', methods=['GET'])
def check_esp32():
    response = esp32_check_status()
    if response:
        return jsonify({'connected': True})
    else:
        return jsonify({'connected': False})

@app.route('/get_scans', methods=['GET'])
def get_scans():
    scans = get_all_scans()
    return jsonify({'scans': scans})

@app.route('/delete_scan/<scan_id>', methods=['GET'])
def delete_scan(scan_id):
    try:
        
        scan_path = os.path.join(IMAGES_FOLDER, scan_id)
        logger.error(f"{scan_id} {scan_path}")
        if os.path.exists(scan_path) and scan_id.startswith("scan_"):
            shutil.rmtree(scan_path)
            socketio.emit('log_message', {'message': f"Deleted scan: {scan_id}"})
            return jsonify({'success': True, 'message': f"Deleted scan: {scan_id}"})
        else:
            return jsonify({'success': False, 'message': "Invalid scan ID"})
    except Exception as e:
        logger.error(f"Error deleting scan: {str(e)}")
        return jsonify({'success': False, 'message': f"Error deleting scan: {str(e)}"})

@app.route('/process_scan/<scan_id>', methods=['POST'])
def process_scan_route(scan_id):
    try:
        scan_path = os.path.join(IMAGES_FOLDER, scan_id)
        if os.path.exists(scan_path) and scan_id.startswith("scan_"):
            # Check if already processing
            if scan_id in processing_status and processing_status[scan_id].get("status") == "active":
                return jsonify({"success": False, "message": "Already processing this scan"}), 400
            
            # Initialize status queue and processing thread
            status_queue = queue.Queue()
            processing_status[scan_id] = {"status": "active", "queue": status_queue}
            processing_results[scan_id] = []
            
            # Start processing in a separate thread
            thread = threading.Thread(target=process_scan_images, args=(scan_id, status_queue))
            thread.daemon = True
            thread.start()
            
            socketio.emit('log_message', {'message': f"Started processing scan: {scan_id}"})
            return jsonify({'success': True, 'message': f"Started processing scan: {scan_id}"})
        else:
            return jsonify({'success': False, 'message': "Invalid scan ID"})
    except Exception as e:
        logger.error(f"Error processing scan: {str(e)}")
        return jsonify({'success': False, 'message': f"Error processing scan: {str(e)}"})

@app.route('/api/status/<scan_id>')
def stream_status(scan_id):
    def generate():
        if scan_id not in processing_status:
            yield f"data: {json.dumps({'status': 'error', 'message': 'Scan not found'})}\n\n"
            return
            
        status_queue = processing_status[scan_id]["queue"]
        
        while True:
            try:
                # Non-blocking queue get with timeout
                status_update = status_queue.get(timeout=0.5)
                processing_results[scan_id].append(status_update)
                
                # Send the update as a server-sent event
                yield f"data: {json.dumps(status_update)}\n\n"
                
                # If processing is complete, exit
                if status_update.get("status") in ["completed", "error"]:
                    processing_status[scan_id]["status"] = "inactive"
                    break
                    
            except queue.Empty:
                # Send heartbeat to keep connection alive
                yield f"data: {json.dumps({'status': 'heartbeat'})}\n\n"
                
            except Exception as e:
                yield f"data: {json.dumps({'status': 'error', 'message': str(e)})}\n\n"
                break
    
    return Response(stream_with_context(generate()), mimetype='text/event-stream')

@app.route('/api/results/<scan_id>')
def get_results(scan_id):
    if scan_id not in processing_results:
        return jsonify({"error": "Scan not found"}), 404
        
    return jsonify({"results": processing_results[scan_id]})

@app.route('/download_processed/<scan_id>', methods=['GET'])
def download_processed(scan_id):
    try:
        processed_dir = os.path.join(IMAGES_FOLDER, scan_id, "processed")
        if os.path.exists(processed_dir) and scan_id.startswith("scan_"):
            # Send the reconstructed model PLY file
            return send_from_directory(processed_dir, "reconstructed_model.ply", as_attachment=True)
        else:
            return jsonify({'success': False, 'message': "Processed data not found"}), 404
    except Exception as e:
        logger.error(f"Error downloading processed data: {str(e)}")
        return jsonify({'success': False, 'message': f"Error downloading processed data: {str(e)}"}), 500

@app.route('/view_model/<scan_id>', methods=['GET'])
def view_model(scan_id):
    try:
        processed_dir = os.path.join(IMAGES_FOLDER, scan_id, "processed")
        if os.path.exists(processed_dir) and scan_id.startswith("scan_"):
            return render_template('view_model.html', scan_id=scan_id)
        else:
            return jsonify({'success': False, 'message': "Processed data not found"}), 404
    except Exception as e:
        logger.error(f"Error viewing model: {str(e)}")
        return jsonify({'success': False, 'message': f"Error viewing model: {str(e)}"}), 500

@app.route('/laser-on', methods=['POST'])
def laser_on():
    response = esp32_laser_on()
    if response:
        return jsonify({'success': True, 'message': "Laser turned ON"})
    else:
        return jsonify({'success': False, 'message': "Failed to turn laser ON"})

@app.route('/laser-off', methods=['POST'])
def laser_off():
    response = esp32_laser_off()
    if response:
        return jsonify({'success': True, 'message': "Laser turned OFF"})
    else:
        return jsonify({'success': False, 'message': "Failed to turn laser OFF"})

@app.route('/step-motor', methods=['POST'])
def step_motor():
    response = esp32_step_motor()
    if response:
        return jsonify({'success': True, 'message': "Motor stepped"})
    else:
        return jsonify({'success': False, 'message': "Failed to step motor"})

@app.route('/start-scan', methods=['POST'])
def api_start_scan():
    global scan_thread, scanning
    
    if scanning:
        return jsonify({'success': False, 'message': "Scan already in progress"})
    
    # Start scan in a separate thread
    scan_thread = threading.Thread(target=start_scan)
    scan_thread.daemon = True
    scan_thread.start()
    
    return jsonify({'success': True, 'message': "Scan started"})

@app.route('/stop-scan', methods=['POST'])
def api_stop_scan():
    global scanning
    
    if not scanning:
        return jsonify({'success': False, 'message': "No scan in progress"})
    
    scanning = False
    
    return jsonify({'success': True, 'message': "Scan stopping..."})

@app.route('/upload-image', methods=['POST'])
def upload_image():
    if 'image' not in request.files:
        return jsonify({'success': False, 'message': "No image provided"})
    
    try:
        image = request.files['image']
        step = request.form.get('step', '0')
        mode = request.form.get('mode', 'unknown')
        
        # Get current scan directory
        scan_dirs = [d for d in os.listdir(IMAGES_FOLDER) if os.path.isdir(os.path.join(IMAGES_FOLDER, d))]
        if not scan_dirs:
            return jsonify({'success': False, 'message': "No scan directory found"})
        
        latest_scan_dir = os.path.join(IMAGES_FOLDER, sorted(scan_dirs)[-1])
        
        # Save the image
        filename = f"image_{step}.jpg"
        save_path = os.path.join(latest_scan_dir, mode, filename)
        image.save(save_path)
        
        socketio.emit('log_message', {'message': f"Image saved: {filename} (Mode: {mode})"})
        return jsonify({'success': True, 'message': f"Image {filename} saved"})
    
    except Exception as e:
        logger.error(f"Error saving image: {str(e)}")
        return jsonify({'success': False, 'message': f"Error saving image: {str(e)}"})

@app.route('/crop_scan/<scan_id>', methods=['POST'])
def crop_scan_route(scan_id):
    try:
        data = request.json
        crop_coords = data.get('crop_coords')
        
        if not crop_coords or not all(k in crop_coords for k in ['x', 'y', 'width', 'height']):
            return jsonify({"success": False, "message": "Invalid crop coordinates"}), 400
        print(crop_coords, scan_id)
        result = crop_images(scan_id, crop_coords)
        
        if result["success"]:
            socketio.emit('log_message', {'message': result["message"]})
            return jsonify(result)
        else:
            return jsonify(result), 500
        
    except Exception as e:
        logger.error(f"Error handling crop request: {str(e)}")
        return jsonify({"success": False, "message": f"Error: {str(e)}"}), 500

@app.route('/preview_first_image/<scan_id>', methods=['GET'])
def preview_first_image(scan_id):
    try:
        scan_dir = os.path.join(IMAGES_FOLDER, scan_id)
        laser_on_dir = os.path.join(scan_dir, "laser_on")
        
        # Get the first image
        laser_on_files = sorted([f for f in os.listdir(laser_on_dir) if f.endswith(('.jpg', '.jpeg', '.png'))])
        if not laser_on_files:
            return jsonify({"success": False, "message": "No laser-on images found"}), 404
        
        first_image = laser_on_files[0]
        return send_from_directory(laser_on_dir, first_image)
        
    except Exception as e:
        logger.error(f"Error getting preview image: {str(e)}")
        return jsonify({"success": False, "message": f"Error: {str(e)}"}), 500


# Socket.IO Events
@socketio.on('connect')
def handle_connect():
    socketio.emit('log_message', {'message': f"Client connected: {request.sid}"})

@socketio.on('disconnect')
def handle_disconnect():
    socketio.emit('log_message', {'message': f"Client disconnected: {request.sid}"})
    
    # If this was a phone client, update the count
    if request.sid in connected_phones:
        connected_phones.remove(request.sid)
        socketio.emit('phones_count', {'count': len(connected_phones)})

@socketio.on('phone_connected')
def handle_phone_connected():
    connected_phones.add(request.sid)
    socketio.emit('log_message', {'message': f"Phone connected: {request.sid}"})
    socketio.emit('phones_count', {'count': len(connected_phones)})

    @socketio.on('image_captured')
    def handle_image_captured(data):
        socketio.emit('log_message', {'message': f"Image captured by phone: Step {data.get('step')}"})

    @socketio.on('clear_log')
    def handle_clear_log():
        socketio.emit('clear_log_response')

    @socketio.on('refresh_scans')
    def handle_refresh_scans():
        scans = get_all_scans()
        socketio.emit('update_scans_list', {'scans': scans})

@socketio.on('request_processing_status')
def handle_request_processing_status(data):
    scan_id = data.get('scan_id')
    if scan_id and scan_id in processing_status:
        if scan_id in processing_results and processing_results[scan_id]:
            latest_result = processing_results[scan_id][-1]
            socketio.emit('processing_status_update', {
                'scan_id': scan_id,
                'status': processing_status[scan_id]["status"],
                'latest_update': latest_result
            }, room=request.sid)
        else:
            socketio.emit('processing_status_update', {
                'scan_id': scan_id,
                'status': processing_status[scan_id]["status"],
                'latest_update': {"status": "waiting", "message": "Waiting for updates"}
            }, room=request.sid)
    else:
        socketio.emit('processing_status_update', {
            'scan_id': scan_id if scan_id else "unknown",
            'status': "not_found",
            'message': "Scan not found or processing not started"
        }, room=request.sid)

    # Periodic ESP32 status check
    def check_esp32_status():
        global esp32_connected
        while True:
            response = esp32_check_status()
            esp32_connected = response is not None
            socketio.emit('esp32_status', {'connected': esp32_connected})
            time.sleep(5)  # Check every 5 seconds

    # Start ESP32 status check thread
    status_thread = threading.Thread(target=check_esp32_status)
    status_thread.daemon = True
    status_thread.start()

if __name__ == '__main__':
    socketio.run(app, host=HOST, port=PORT, debug=DEBUG)
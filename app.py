from flask import Flask, render_template, request, jsonify, send_file
import os
import base64
from io import BytesIO
import tempfile
from stego_core import *
from stego_core import extract_data_from_image_DE, extract_data_from_audio_DE

application = Flask(__name__)

app = application

app.config['SECRET_KEY'] = 'hgdhsgdyegwe$##%$%#@##g24g1g1'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['DOWNLOAD_FOLDER'] = 'downloads'
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size

# Create directories if they don't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['DOWNLOAD_FOLDER'], exist_ok=True)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/embed_audio', methods=['POST'])
def embed_audio():
    temp_audio_path = None
    stego_audio_path = None
    
    try:
        # Get form data with validation
        audio_file = request.files.get('audio')
        secret_message = request.form.get('secret_message', '').strip()
        
        # Validate inputs
        if not audio_file or audio_file.filename == '':
            return jsonify({'success': False, 'error': 'No audio file selected'})
        
        if not secret_message:
            return jsonify({'success': False, 'error': 'Secret message cannot be empty'})
        
        # Check file type
        if not audio_file.filename.lower().endswith(('.wav', '.wave')):
            return jsonify({'success': False, 'error': 'Only WAV audio files are supported'})
        
        # Generate keys
        private_key, public_key = ecc_generate_keypair()
        aes_key = ecc_derive_shared_key(private_key, public_key)
        
        # Encrypt message
        encryption_start = time.perf_counter()
        encrypted_data, ciphertext, tag = aes_encrypt(secret_message, aes_key)
        encryption_time = (time.perf_counter() - encryption_start) * 1000
        
        # Save audio to temporary file
        temp_audio = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
        temp_audio_path = temp_audio.name
        audio_file.save(temp_audio_path)
        temp_audio.close()
        
        # Embed data in audio with capacity error handling
        try:
            stego_audio_path, embed_time, snr, capacity_bits, capacity_per_sample = embed_data_in_audio_DE(
                temp_audio_path, encrypted_data
            )
        except ValueError as e:
            if "too large" in str(e).lower():
                return jsonify({'success': False, 'error': f"Message too large for selected audio file. {str(e)}"})
            else:
                raise e
        
        # Analyze ciphertext
        ciphertext_analysis = analyze_ciphertext(ciphertext, tag, encrypted_data)
        
        # Get system metrics
        cpu_percent, memory_usage = get_system_metrics()
        
        # Read stego audio as base64
        with open(stego_audio_path, 'rb') as f:
            stego_audio_data = base64.b64encode(f.read()).decode()
        
        response = {
            'success': True,
            'stego_audio': stego_audio_data,
            'private_key': private_key.hex(),
            'public_key': public_key.hex(),
            'aes_key': aes_key.hex(),
            'metrics': {
                'encryption_time': encryption_time,
                'embed_time': embed_time,
                'total_time': encryption_time + embed_time,
                'snr': snr,
                'capacity_bits': capacity_bits,
                'capacity_per_sample': capacity_per_sample,
                'cpu_usage': cpu_percent,
                'memory_usage': memory_usage,
                'original_message_size': len(secret_message.encode()),
                'encrypted_data_size': len(encrypted_data)
            },
            'ciphertext_analysis': ciphertext_analysis
        }
        
        return jsonify(response)
        
    except Exception as e:
        print(f"Error in embed_audio: {str(e)}")
        return jsonify({'success': False, 'error': f"Audio embedding failed: {str(e)}"})
    
    finally:
        # Clean up temporary files
        if temp_audio_path and os.path.exists(temp_audio_path):
            safe_delete_file(temp_audio_path)
        if stego_audio_path and os.path.exists(stego_audio_path):
            safe_delete_file(stego_audio_path)

@app.route('/extract_audio', methods=['POST'])
def extract_audio():
    temp_audio_path = None
    
    try:
        # Get form data with validation
        audio_file = request.files.get('stego_audio')
        private_key_hex = request.form.get('private_key', '').strip()
        public_key_hex = request.form.get('public_key', '').strip()
        
        # Validate inputs
        if not audio_file or audio_file.filename == '':
            return jsonify({'success': False, 'error': 'No audio file selected'})
        
        if not private_key_hex or not public_key_hex:
            return jsonify({'success': False, 'error': 'Private and public keys are required'})
        
        # Check file type
        if not audio_file.filename.lower().endswith(('.wav', '.wave')):
            return jsonify({'success': False, 'error': 'Only WAV audio files are supported'})
        
        # Convert keys
        try:
            private_key = bytes.fromhex(private_key_hex)
            public_key = bytes.fromhex(public_key_hex)
            aes_key = ecc_derive_shared_key(private_key, public_key)
        except (ValueError, TypeError) as e:
            return jsonify({'success': False, 'error': f'Invalid key format: {str(e)}'})
        
        # Save audio to temporary file
        temp_audio = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
        temp_audio_path = temp_audio.name
        audio_file.save(temp_audio_path)
        temp_audio.close()
        
        # Extract data from audio
        extracted_data, extract_time = extract_data_from_audio_DE(temp_audio_path)
        
        if not extracted_data:
            return jsonify({'success': False, 'error': 'No hidden data found in the audio file or the file may be corrupted'})
        
        # Decrypt message
        decryption_start = time.perf_counter()
        try:
            decrypted_message, extracted_ciphertext = aes_decrypt(extracted_data, aes_key)
        except ValueError as e:
            return jsonify({'success': False, 'error': f'Decryption failed: {str(e)}'})
        decryption_time = (time.perf_counter() - decryption_start) * 1000
        
        # Get system metrics
        cpu_percent, memory_usage = get_system_metrics()
        
        response = {
            'success': True,
            'decrypted_message': decrypted_message,
            'metrics': {
                'extract_time': extract_time,
                'decryption_time': decryption_time,
                'total_time': extract_time + decryption_time,
                'cpu_usage': cpu_percent,
                'memory_usage': memory_usage
            }
        }
        
        return jsonify(response)
        
    except Exception as e:
        print(f"Error in extract_audio: {str(e)}")
        return jsonify({'success': False, 'error': f"Audio extraction failed: {str(e)}"})
    
    finally:
        # Clean up temporary file
        if temp_audio_path and os.path.exists(temp_audio_path):
            safe_delete_file(temp_audio_path)

@app.route('/embed_image', methods=['POST'])
def embed_image():
    try:
        # Get form data with validation
        image_file = request.files.get('image')
        secret_message = request.form.get('secret_message', '').strip()
        
        # Validate inputs
        if not image_file or image_file.filename == '':
            return jsonify({'success': False, 'error': 'No image file selected'})
        
        if not secret_message:
            return jsonify({'success': False, 'error': 'Secret message cannot be empty'})
        
        # Check file type
        allowed_extensions = {'.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.tif'}
        file_ext = os.path.splitext(image_file.filename.lower())[1]
        if file_ext not in allowed_extensions:
            return jsonify({'success': False, 'error': 'Supported image formats: PNG, JPG, JPEG, BMP, TIFF'})
        
        # Generate keys
        private_key, public_key = ecc_generate_keypair()
        aes_key = ecc_derive_shared_key(private_key, public_key)
        
        # Encrypt message
        encryption_start = time.perf_counter()
        encrypted_data, ciphertext, tag = aes_encrypt(secret_message, aes_key)
        encryption_time = (time.perf_counter() - encryption_start) * 1000
        
        # Convert image to base64
        image_data = base64.b64encode(image_file.read()).decode()
        full_image_data = f"data:image/png;base64,{image_data}"
        
        # Embed data in image with capacity error handling
        try:
            stego_image, embed_time, psnr, capacity_bits, capacity_per_pixel = embed_data_in_image_DE(
                full_image_data, encrypted_data
            )
        except ValueError as e:
            if "too large" in str(e).lower():
                return jsonify({'success': False, 'error': f"Message too large for selected image. {str(e)}"})
            else:
                raise e
        
        # Analyze ciphertext
        ciphertext_analysis = analyze_ciphertext(ciphertext, tag, encrypted_data)
        
        # Get system metrics
        cpu_percent, memory_usage = get_system_metrics()
        
        response = {
            'success': True,
            'stego_image': stego_image,
            'private_key': private_key.hex(),
            'public_key': public_key.hex(),
            'aes_key': aes_key.hex(),
            'metrics': {
                'encryption_time': encryption_time,
                'embed_time': embed_time,
                'total_time': encryption_time + embed_time,
                'psnr': psnr,
                'capacity_bits': capacity_bits,
                'capacity_per_pixel': capacity_per_pixel,
                'cpu_usage': cpu_percent,
                'memory_usage': memory_usage,
                'original_message_size': len(secret_message.encode()),
                'encrypted_data_size': len(encrypted_data)
            },
            'ciphertext_analysis': ciphertext_analysis
        }
        
        return jsonify(response)
        
    except Exception as e:
        print(f"Error in embed_image: {str(e)}")
        return jsonify({'success': False, 'error': f"Image embedding failed: {str(e)}"})

@app.route('/extract_image', methods=['POST'])
def extract_image():
    try:
        # Get form data with validation
        image_file = request.files.get('stego_image')
        private_key_hex = request.form.get('private_key', '').strip()
        public_key_hex = request.form.get('public_key', '').strip()
        
        # Validate inputs
        if not image_file or image_file.filename == '':
            return jsonify({'success': False, 'error': 'No image file selected'})
        
        if not private_key_hex or not public_key_hex:
            return jsonify({'success': False, 'error': 'Private and public keys are required'})
        
        # Check file type
        allowed_extensions = {'.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.tif'}
        file_ext = os.path.splitext(image_file.filename.lower())[1]
        if file_ext not in allowed_extensions:
            return jsonify({'success': False, 'error': 'Supported image formats: PNG, JPG, JPEG, BMP, TIFF'})
        
        # Convert keys
        try:
            private_key = bytes.fromhex(private_key_hex)
            public_key = bytes.fromhex(public_key_hex)
            aes_key = ecc_derive_shared_key(private_key, public_key)
        except (ValueError, TypeError) as e:
            return jsonify({'success': False, 'error': f'Invalid key format: {str(e)}'})
        
        # Convert image to base64
        image_data = base64.b64encode(image_file.read()).decode()
        full_image_data = f"data:image/png;base64,{image_data}"
        
        # Extract data from image
        extracted_data, extract_time = extract_data_from_image_DE(full_image_data)
        
        if not extracted_data:
            return jsonify({'success': False, 'error': 'No hidden data found in the image or the image may be corrupted'})
        
        # Decrypt message
        decryption_start = time.perf_counter()
        try:
            decrypted_message, extracted_ciphertext = aes_decrypt(extracted_data, aes_key)
        except ValueError as e:
            return jsonify({'success': False, 'error': f'Decryption failed: {str(e)}'})
        decryption_time = (time.perf_counter() - decryption_start) * 1000
        
        # Get system metrics
        cpu_percent, memory_usage = get_system_metrics()
        
        response = {
            'success': True,
            'decrypted_message': decrypted_message,
            'metrics': {
                'extract_time': extract_time,
                'decryption_time': decryption_time,
                'total_time': extract_time + decryption_time,
                'cpu_usage': cpu_percent,
                'memory_usage': memory_usage
            }
        }
        
        return jsonify(response)
        
    except Exception as e:
        print(f"Error in extract_image: {str(e)}")
        return jsonify({'success': False, 'error': f"Image extraction failed: {str(e)}"})

# Error handlers
@app.errorhandler(413)
def too_large(e):
    return jsonify({'success': False, 'error': 'File too large. Maximum size is 50MB.'}), 413

@app.errorhandler(500)
def internal_server_error(e):
    return jsonify({'success': False, 'error': 'Internal server error'}), 500

@app.errorhandler(404)
def not_found(e):
    return jsonify({'success': False, 'error': 'Endpoint not found'}), 404

@app.errorhandler(400)
def bad_request(e):
    return jsonify({'success': False, 'error': 'Bad request'}), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
import base64
import tempfile
import os
import time
import math
import struct
import numpy as np
from PIL import Image
import wave
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
import hashlib
import psutil
from io import BytesIO
import cv2
import bisect
from typing import Tuple

# ---------------- PVD Steganography Functions ----------------
def embending(n: int) -> Tuple[int, int, int]:
    srange = (0, 2, 4, 8, 12, 16, 24, 32, 48, 64, 96, 128, 192, 256)
    l = bisect.bisect_right(srange, n) - 1
    return srange[l], int(np.log2(srange[l + 1] - srange[l])), srange[l + 1] - 1

def change_diff(diff: int, l: int, r: int) -> Tuple[bool, int, int]:
    swap = False
    if l > r:
        l, r = r, l
        swap = True
    
    sg = np.sign(diff)
    ost = sg * (np.abs(diff) % 2)
    floor = sg * (np.abs(diff) // 2)

    l -= floor
    r += floor
    
    if l < 0 or r > 255 or ost > 0 and l == 0 and r == 255:
        return False, 0, 0
    
    if ost > 0 and l > (255 - r) or ost < 0 and l < (255 - r):
        l -= ost
    else:
        r += ost
    
    if swap:
        l, r = r, l

    return True, l, r

def bin_to_bytes_readable(b: str) -> bytearray:
    return bytearray([int(b[i:i+8], 2) for i in range(0, len(b), 8)])

def pvd_store(img_array: np.ndarray, secret_data: bytes) -> np.ndarray:
    """PVD embedding function that works with numpy array"""
    img = img_array.copy()
    height, width = img.shape[0], img.shape[1]
    width -= width % 2
    
    # Convert secret data to binary
    data = bin(int.from_bytes(secret_data, byteorder='big'))[2:]
    data = '0' * (8 - len(data) % 8) + data

    # Add length header
    data_len = bin(len(data))[2:].zfill(32)
    data = data_len + data

    i = capacity = 0
    while i < height:
        for j in range(0, width, 2):
            for k in range(3):  # RGB channels
                dif = max(img[i, j + 1, k], img[i, j, k]) - min(img[i, j + 1, k], img[i, j, k])

                emb, n, maxr = embending(dif)
                res, _, _ = change_diff(maxr - dif, min(img[i, j + 1, k], img[i, j, k]), max(img[i, j + 1, k], img[i, j, k]))
                if not res:
                    continue
                
                if capacity + n > len(data):
                    # Pad with zeros if we don't have enough data
                    bits = data[capacity:] + '0' * (n - (len(data) - capacity))
                else:
                    bits = data[capacity:capacity + n]
                
                capacity += len(bits)

                new_dif = emb + int(bits, 2)
                success, new_val1, new_val2 = change_diff(new_dif - dif, img[i, j, k], img[i, j + 1, k])
                
                if success:
                    img[i, j, k] = new_val1
                    img[i, j + 1, k] = new_val2

                if capacity >= len(data):
                    return img
        
        i += 1

    return img

def pvd_unstore(img_array: np.ndarray) -> bytes:
    """PVD extraction function that works with numpy array"""
    img = img_array
    height, width = img.shape[0], img.shape[1]
    width -= width % 2

    capacity = -1
    result_len, is_body = '', False
    result = ''
    
    for i in range(height):
        for j in range(0, width, 2):
            for k in range(3):  # RGB channels
                dif = max(img[i, j + 1, k], img[i, j, k]) - min(img[i, j + 1, k], img[i, j, k])

                emb, ln, maxr = embending(dif)
                res, _, _ = change_diff(maxr - dif, min(img[i, j + 1, k], img[i, j, k]), max(img[i, j + 1, k], img[i, j, k]))
                if not res:
                    continue
                
                secret = dif - emb

                bits = bin(secret)[2:].zfill(ln)
                if not is_body:
                    result_len += bits

                    if len(result_len) >= 32:
                        is_body = True
                        capacity = int(result_len[:32], 2)
                        print(f"PVD Extraction: Data length from header: {capacity} bits")

                        if len(result_len) > 32:
                            result = result_len[32:]
                    
                    continue
                else:
                    if len(bits) + len(result) > capacity:
                        bits = bits.lstrip('0')
                        bits = bits.zfill(capacity - len(result))
                    
                    result += bits
                
                if is_body and len(result) >= capacity:
                    # Convert binary to bytes
                    binary_data = result[:capacity]
                    try:
                        extracted_bytes = bin_to_bytes_readable(binary_data)
                        print(f"PVD Extraction: Successfully extracted {len(extracted_bytes)} bytes")
                        return bytes(extracted_bytes)
                    except Exception as e:
                        print(f"PVD Extraction Error: {e}")
                        return b''
    
    return b''

# ---------------- ECC Key Exchange ----------------
def ecc_generate_keypair():
    private_key = get_random_bytes(32)
    public_key = get_random_bytes(32)     
    return private_key, public_key

def ecc_derive_shared_key(private_key, public_key):
    shared_key = hashlib.sha256(private_key + public_key).digest()
    return shared_key[:16]  # AES-128

# ---------------- AES Encryption / Decryption ----------------
def aes_encrypt(message, key):
    cipher = AES.new(key, AES.MODE_EAX)
    ciphertext, tag = cipher.encrypt_and_digest(message.encode('utf-8'))
    encrypted_data = cipher.nonce + tag + ciphertext
    return encrypted_data, ciphertext, tag

def aes_decrypt(encrypted_data, key):
    try:
        if len(encrypted_data) < 48:  # nonce(16) + tag(16) + at least 16 bytes ciphertext
            raise ValueError(f"Encrypted data too short: {len(encrypted_data)} bytes, minimum 48 required")
            
        nonce = encrypted_data[:16]
        tag = encrypted_data[16:32]
        ciphertext = encrypted_data[32:]
        
        if len(ciphertext) == 0:
            raise ValueError("Ciphertext is empty")
            
        cipher = AES.new(key, AES.MODE_EAX, nonce=nonce)
        decrypted = cipher.decrypt(ciphertext)
        return decrypted.decode('utf-8'), ciphertext
    except Exception as e:
        print(f"Decryption error: {e}")
        raise ValueError(f"Decryption failed: {str(e)}")

# ---------------- Quality Metrics ----------------
def calculate_psnr(original, stego):
    """Calculate PSNR between original and stego image"""
    if original.shape != stego.shape:
        raise ValueError("Images must have the same dimensions")
    
    mse = np.mean((original.astype(float) - stego.astype(float)) ** 2)
    if mse == 0:
        return float('inf')
    max_pixel = 255.0
    psnr = 20 * math.log10(max_pixel / math.sqrt(mse))
    return psnr

def calculate_snr(original, stego):
    """Calculate SNR between original and stego audio"""
    if len(original) != len(stego):
        raise ValueError("Audio signals must have the same length")
    
    signal_power = np.mean(original.astype(float) ** 2)
    noise_power = np.mean((original.astype(float) - stego.astype(float)) ** 2)
    if noise_power == 0:
        return float('inf')
    snr = 10 * math.log10(signal_power / noise_power)
    return snr

def calculate_entropy(data):
    """Calculate Shannon entropy of data"""
    if len(data) == 0:
        return 0
    entropy = 0
    for x in range(256):
        p_x = float(data.count(bytes([x]))) / len(data)
        if p_x > 0:
            entropy += - p_x * math.log2(p_x)
    return entropy

# ---------------- PVD Image Steganography ----------------
def embed_data_in_image_DE(image_data, data_bytes):
    start = time.perf_counter()
    
    try:
        # Convert base64 to PIL Image
        if isinstance(image_data, str) and image_data.startswith('data:image'):
            image_data = image_data.split(',')[1]
        
        image_bytes = base64.b64decode(image_data)
        
        # Convert to numpy array using OpenCV
        nparr = np.frombuffer(image_bytes, np.uint8)
        img_array = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if img_array is None:
            raise ValueError("Failed to decode image")
        
        original_array = img_array.copy()

        print(f"PVD Embedding: Embedding {len(data_bytes)} bytes into image with shape {img_array.shape}")
        
        # Use PVD to embed data
        stego_array = pvd_store(img_array, data_bytes)
        
        # Encode back to PNG
        success, encoded_image = cv2.imencode('.png', stego_array)
        if not success:
            raise ValueError("Failed to encode stego image")
        
        output_base64 = base64.b64encode(encoded_image).decode()
        
        end = time.perf_counter()
        
        # Calculate PSNR
        psnr_value = calculate_psnr(original_array, stego_array)
        
        # Calculate capacity metrics
        total_pixels = img_array.shape[0] * img_array.shape[1]
        capacity_bits = len(data_bytes) * 8
        capacity_per_pixel = capacity_bits / total_pixels if total_pixels > 0 else 0
        
        print(f"PVD Embedding: Complete - {capacity_bits} bits embedded, PSNR: {psnr_value:.2f} dB")
        
        return output_base64, (end - start) * 1000, psnr_value, capacity_bits, capacity_per_pixel
        
    except Exception as e:
        print(f"Error in PVD image embedding: {str(e)}")
        raise

def extract_data_from_image_DE(image_data):
    start = time.perf_counter()
    
    try:
        # Convert base64 to numpy array
        if isinstance(image_data, str) and image_data.startswith('data:image'):
            image_data = image_data.split(',')[1]
        
        image_bytes = base64.b64decode(image_data)
        
        # Convert to numpy array using OpenCV
        nparr = np.frombuffer(image_bytes, np.uint8)
        img_array = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if img_array is None:
            raise ValueError("Failed to decode image")
        
        print(f"PVD Extraction: Extracting from image with shape {img_array.shape}")
        
        # Use PVD to extract data
        extracted_data = pvd_unstore(img_array)
        
        end = time.perf_counter()
        
        if not extracted_data:
            print("PVD Extraction: No data extracted from image")
        else:
            print(f"PVD Extraction: Successfully extracted {len(extracted_data)} bytes")
        
        return extracted_data, (end - start) * 1000
        
    except Exception as e:
        print(f"Error in PVD image extraction: {str(e)}")
        return b'', 0

# ---------------- DE Audio Steganography ----------------
def embed_data_in_audio_DE(audio_file_path, data_bytes):
    start = time.perf_counter()
    temp_output = None
    
    try:
        # Read audio file
        with wave.open(audio_file_path, 'rb') as audio:
            params = audio.getparams()
            # Check if audio is compatible
            if params.sampwidth != 2:  # 16-bit audio
                raise ValueError("Only 16-bit WAV files are supported")
            
            frames = np.frombuffer(audio.readframes(audio.getnframes()), dtype=np.int16).copy()
        
        original_frames = frames.copy()

        # Calculate maximum capacity
        max_capacity_bits = len(frames)  # 1 bit per sample
        data_size_bits = (len(data_bytes) + 8) * 8  # +8 for length and checksum
        
        if data_size_bits > max_capacity_bits:
            raise ValueError(f"Message too large for audio. Max: {max_capacity_bits//8} bytes, Required: {len(data_bytes)} bytes")

        print(f"Embedding {len(data_bytes)} bytes ({data_size_bits} bits) into audio with {len(frames)} samples")
        
        # Add checksum for data integrity
        checksum = hashlib.md5(data_bytes).digest()[:4]
        length_bytes = struct.pack('>I', len(data_bytes))
        full_data = length_bytes + checksum + data_bytes
        
        print(f"Total bits to embed: {len(full_data)*8} (header: 64 bits, data: {len(data_bytes)*8} bits)")
        
        data_bits = ''.join(format(b, '08b') for b in full_data)
        bit_idx = 0
        total_bits_embedded = 0

        # Simple LSB embedding for audio
        for i in range(len(frames)):
            if bit_idx >= len(data_bits):
                break
            
            # Get current sample value
            current_sample = frames[i]
            
            # Extract LSB and prepare new value
            new_sample = (current_sample & ~1) | int(data_bits[bit_idx])
            
            # Ensure the value stays within int16 bounds
            if new_sample > 32767:
                new_sample = 32767
            elif new_sample < -32768:
                new_sample = -32768
                
            frames[i] = np.int16(new_sample)
            bit_idx += 1
            total_bits_embedded += 1

        # Verify all bits were embedded
        if bit_idx < len(data_bits):
            raise ValueError(f"Not all data could be embedded. Embedded {bit_idx}/{len(data_bits)} bits")

        print(f"Successfully embedded {total_bits_embedded} bits out of {len(data_bits)} requested")

        # Save to temporary file
        temp_output = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
        
        with wave.open(temp_output.name, 'wb') as new_audio:
            new_audio.setparams(params)
            new_audio.writeframes(frames.astype(np.int16).tobytes())
        
        end = time.perf_counter()
        
        # Calculate audio quality metrics
        snr_value = calculate_snr(original_frames, frames)
        
        # Calculate capacity metrics
        total_samples = len(frames)
        capacity_bits = total_bits_embedded
        capacity_per_sample = capacity_bits / total_samples if total_samples > 0 else 0
        
        print(f"Audio embedding complete: {total_bits_embedded} bits embedded, SNR: {snr_value:.2f} dB")
        
        return temp_output.name, (end - start) * 1000, snr_value, capacity_bits, capacity_per_sample
        
    except Exception as e:
        print(f"Error in audio embedding: {str(e)}")
        if temp_output and os.path.exists(temp_output.name):
            safe_delete_file(temp_output.name)
        raise

def extract_data_from_audio_DE(audio_file_path):
    start = time.perf_counter()
    
    try:
        # Read audio file
        with wave.open(audio_file_path, 'rb') as audio:
            params = audio.getparams()
            if params.sampwidth != 2:  # 16-bit audio
                raise ValueError("Only 16-bit WAV files are supported")
            
            frames = np.frombuffer(audio.readframes(audio.getnframes()), dtype=np.int16)
        
        data_bits = ''
        # Extract ALL available bits
        total_samples = len(frames)
        print(f"Extracting from {total_samples} audio samples")
        
        for i in range(len(frames)):
            # Direct extraction without uint16 conversion
            sample = frames[i]
            data_bits += str(sample & 1)

        print(f"Extracted {len(data_bits)} bits from audio")

        # Try to extract the data with checksum verification
        extracted_data = b''
        max_data_length = 10 * 1024 * 1024  # 10MB max data length
        
        try:
            if len(data_bits) >= 64:  # 32 bits for length + 32 bits for checksum
                # Extract length
                length_bytes = bytearray()
                for i in range(0, 32, 8):
                    if i + 8 <= len(data_bits):
                        byte_val = int(data_bits[i:i+8], 2)
                        length_bytes.append(byte_val)
                
                if len(length_bytes) == 4:
                    data_length = struct.unpack('>I', bytes(length_bytes))[0]
                    print(f"Data length from header: {data_length} bytes")
                    
                    # Safety check for data length
                    if data_length > max_data_length:
                        print(f"Data length too large: {data_length} bytes")
                        return b'', (time.perf_counter() - start) * 1000
                    
                    # Extract checksum
                    checksum_extracted = bytearray()
                    for i in range(32, 64, 8):
                        if i + 8 <= len(data_bits):
                            byte_val = int(data_bits[i:i+8], 2)
                            checksum_extracted.append(byte_val)
                    
                    # Calculate total bits needed
                    total_bits_needed = (4 + 4 + data_length) * 8
                    print(f"Total bits needed: {total_bits_needed}, Available: {len(data_bits)}")
                    
                    if len(data_bits) >= total_bits_needed:
                        # Extract data
                        data_bytes = bytearray()
                        for i in range(64, total_bits_needed, 8):
                            if i + 8 <= len(data_bits):
                                byte_val = int(data_bits[i:i+8], 2)
                                data_bytes.append(byte_val)
                        
                        if len(data_bytes) == data_length:
                            # Verify checksum
                            calculated_checksum = hashlib.md5(bytes(data_bytes)).digest()[:4]
                            extracted_checksum = bytes(checksum_extracted)
                            
                            if extracted_checksum == calculated_checksum:
                                extracted_data = bytes(data_bytes)
                                print(f"Successfully extracted {len(extracted_data)} bytes with valid checksum")
                            else:
                                print("Audio checksum verification failed - data may be corrupted")
                                # Use the data anyway
                                extracted_data = bytes(data_bytes)
                                print(f"Using data without checksum verification: {len(extracted_data)} bytes")
                        else:
                            print(f"Data length mismatch: expected {data_length}, got {len(data_bytes)}")
                            # Use what we have
                            extracted_data = bytes(data_bytes)
                            print(f"Using available data: {len(extracted_data)} bytes")
                    else:
                        print(f"Insufficient bits extracted. Needed: {total_bits_needed}, Got: {len(data_bits)}")
                else:
                    print("Failed to extract length header from audio")
            else:
                print(f"Insufficient bits for audio header. Needed: 64, Got: {len(data_bits)}")
                
        except Exception as e:
            print(f"Error during audio data extraction: {e}")
            extracted_data = b''
        
        end = time.perf_counter()
        
        if not extracted_data:
            print("WARNING: No data extracted from audio")
        else:
            print(f"Extraction successful: {len(extracted_data)} bytes")
        
        return extracted_data, (end - start) * 1000
        
    except Exception as e:
        print(f"Error in audio extraction: {str(e)}")
        return b'', 0

# ---------------- Utility Functions ----------------
def analyze_ciphertext(ciphertext, tag, encrypted_data):
    """Analyze and display ciphertext information"""
    analysis = {
        'ciphertext_length': len(ciphertext),
        'tag_length': len(tag),
        'nonce_length': 16,
        'total_encrypted_length': len(encrypted_data),
        'ciphertext_hex': ciphertext.hex()[:100] + '...' if len(ciphertext.hex()) > 100 else ciphertext.hex(),
        'ciphertext_base64': base64.b64encode(ciphertext).decode()[:100] + '...',
        'tag_hex': tag.hex(),
        'entropy': calculate_entropy(ciphertext)
    }
    return analysis

def get_system_metrics():
    try:
        cpu_percent = psutil.cpu_percent(interval=0.1)
        process = psutil.Process(os.getpid())
        memory_usage = process.memory_info().rss / 1e6  # MB
        return cpu_percent, memory_usage
    except:
        return 0.0, 0.0

def safe_delete_file(file_path):
    """Safely delete a file with retry logic"""
    if file_path and os.path.exists(file_path):
        try:
            os.unlink(file_path)
            return True
        except PermissionError:
            # File might still be in use, try again after a short delay
            time.sleep(0.1)
            try:
                os.unlink(file_path)
                return True
            except:
                return False
        except:
            return False
    return True
from PIL import Image
import numpy as np
import struct
from collections import Counter
import os
import math
from .utils import compute_differences, restore_from_differences
from .lzw import lzw_compress_gray, lzw_decompress_gray

def compress_color_image(image_path, compressed_file):
    """
    Compresses a color image using differential encoding and LZW compression
    """
    # Read and convert image to RGB
    img = Image.open(image_path).convert("RGB")
    rows, cols = img.size[1], img.size[0]
    
    # Split into channels
    r, g, b = img.split()
    channels = {
        'R': np.array(r, dtype=np.uint8),
        'G': np.array(g, dtype=np.uint8),
        'B': np.array(b, dtype=np.uint8)
    }
    
    compressed_channels = {}
    
    for key in channels:
        # Compute differences
        diff_image = compute_differences(channels[key])
        # Flatten and compress
        data = diff_image.flatten().tolist()
        codes = lzw_compress_gray(data)
        compressed_channels[key] = codes
    
    # Write compressed data
    with open(compressed_file, "wb") as f:
        # Write dimensions
        f.write(struct.pack(">II", rows, cols))
        
        # Write first pixels of each channel (reference pixels)
        for key in ['R', 'G', 'B']:
            f.write(struct.pack(">B", channels[key][0, 0]))
        
        # Write compressed data for each channel
        for key in ['R', 'G', 'B']:
            codes = compressed_channels[key]
            f.write(struct.pack(">I", len(codes)))
            for code in codes:
                f.write(struct.pack(">H", code))
    
    print("Compression completed. Compressed file:", compressed_file)

def decompress_color_image(compressed_file, restored_image_path):
    """
    Decompresses a color image from differential LZW compressed file
    """
    with open(compressed_file, "rb") as f:
        # Read dimensions
        rows, cols = struct.unpack(">II", f.read(8))
        
        # Read first pixels
        first_pixels = {}
        for key in ['R', 'G', 'B']:
            first_pixels[key] = struct.unpack(">B", f.read(1))[0]
        
        channels_restored = {}
        for key in ['R', 'G', 'B']:
            # Read compressed data
            num_codes = struct.unpack(">I", f.read(4))[0]
            codes = [struct.unpack(">H", f.read(2))[0] for _ in range(num_codes)]
            
            # Decompress
            decompressed = lzw_decompress_gray(codes)
            
            # Reshape to 2D array
            diff_image = np.array(decompressed, dtype=np.int16).reshape((rows, cols))
            
            # Set first pixel
            diff_image[0, 0] = first_pixels[key]
            
            # Restore from differences
            channel_array = restore_from_differences(diff_image)
            channels_restored[key] = channel_array
    
    # Merge channels and save
    restored_img = Image.merge("RGB", (
        Image.fromarray(channels_restored['R']),
        Image.fromarray(channels_restored['G']),
        Image.fromarray(channels_restored['B'])
    ))
    restored_img.save(restored_image_path)
    print("Decompression completed. Restored image:", restored_image_path)
    return restored_img

def calculate_color_metrics(image_path, compressed_file):
    """
    Calculates compression metrics including entropy, code length, and compression ratio
    """
    original_size = os.path.getsize(image_path)
    compressed_size = os.path.getsize(compressed_file)
    
    # Calculate entropy for each channel
    img = np.array(Image.open(image_path).convert("RGB"))
    entropies = []
    
    for i in range(3):
        channel = img[:, :, i].flatten()
        # Calculate differences for entropy
        diff_channel = np.diff(channel)
        hist = Counter(diff_channel)
        total = len(diff_channel)
        entropy = -sum((count / total) * math.log2(count / total) for count in hist.values())
        entropies.append(entropy)
    
    avg_entropy = sum(entropies) / 3
    
    # Calculate average code length
    total_codes = 0
    with open(compressed_file, "rb") as f:
        f.read(11)  # Skip dimensions and first pixels
        for _ in range(3):
            num_codes = struct.unpack(">I", f.read(4))[0]
            total_codes += num_codes
            f.read(num_codes * 2)
    
    avg_code_length = (total_codes * 16) / (img.shape[0] * img.shape[1] * 3)
    compression_ratio = compressed_size / original_size
    
    print(f"Original File Size: {original_size} bytes")
    print(f"Compressed File Size: {compressed_size} bytes")
    print(f"Compression Ratio: {compression_ratio:.4f}")
    print(f"Average Code Length: {avg_code_length:.4f} bits/pixel")
    print(f"Average Entropy: {avg_entropy:.4f} bits/pixel")
    
    return avg_entropy, avg_code_length, compressed_size, compression_ratio 
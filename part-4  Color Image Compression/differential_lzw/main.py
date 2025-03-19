from src.compression import compress_color_image, decompress_color_image, calculate_color_metrics
from PIL import Image
import numpy as np
import os

def main():
    # Create output directory if it doesn't exist
    output_dir = "output"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Define file paths - assuming color_image.bmp is in the differential_lzw directory
    image_path = "color_image.bmp"
    compressed_file = os.path.join(output_dir, "compressed_diff_lzw.bin")
    restored_image_path = os.path.join(output_dir, "restored_diff_lzw.bmp")
    
    # Check if input image exists
    if not os.path.exists(image_path):
        print(f"Error: Input image '{image_path}' not found!")
        print("Please place your color_image.bmp in the differential_lzw directory.")
        return
    
    # Compression phase
    print("\nStarting compression...")
    compress_color_image(image_path, compressed_file)
    
    # Calculate metrics
    print("\nCalculating metrics...")
    calculate_color_metrics(image_path, compressed_file)
    
    # Decompression phase
    print("\nStarting decompression...")
    restored_img = decompress_color_image(compressed_file, restored_image_path)
    
    # Verify results
    print("\nVerifying results...")
    original_img = Image.open(image_path).convert("RGB")
    if np.array_equal(np.array(original_img), np.array(restored_img)):
        print("Success: Original and restored images are identical!")
        print(f"\nFiles saved in '{output_dir}' directory:")
        print(f"- Compressed file: {os.path.basename(compressed_file)}")
        print(f"- Restored image: {os.path.basename(restored_image_path)}")
    else:
        print("Error: Images differ.")

if __name__ == "__main__":
    main() 
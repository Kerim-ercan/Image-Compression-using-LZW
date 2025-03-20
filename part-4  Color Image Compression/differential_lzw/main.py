from src.compression import compress_color_image, decompress_color_image, calculate_color_metrics
from PIL import Image
import numpy as np
import os

def compare_images(original, restored):
    """
    Compare two images and show where they differ
    """
    orig_array = np.array(original)
    rest_array = np.array(restored)
    
 
    diff_mask = np.any(orig_array != rest_array, axis=2)
    diff_count = np.sum(diff_mask)
    
    if diff_count > 0:
        print(f"\nFound {diff_count} different pixels")
        
       
        diff_indices = np.where(diff_mask)
        for i in range(min(5, diff_count)):
            y, x = diff_indices[0][i], diff_indices[1][i]
            orig_pixel = orig_array[y, x]
            rest_pixel = rest_array[y, x]
            print(f"Position ({x}, {y}):")
            print(f"  Original: R={orig_pixel[0]}, G={orig_pixel[1]}, B={orig_pixel[2]}")
            print(f"  Restored: R={rest_pixel[0]}, G={rest_pixel[1]}, B={rest_pixel[2]}")
    else:
        print("Images are identical!")

def main():
   
    output_dir = "output"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
   
    image_path = "color_image.bmp"
    compressed_file = os.path.join(output_dir, "compressed_diff_lzw.bin")
    restored_image_path = os.path.join(output_dir, "restored_diff_lzw.bmp")
    
   
    if not os.path.exists(image_path):
        print(f"Error: Input image '{image_path}' not found!")
        print("Please place your color_image.bmp in the differential_lzw directory.")
        return
    

    print("\nStarting compression...")
    compress_color_image(image_path, compressed_file)
    
  
    print("\nCalculating metrics...")
    calculate_color_metrics(image_path, compressed_file)
    
    
    print("\nStarting decompression...")
    restored_img = decompress_color_image(compressed_file, restored_image_path)
    
    
    print("\nVerifying results...")
    original_img = Image.open(image_path).convert("RGB")
    if np.array_equal(np.array(original_img), np.array(restored_img)):
        print("Success: Original and restored images are identical!")
        print(f"\nFiles saved in '{output_dir}' directory:")
        print(f"- Compressed file: {os.path.basename(compressed_file)}")
        print(f"- Restored image: {os.path.basename(restored_image_path)}")
    else:
        print("Error: Images differ.")
        compare_images(original_img, restored_img)

if __name__ == "__main__":
    main() 
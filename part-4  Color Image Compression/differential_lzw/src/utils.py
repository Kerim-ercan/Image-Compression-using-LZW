import numpy as np

def compute_differences(channel):
    """
    Computes row-wise and column-wise differences for a channel
    Returns the difference image
    """
    rows, cols = channel.shape
    diff_image = np.zeros_like(channel, dtype=np.int16)
    
    # First pixel remains unchanged
    diff_image[0, 0] = channel[0, 0]
    
    # First row differences (left to right)
    for j in range(1, cols):
        diff_image[0, j] = int(channel[0, j]) - int(channel[0, j-1])
    
    # First column differences (top to bottom)
    for i in range(1, rows):
        diff_image[i, 0] = int(channel[i, 0]) - int(channel[i-1, 0])
    
    # Rest of the image (row by row)
    for i in range(1, rows):
        for j in range(1, cols):
            diff_image[i, j] = int(channel[i, j]) - int(channel[i, j-1])
    
    return diff_image

def restore_from_differences(diff_image):
    """
    Restores original image from differences
    """
    rows, cols = diff_image.shape
    restored = np.zeros_like(diff_image, dtype=np.uint8)
    
    # First pixel is unchanged
    restored[0, 0] = diff_image[0, 0]
    
    # Restore first row
    for j in range(1, cols):
        val = int(restored[0, j-1]) + int(diff_image[0, j])
        restored[0, j] = val % 256
    
    # Restore first column
    for i in range(1, rows):
        val = int(restored[i-1, 0]) + int(diff_image[i, 0])
        restored[i, 0] = val % 256
    
    # Restore rest of the image
    for i in range(1, rows):
        for j in range(1, cols):
            val = int(restored[i, j-1]) + int(diff_image[i, j])
            restored[i, j] = val % 256
    
    return restored 
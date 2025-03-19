# Differential LZW Image Compression

This project implements a color image compression algorithm that combines differential encoding with LZW compression. The algorithm works by:

1. Separating the color image into R, G, B channels
2. Computing pixel differences (both row-wise and column-wise)
3. Applying LZW compression to the differences
4. Storing the compressed data efficiently

## Features

- Lossless compression
- Handles color images (RGB)
- Combines differential encoding with LZW compression
- Calculates compression metrics (entropy, compression ratio, etc.)

## Requirements

- Python 3.6+
- PIL (Pillow)
- NumPy

Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

1. Place your color image (BMP format) in the same directory as main.py
2. Run the compression:
```bash
python main.py
```

The script will:
- Compress the image and save it as 'compressed_diff_lzw.bin'
- Decompress the image and save it as 'restored_diff_lzw.bmp'
- Display compression metrics
- Verify that the restored image matches the original

## Project Structure

```
differential_lzw/
├── src/
│   ├── __init__.py
│   ├── utils.py        # Difference computation utilities
│   ├── lzw.py         # LZW compression implementation
│   └── compression.py  # Color image compression functions
├── main.py            # Main script
├── requirements.txt   # Dependencies
└── README.md         # This file
```

## Metrics

The program calculates and displays:
- Original file size
- Compressed file size
- Compression ratio
- Average code length (bits/pixel)
- Average entropy (bits/pixel) 
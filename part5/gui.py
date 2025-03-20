from PIL import Image, ImageTk
import numpy as np
import os
import tkinter as tk
from tkinter import filedialog, messagebox
import struct
from collections import Counter
import math


current_directory = os.path.dirname(os.path.realpath(__file__))
image_file_path = os.path.join(current_directory, 'thumbs_up.bmp') 
compressed_file_path = os.path.join(current_directory, 'compressed.bin')
decompressed_image_path = os.path.join(current_directory, 'decompressed.bmp')
original_img = None
decompressed_img = None
compression_level = 1  


if not os.path.exists(image_file_path):
    print(f"Uyarı: Varsayılan resim dosyası bulunamadı: {image_file_path}")
   
    for file in os.listdir(current_directory):
        if file.endswith('.bmp'):
            image_file_path = os.path.join(current_directory, file)
            print(f"Alternatif resim dosyası kullanılıyor: {image_file_path}")
            break



def compute_differences(channel):
    """
    Computes row-wise and column-wise differences for a channel
    Returns the difference image
    """
    rows, cols = channel.shape
    diff_image = np.zeros_like(channel, dtype=np.int16)
    
  
    diff_image[:, 1:] = channel[:, 1:].astype(np.int16) - channel[:, :-1].astype(np.int16)
    
  
    diff_image[1:, 0] = channel[1:, 0].astype(np.int16) - channel[:-1, 0].astype(np.int16)
    
    return diff_image

def restore_from_differences(diff_image):
    """
    Restores original image from differences
    """
    rows, cols = diff_image.shape
    restored = np.zeros_like(diff_image, dtype=np.uint8)
   
    restored[0, 0] = diff_image[0, 0]  
    for i in range(1, rows):
        restored[i, 0] = (restored[i-1, 0] + diff_image[i, 0]) % 256
    
    
    for i in range(rows):
        for j in range(1, cols):
            restored[i, j] = (restored[i, j-1] + diff_image[i, j]) % 256
    
    return restored

def lzw_compress_gray(data):
    """Basic LZW compression for grayscale data"""
    dictionary = {bytes([i]): i for i in range(256)}
    dict_size = 256
    max_dict_size = 65536  
    w = bytes()
    compressed = []
    
    for pixel in data:
        if pixel < 0:
            pixel = 256 + pixel  
        
        wc = w + bytes([pixel % 256])
        if wc in dictionary:
            w = wc
        else:
            compressed.append(dictionary[w])
            if dict_size < max_dict_size:
                dictionary[wc] = dict_size
                dict_size += 1
            w = bytes([pixel % 256])
    
    if w:
        compressed.append(dictionary[w])
    return compressed

def lzw_decompress_gray(codes):
    """Basic LZW decompression for grayscale data"""
    dictionary = {i: bytes([i]) for i in range(256)}
    dict_size = 256
    w = bytes([codes.pop(0)])
    result = [w]
    
    for code in codes:
        if code in dictionary:
            entry = dictionary[code]
        elif code == dict_size:
            entry = w + w[:1]
        else:
            raise ValueError(f"Invalid compressed code: {code}")
        
        result.append(entry)
        dictionary[dict_size] = w + entry[:1]
        dict_size += 1
        w = entry
    
    decompressed = list(b''.join(result))
 
    return [(x - 256 if x > 127 else x) for x in decompressed]



def level1_compress(image_path, compressed_file):
    """Basic LZW compression without preprocessing"""
    img = Image.open(image_path).convert("L")
    pixels = np.array(img).flatten()
    
    compressed = lzw_compress_gray(pixels)
    
    with open(compressed_file, "wb") as f:
       
        width, height = img.size
        f.write(struct.pack(">II", height, width))
       
        f.write(struct.pack(">I", len(compressed)))
        for code in compressed:
            f.write(struct.pack(">H", code))
    
    return compressed_file

def level1_decompress(compressed_file, output_image_path):
    """Basic LZW decompression without postprocessing"""
    with open(compressed_file, "rb") as f:
       
        height, width = struct.unpack(">II", f.read(8))
   
        num_codes = struct.unpack(">I", f.read(4))[0]
        codes = [struct.unpack(">H", f.read(2))[0] for _ in range(num_codes)]
    
    decompressed = lzw_decompress_gray(codes)
    
   
    if len(decompressed) < width * height:
        decompressed.extend([0] * (width * height - len(decompressed)))
    elif len(decompressed) > width * height:
        decompressed = decompressed[:width * height]
    
    restored_img = Image.fromarray(np.array(decompressed, dtype=np.uint8).reshape((height, width)))
    restored_img.save(output_image_path)
    
    return restored_img


def level2_compress(image_path, compressed_file):
    """Difference encoding + LZW compression"""
    img = Image.open(image_path).convert("L")
    img_array = np.array(img, dtype=np.uint8)
    
 
    diff_image = compute_differences(img_array)
    data = diff_image.flatten().tolist()
    
   
    compressed = lzw_compress_gray(data)
    
    with open(compressed_file, "wb") as f:
      
        height, width = img_array.shape
        f.write(struct.pack(">II", height, width))
       
        f.write(struct.pack(">I", len(compressed)))
        for code in compressed:
            f.write(struct.pack(">H", code))
    
    return compressed_file

def level2_decompress(compressed_file, output_image_path):
    """LZW decompression + difference decoding"""
    with open(compressed_file, "rb") as f:
      
        height, width = struct.unpack(">II", f.read(8))
     
        num_codes = struct.unpack(">I", f.read(4))[0]
        codes = [struct.unpack(">H", f.read(2))[0] for _ in range(num_codes)]
    
    decompressed = lzw_decompress_gray(codes)
    

    if len(decompressed) < width * height:
        decompressed.extend([0] * (width * height - len(decompressed)))
    elif len(decompressed) > width * height:
        decompressed = decompressed[:width * height]
    

    diff_image = np.array(decompressed, dtype=np.int16).reshape((height, width))
    restored_array = restore_from_differences(diff_image)
    
    restored_img = Image.fromarray(restored_array)
    restored_img.save(output_image_path)
    
    return restored_img


def level3_compress(image_path, compressed_file):
    """RGB color image compression using differences + LZW"""
    img = Image.open(image_path).convert("RGB")
 
    width, height = img.size
    
    
    r, g, b = img.split()
    channels = {
        'R': np.array(r, dtype=np.uint8),
        'G': np.array(g, dtype=np.uint8),
        'B': np.array(b, dtype=np.uint8)
    }
    
 
    compressed_channels = {}
    for key in channels:
        diff_image = compute_differences(channels[key])
        data = diff_image.flatten().tolist()
        codes = lzw_compress_gray(data)
        compressed_channels[key] = codes
    

    with open(compressed_file, "wb") as f:
        f.write(struct.pack(">II", height, width))
      
        for key in ['R', 'G', 'B']:
            codes = compressed_channels[key]
            f.write(struct.pack(">I", len(codes)))
            for code in codes:
                f.write(struct.pack(">H", code))
    
    return compressed_file

def level3_decompress(compressed_file, output_image_path):
    """RGB color image decompression"""
    with open(compressed_file, "rb") as f:
        
        height, width = struct.unpack(">II", f.read(8))
        
        channels_restored = {}
        for key in ['R', 'G', 'B']:
            num_codes = struct.unpack(">I", f.read(4))[0]
            codes = [struct.unpack(">H", f.read(2))[0] for _ in range(num_codes)]
            
          
            decompressed = lzw_decompress_gray(codes)
            
          
            if len(decompressed) < width * height:
                decompressed.extend([0] * (width * height - len(decompressed)))
            elif len(decompressed) > width * height:
                decompressed = decompressed[:width * height]
            
           
            diff_image = np.array(decompressed, dtype=np.int16).reshape((height, width))
            channel_array = restore_from_differences(diff_image)
            channels_restored[key] = channel_array
    

    restored_img = Image.merge("RGB", (
        Image.fromarray(channels_restored['R']),
        Image.fromarray(channels_restored['G']),
        Image.fromarray(channels_restored['B'])
    ))
    restored_img.save(output_image_path)
    
    return restored_img


def level4_compress(image_path, compressed_file):
    return level3_compress(image_path, compressed_file)

def level4_decompress(compressed_file, output_image_path):
    return level3_decompress(compressed_file, output_image_path)

def level5_compress(image_path, compressed_file):
    return level3_compress(image_path, compressed_file)

def level5_decompress(compressed_file, output_image_path):
    return level3_decompress(compressed_file, output_image_path)



def calculate_metrics(image_path, compressed_file):
    """Calculate compression metrics"""
  
    original_size = os.path.getsize(image_path)
    compressed_size = os.path.getsize(compressed_file)
    
   
    img = Image.open(image_path).convert("L")
    pixels = np.array(img).flatten()
    hist = Counter(pixels)
    total = len(pixels)
    entropy = -sum((count / total) * math.log2(count / total) for count in hist.values())
    
 
    with open(compressed_file, "rb") as f:
       
        f.read(8)
        if compression_level == 3 or compression_level == 4 or compression_level == 5:
          
            total_codes = 0
            for _ in range(3):
                num_codes = struct.unpack(">I", f.read(4))[0]
                total_codes += num_codes
                f.read(num_codes * 2)  
            avg_code_length = (total_codes * 16) / (img.size[0] * img.size[1] * 3)
        else:
          
            num_codes = struct.unpack(">I", f.read(4))[0]
            avg_code_length = (num_codes * 16) / (img.size[0] * img.size[1])
    
    compression_ratio = compressed_size / original_size
    
    return entropy, avg_code_length, original_size, compressed_size, compression_ratio



def start():
    """Main function to create and start the GUI"""
    global original_img, decompressed_img
    
 
    gui = tk.Tk()
    gui.title('LZW Image Compression')
    gui['bg'] = 'royal blue'
    
 
    frame = tk.Frame(gui)
    frame.grid(row=0, column=0, padx=15, pady=15)
    frame['bg'] = 'royal blue'
    
   
    menu_bar = tk.Menu(gui)
    gui.config(menu=menu_bar)
    
  
    file_menu = tk.Menu(menu_bar, tearoff=0)
    menu_bar.add_cascade(label="File", menu=file_menu)
    file_menu.add_command(label="Open Image", command=lambda: open_image(original_img_panel, decompressed_img_panel))
    file_menu.add_command(label="Exit", command=gui.quit)
    
    methods_menu = tk.Menu(menu_bar, tearoff=0)
    menu_bar.add_cascade(label="Methods", menu=methods_menu)
    
  
    methods_menu.add_command(label="Level 1: Compression", command=lambda: set_compression_level(1))
    methods_menu.add_command(label="Level 1: Decompression", command=lambda: decompress_image())
    methods_menu.add_command(label="Level 2: Compression", command=lambda: set_compression_level(2))
    methods_menu.add_command(label="Level 2: Decompression", command=lambda: decompress_image())
    methods_menu.add_command(label="Level 3: Compression", command=lambda: set_compression_level(3))
    methods_menu.add_command(label="Level 3: Decompression", command=lambda: decompress_image())
    methods_menu.add_command(label="Level 4: Compression", command=lambda: set_compression_level(4))
    methods_menu.add_command(label="Level 4: Decompression", command=lambda: decompress_image())
    methods_menu.add_command(label="Level 5: Compression", command=lambda: set_compression_level(5))
    methods_menu.add_command(label="Level 5: Decompression", command=lambda: decompress_image())
    
   
    img_frame = tk.Frame(frame, bg='royal blue')
    img_frame.grid(row=0, column=0, padx=10, pady=10)
    
  
    original_label = tk.Label(img_frame, text="Original Image", bg='royal blue', fg='white')
    original_label.grid(row=0, column=0, padx=5, pady=5)
    
 
    if os.path.exists(image_file_path):
        try:
            original_img = ImageTk.PhotoImage(file=image_file_path)
        except Exception as e:
            print(f"Resim yüklenirken hata: {e}")
         
            dummy_img = Image.new('RGB', (200, 200), color='gray')
            original_img = ImageTk.PhotoImage(image=dummy_img)
    else:
        
        dummy_img = Image.new('RGB', (200, 200), color='gray')
        original_img = ImageTk.PhotoImage(image=dummy_img)
        
    original_img_panel = tk.Label(img_frame, image=original_img)
    original_img_panel.grid(row=1, column=0, padx=10, pady=10)
    
   
    decompressed_label = tk.Label(img_frame, text="Decompressed Image", bg='royal blue', fg='white')
    decompressed_label.grid(row=0, column=1, padx=5, pady=5)
    

    if 'dummy_img' in locals():
        decompressed_img = ImageTk.PhotoImage(image=dummy_img)  
    else:
        decompressed_img = ImageTk.PhotoImage(file=image_file_path)  
        
    decompressed_img_panel = tk.Label(img_frame, image=decompressed_img)
    decompressed_img_panel.grid(row=1, column=1, padx=10, pady=10)
    

    metrics_frame = tk.Frame(frame, bg='royal blue')
    metrics_frame.grid(row=1, column=0, padx=10, pady=10, sticky='w')
    
    
    entropy_label = tk.Label(metrics_frame, text="Entropy: ", bg='royal blue', fg='white')
    entropy_label.grid(row=0, column=0, sticky='w', padx=5, pady=2)
    
    avg_code_length_label = tk.Label(metrics_frame, text="Average Code Length: ", bg='royal blue', fg='white')
    avg_code_length_label.grid(row=1, column=0, sticky='w', padx=5, pady=2)
    
    comp_ratio_label = tk.Label(metrics_frame, text="Compression Ratio: ", bg='royal blue', fg='white')
    comp_ratio_label.grid(row=2, column=0, sticky='w', padx=5, pady=2)
    
    input_size_label = tk.Label(metrics_frame, text="Input Image size: ", bg='royal blue', fg='white')
    input_size_label.grid(row=3, column=0, sticky='w', padx=5, pady=2)
    
    comp_size_label = tk.Label(metrics_frame, text="Compressed Image size: ", bg='royal blue', fg='white')
    comp_size_label.grid(row=4, column=0, sticky='w', padx=5, pady=2)
    
    diff_label = tk.Label(metrics_frame, text="Difference: ", bg='royal blue', fg='white')
    diff_label.grid(row=5, column=0, sticky='w', padx=5, pady=2)
    
   
    button_frame = tk.Frame(frame, bg='royal blue')
    button_frame.grid(row=2, column=0, padx=10, pady=10)
    
 
    color_btn = tk.Button(button_frame, text="Color", width=10, command=lambda: display_color_mode(original_img_panel, 'color'))
    color_btn.grid(row=0, column=0, padx=5)
    
    grayscale_btn = tk.Button(button_frame, text="GrayScale", width=10, bg='gray', command=lambda: display_color_mode(original_img_panel, 'gray'))
    grayscale_btn.grid(row=0, column=1, padx=5)
    
    red_btn = tk.Button(button_frame, text="Red", width=10, bg='red', command=lambda: display_color_mode(original_img_panel, 'red'))
    red_btn.grid(row=0, column=2, padx=5)
    
    green_btn = tk.Button(button_frame, text="Green", width=10, bg='SpringGreen2', command=lambda: display_color_mode(original_img_panel, 'green'))
    green_btn.grid(row=0, column=3, padx=5)
    
    blue_btn = tk.Button(button_frame, text="Blue", width=10, bg='DodgerBlue2', command=lambda: display_color_mode(original_img_panel, 'blue'))
    blue_btn.grid(row=0, column=4, padx=5)
    
    
    compress_btn = tk.Button(frame, text=f"Compress (Level {compression_level})", width=20, command=lambda: compress_image(original_img_panel, decompressed_img_panel, entropy_label, avg_code_length_label, comp_ratio_label, input_size_label, comp_size_label, diff_label))
    compress_btn.grid(row=3, column=0, pady=10)
    
   
    gui.mainloop()

def open_image(original_panel, decompressed_panel):
    """Open an image file and display it"""
    global image_file_path, original_img, decompressed_img
    
    file_path = filedialog.askopenfilename(
        initialdir=current_directory,
        title='Select an image file',
        filetypes=[('Image files', '*.bmp;*.png;*.jpg;*.jpeg')]
    )
    
    if file_path == '':
        messagebox.showinfo('Warning', 'No image file is selected/opened.')
    else:
        image_file_path = file_path
        original_img = ImageTk.PhotoImage(file=image_file_path)
        original_panel.config(image=original_img)
        original_panel.photo_ref = original_img
        
       
        decompressed_img = ImageTk.PhotoImage(file=image_file_path)
        decompressed_panel.config(image=decompressed_img)
        decompressed_panel.photo_ref = decompressed_img

def set_compression_level(level):
    """Set the compression level and update the compress button text"""
    global compression_level
    compression_level = level
   
    print(f"Compression level set to {level}")

def display_color_mode(image_panel, mode):
    """Display the image in different color modes"""
    global image_file_path
    
    try:
  
        if not os.path.exists(image_file_path):
            messagebox.showerror("Hata", "Görüntülenecek resim dosyası bulunamadı.")
            return
            
        img_rgb = Image.open(image_file_path)
        
        if mode == 'gray':
            img_display = img_rgb.convert('L')
        elif mode == 'red':
            r, g, b = img_rgb.split()
            zeros = Image.new('L', img_rgb.size, 0)
            img_display = Image.merge('RGB', (r, zeros, zeros))
        elif mode == 'green':
            r, g, b = img_rgb.split()
            zeros = Image.new('L', img_rgb.size, 0)
            img_display = Image.merge('RGB', (zeros, g, zeros))
        elif mode == 'blue':
            r, g, b = img_rgb.split()
            zeros = Image.new('L', img_rgb.size, 0)
            img_display = Image.merge('RGB', (zeros, zeros, b))
        else:  
            img_display = img_rgb
        
        img = ImageTk.PhotoImage(image=img_display)
        image_panel.config(image=img)
        image_panel.photo_ref = img
    except Exception as e:
        messagebox.showerror("Hata", f"Resim görüntülenirken bir hata oluştu: {str(e)}")

def compress_image(original_panel, decompressed_panel, entropy_label, avg_code_label, ratio_label, input_size_label, comp_size_label, diff_label):
    """Compress the image using selected compression level"""
    global compression_level, compressed_file_path
    
    try:
       
        if compression_level == 1:
            level1_compress(image_file_path, compressed_file_path)
        elif compression_level == 2:
            level2_compress(image_file_path, compressed_file_path)
        elif compression_level == 3:
            level3_compress(image_file_path, compressed_file_path)
        elif compression_level == 4:
            level4_compress(image_file_path, compressed_file_path)
        elif compression_level == 5:
            level5_compress(image_file_path, compressed_file_path)
        
       
        entropy, avg_code_length, original_size, compressed_size, compression_ratio = calculate_metrics(image_file_path, compressed_file_path)
        
       
        entropy_label.config(text=f"Entropy: {entropy:.4f} bits/pixel")
        avg_code_label.config(text=f"Average Code Length: {avg_code_length:.4f} bits/pixel")
        ratio_label.config(text=f"Compression Ratio: {compression_ratio:.4f}")
        input_size_label.config(text=f"Input Image size: {original_size} bytes")
        comp_size_label.config(text=f"Compressed Image size: {compressed_size} bytes")
        diff_label.config(text=f"Difference: {original_size - compressed_size} bytes")
        
        messagebox.showinfo("Success", f"Image compressed successfully using level {compression_level}!")
        
    except Exception as e:
        messagebox.showerror("Error", f"Compression failed: {str(e)}")

def decompress_image():
    """Decompress the image using selected compression level"""
    global compression_level, compressed_file_path, decompressed_image_path, decompressed_img
    
    try:
       
        if compression_level == 1:
            restored_img = level1_decompress(compressed_file_path, decompressed_image_path)
        elif compression_level == 2:
            restored_img = level2_decompress(compressed_file_path, decompressed_image_path)
        elif compression_level == 3:
            restored_img = level3_decompress(compressed_file_path, decompressed_image_path)
        elif compression_level == 4:
            restored_img = level4_decompress(compressed_file_path, decompressed_image_path)
        elif compression_level == 5:
            restored_img = level5_decompress(compressed_file_path, decompressed_image_path)
        
      
        decompressed_img = ImageTk.PhotoImage(image=restored_img)
        image_panel = tk._default_root.children['!frame'].children['!frame']
        decompressed_panel = image_panel.children['!label2']
        decompressed_panel.config(image=decompressed_img)
        decompressed_panel.photo_ref = decompressed_img
        
        messagebox.showinfo("Success", f"Image decompressed successfully using level {compression_level}!")
        
    except Exception as e:
        messagebox.showerror("Error", f"Decompression failed: {str(e)}")

if __name__ == '__main__':
    start()
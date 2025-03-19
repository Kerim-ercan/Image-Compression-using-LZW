from PIL import Image
import numpy as np
import os
import math
import struct
from collections import Counter


# --- LZW Sıkıştırma ve Açma Fonksiyonları (Gray-Scale için) ---

def compute_differences(channel):
    """
    Computes row-wise and column-wise differences for a channel
    Returns the difference image
    """
    rows, cols = channel.shape
    diff_image = np.zeros_like(channel, dtype=np.int16)
    
    # Row-wise differences (starting from second pixel in each row)
    diff_image[:, 1:] = channel[:, 1:].astype(np.int16) - channel[:, :-1].astype(np.int16)
    
    # Column-wise differences for first column (starting from second pixel)
    diff_image[1:, 0] = channel[1:, 0].astype(np.int16) - channel[:-1, 0].astype(np.int16)
    
    return diff_image

def restore_from_differences(diff_image):
    """
    Restores original image from differences
    """
    rows, cols = diff_image.shape
    restored = np.zeros_like(diff_image, dtype=np.uint8)
    
    # Restore first column
    restored[0, 0] = diff_image[0, 0]  # First pixel remains unchanged
    for i in range(1, rows):
        restored[i, 0] = (restored[i-1, 0] + diff_image[i, 0]) % 256
    
    # Restore rest of the image row by row
    for i in range(rows):
        for j in range(1, cols):
            restored[i, j] = (restored[i, j-1] + diff_image[i, j]) % 256
    
    return restored

def lzw_compress_gray(data):
    dictionary = {bytes([i]): i for i in range(256)}
    dict_size = 256
    max_dict_size = 65536  # 16-bit limit
    w = bytes()
    compressed = []
    
    for pixel in data:
        # Convert negative differences to positive representation
        if pixel < 0:
            pixel = 256 + pixel  # Map negative values to upper range
        
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
    # Convert back to signed values if necessary
    return [(x - 256 if x > 127 else x) for x in decompressed]


# --- Renkli Görüntü için Sıkıştırma ve Açma Fonksiyonları ---

def compress_color_image(image_path, compressed_file):
    """
    1. Renkli resmi açar ve RGB bileşenlerine ayırır (her biri bir gri seviye görüntüsüdür).
    2. Her kanal için LZW ile sıkıştırma uygular.
    3. Sıkıştırılmış kodları ve görüntü boyut bilgisini tek bir binary dosyada saklar.
    4. Ayrıca her kanal için metrikler hesaplanabilir.
    """
    # Resmi aç ve RGB'ye çevir
    img = Image.open(image_path).convert("RGB")
    # Görüntü boyutları (tüm kanallar aynı boyutta)
    rows, cols = img.size[1], img.size[0]  # Pillow'da (width, height) olduğundan dikkat!

    # Kanal ayrımı (R, G, B)
    r, g, b = img.split()
    channels = {'R': np.array(r, dtype=np.uint8),
                'G': np.array(g, dtype=np.uint8),
                'B': np.array(b, dtype=np.uint8)}

    # Her kanal için sıkıştırılmış kodları saklamak üzere bir yapı oluşturuyoruz
    compressed_channels = {}

    for key in channels:
        # Compute differences
        diff_image = compute_differences(channels[key])
        # Flatten and compress
        data = diff_image.flatten().tolist()
        codes = lzw_compress_gray(data)
        compressed_channels[key] = codes

    # Sıkıştırılmış veriyi dosyaya yazıyoruz.
    # Dosya formatı:
    # 1) 4 byte: rows (unsigned int, big endian)
    # 2) 4 byte: cols (unsigned int)
    # Sonra her kanal için sırasıyla:
    # 3) 4 byte: Kanalın kod sayısı (N)
    # 4) N adet 2 byte: Her kod (unsigned short, big endian)
    with open(compressed_file, "wb") as f:
        f.write(struct.pack(">I", rows))
        f.write(struct.pack(">I", cols))
        # Kanallar R, G, B sırasıyla yazılıyor.
        for key in ['R', 'G', 'B']:
            codes = compressed_channels[key]
            f.write(struct.pack(">I", len(codes)))  # Kanal kod sayısı
            for code in codes:
                f.write(struct.pack(">H", code))  # Her kodu 2 bayt olarak yazıyoruz (H: unsigned short)
    print("Sıkıştırma tamamlandı. Sıkıştırılmış dosya:", compressed_file)


def decompress_color_image(compressed_file, restored_image_path):
    """
    Sıkıştırılmış dosyayı açar, içindeki bilgiden RGB kanallarını LZW açma yöntemiyle geri getirir,
    orijinal boyutlara yeniden şekillendirir ve restore edilmiş renkli resmi oluşturur.
    """
    with open(compressed_file, "rb") as f:
        # Görüntü boyutlarını oku.
        rows = struct.unpack(">I", f.read(4))[0]
        cols = struct.unpack(">I", f.read(4))[0]
        channels_restored = {}
        for key in ['R', 'G', 'B']:
            # Her kanal için kod sayısını oku.
            num_codes = struct.unpack(">I", f.read(4))[0]
            codes = [struct.unpack(">H", f.read(2))[0] for _ in range(num_codes)]  # 2 bayt okuyoruz
            # LZW açma işlemi
            decompressed = lzw_decompress_gray(codes)
            # Yeniden 2D'ye dönüştür (uint8 formatına çeviriyoruz)
            diff_image = np.array(decompressed, dtype=np.int16).reshape((rows, cols))
            # Restore from differences
            channel_array = restore_from_differences(diff_image)
            channels_restored[key] = channel_array

    # Kanalları birleştirip renkli görüntü oluşturuyoruz.
    restored_img = Image.merge("RGB", (Image.fromarray(channels_restored['R']),
                                       Image.fromarray(channels_restored['G']),
                                       Image.fromarray(channels_restored['B'])))
    restored_img.save(restored_image_path)
    print("Açma tamamlandı. Restore edilmiş resim:", restored_image_path)
    return restored_img


def calculate_color_metrics(image_path, compressed_file):
    """
    Orijinal resim ve sıkıştırılmış dosya üzerinden metrikleri hesaplar:
    - Entropi (her kanal için ayrı ayrı hesaplanıp ortalaması alınabilir)
    - Ortalama kod uzunluğu (tüm kanalların toplam kod sayısı üzerinden)
    - Sıkıştırılmış dosya boyutu
    - Sıkıştırma oranı
    """
    # Orijinal resmin dosya boyutunu alıyoruz
    original_size = os.path.getsize(image_path)
    compressed_size = os.path.getsize(compressed_file)

    # Açık resmi numpy array'e çevir (RGB)
    img = np.array(Image.open(image_path).convert("RGB"))
    # Entropi: Her kanalın histogramı hesaplanıp ortalaması alınabilir.
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

    # Ortalama kod uzunluğunu hesaplamak için,
    # dosyadaki toplam bit sayısı bölünmüş toplam sembol sayısı (R+G+B)
    total_codes = 0
    with open(compressed_file, "rb") as f:
        f.read(8)  # rows, cols
        for _ in range(3):
            num_codes = struct.unpack(">I", f.read(4))[0]
            total_codes += num_codes
            f.read(num_codes * 2)  # 2 bayt okuyoruz her kod için
    # Her kodu 2 bayt = 16 bit olarak sakladığımızı varsayarsak:
    avg_code_length = (total_codes * 16) / (img.shape[0] * img.shape[1] * 3)  # bit/piksel

    compression_ratio = compressed_size / original_size

    print(f"Orijinal Dosya Boyutu: {original_size} byte")
    print(f"Sıkıştırılmış Dosya Boyutu: {compressed_size} byte")
    print(f"Compression Ratio: {compression_ratio:.4f}")
    print(f"Ortalama Kod Uzunluğu: {avg_code_length:.4f} bit/piksel")
    print(f"Ortalama Entropi: {avg_entropy:.4f} bit/piksel")

    return avg_entropy, avg_code_length, compressed_size, compression_ratio


# --- Ana Program Bloğu ---

if __name__ == "__main__":
    image_path = "color_image.bmp"  # Renkli görüntü dosyanızın yolu
    compressed_file = "compressed_diff_lzw.bin"
    restored_image_path = "restored_diff_lzw.bmp"

    # Sıkıştırma aşaması
    compress_color_image(image_path, compressed_file)
    calculate_color_metrics(image_path, compressed_file)

    # Açma (Decompression) aşaması
    restored_img = decompress_color_image(compressed_file, restored_image_path)

    # Karşılaştırma: Orijinal ve açılmış görüntüleri piksel bazında kontrol edelim.
    original_img = Image.open(image_path).convert("RGB")
    if np.array_equal(np.array(original_img), np.array(restored_img)):
        print("Başarılı: Orijinal ve restore edilmiş görüntüler aynı!")
    else:
        print("Hata: Görüntüler arasında fark var.")

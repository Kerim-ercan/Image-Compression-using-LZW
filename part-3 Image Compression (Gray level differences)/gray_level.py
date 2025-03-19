from PIL import Image
import numpy as np
import os
from collections import Counter
import math


def compute_difference_image(img_array):
    """
    Verilen 2D numpy dizisi (gri ton resim) için fark görüntüsünü hesaplar.
    - İlk piksel (0,0) orijinal değeri korur.
    - İlk satırda, 2. pikselden itibaren, solundaki piksel ile fark alınır.
    - Diğer satırlarda, ilk sütun üst satır ile fark, diğer sütunlar ise satır farkı kullanılarak hesaplanır.
    """
    rows, cols = img_array.shape
    diff_img = np.zeros((rows, cols), dtype=np.int16)
    diff_img[0, 0] = img_array[0, 0]
    # İlk satır (satır 0) için:
    diff_img[0, 1:] = img_array[0, 1:] - img_array[0, :-1]
    # Diğer satırlar için:
    for i in range(1, rows):
        # İlk sütun: sütun farkı
        diff_img[i, 0] = img_array[i, 0] - img_array[i - 1, 0]
        # Diğer sütunlar: satır farkı
        diff_img[i, 1:] = img_array[i, 1:] - img_array[i, :-1]
    return diff_img


def lzw_compress(integers, compressed_file):
    """
    LZW sıkıştırması, integer dizisi (fark dizisi) üzerinde uygulanır.
    Başlangıç sözlüğü, farkların olası aralığı -255 ile 255 olarak oluşturulur.
    Sıkıştırılmış kodlar, her biri 2 bayt olarak 'compressed_file' dosyasına yazılır.
    """
    # Başlangıç sözlüğü: her sembolü tek elemanlı tuple olarak saklıyoruz.
    dictionary = {(i,): i + 255 for i in range(-255, 256)}
    dict_size = len(dictionary)
    w = ()
    compressed = []
    for symbol in integers:
        wc = w + (symbol,)
        if wc in dictionary:
            w = wc
        else:
            compressed.append(dictionary[w])
            dictionary[wc] = dict_size
            dict_size += 1
            w = (symbol,)
    if w:
        compressed.append(dictionary[w])

    # Sıkıştırılmış kodları dosyaya yazma (her kod 2 bayt)
    with open(compressed_file, "wb") as f:
        for code in compressed:
            f.write(code.to_bytes(2, byteorder='big'))
    return compressed


def lzw_decompress(compressed_file):
    """
    LZW açma işlemi: Sıkıştırılmış dosyadan kodlar okunur ve
    başlangıç sözlüğü (fark aralığı -255 ile 255) ile orijinal fark dizisi elde edilir.
    """
    # Dosyadaki kodları oku
    file_size = os.path.getsize(compressed_file)
    with open(compressed_file, "rb") as f:
        codes = [int.from_bytes(f.read(2), byteorder='big') for _ in range(file_size // 2)]

    # Başlangıç sözlüğü
    dictionary = {i + 255: (i,) for i in range(-255, 256)}
    dict_size = len(dictionary)

    # İlk kodu al ve ilgili tuple'ı belirle
    result = []
    first_code = codes.pop(0)
    w = dictionary[first_code]
    result.extend(w)

    for code in codes:
        if code in dictionary:
            entry = dictionary[code]
        elif code == dict_size:
            entry = w + (w[0],)
        else:
            raise ValueError("Geçersiz sıkıştırılmış kod: %s" % code)
        result.extend(entry)
        dictionary[dict_size] = w + (entry[0],)
        dict_size += 1
        w = entry
    return result


def restore_image_from_diff(diff_img):
    """
    Fark görüntüsünden orijinal görüntüyü geri kazanır.
    - İlk satırdaki pikseller, soldan sağa kümülatif toplanır.
    - İlk sütundaki (ilk piksel hariç) pikseller, üstteki piksel ile toplanır.
    - Diğer pikseller, satır içindeki önceki piksele fark eklenerek hesaplanır.
    """
    rows, cols = diff_img.shape
    restored = np.zeros((rows, cols), dtype=np.int16)
    restored[0, 0] = diff_img[0, 0]
    # İlk satır
    for j in range(1, cols):
        restored[0, j] = restored[0, j - 1] + diff_img[0, j]
    # Diğer satırlar
    for i in range(1, rows):
        restored[i, 0] = restored[i - 1, 0] + diff_img[i, 0]
        for j in range(1, cols):
            restored[i, j] = restored[i, j - 1] + diff_img[i, j]
    # Değerleri 0-255 aralığına getir
    restored = np.clip(restored, 0, 255).astype(np.uint8)
    return restored


def calculate_metrics(original_img, compressed_file, num_symbols):
    """
    - Entropi: Fark görüntüsündeki sembollerin olasık dağılımı.
    - Ortalama kod uzunluğu: Sıkıştırılmış dosyanın toplam bit sayısının sembol sayısına oranı.
    - Dosya boyutu ve sıkıştırma oranı da hesaplanır.
    """
    # Entropi hesaplama (fark dizisi üzerinden)
    hist = Counter(original_img.flatten())
    total = original_img.size
    entropy = -sum((count / total) * math.log2(count / total) for count in hist.values())

    # Sıkıştırılmış dosya boyutu (bayt cinsinden)
    comp_size = os.path.getsize(compressed_file)
    # Her kodu 2 bayt olarak sakladığımızı varsayarsak, toplam sembol sayısı: num_symbols
    avg_code_length = (comp_size * 8) / num_symbols  # bit/sembol
    # Orijinal verinin boyutu (ham fark verisi: her piksel 16 bit olarak düşünülebilir)
    original_size = original_img.size * 16 / 8  # byte cinsinden (örneğin her piksel için 2 bayt)

    compression_ratio = comp_size / original_size
    print(f"Entropy: {entropy:.4f} bits/sembol")
    print(f"Ortalama Kod Uzunluğu: {avg_code_length:.4f} bit/sembol")
    print(f"Sıkıştırılmış Dosya Boyutu: {comp_size} byte")
    print(f"Sıkıştırma Oranı: {compression_ratio:.4f}")

    return entropy, avg_code_length, comp_size, compression_ratio


if __name__ == "__main__":
    # Dosya yolları ve resim yükleme
    image_path = "lena.bmp"  # Gri ton resmi içeren dosya
    compressed_file = "compressed_part3.bin"
    restored_image_path = "restored_part3.png"

    # Resmi aç ve gri tonlamaya çevir
    img = Image.open(image_path).convert("L")
    img_array = np.array(img, dtype=np.int16)

    # Fark görüntüsünü hesapla
    diff_img = compute_difference_image(img_array)
    # Düzleştir (tek boyutlu fark dizisi)
    diff_list = diff_img.flatten().tolist()

    # LZW ile fark dizisini sıkıştır
    lzw_compress(diff_list, compressed_file)

    # Performans metriklerini hesapla
    # Not: num_symbols, fark dizisindeki toplam sembol sayısıdır.
    calculate_metrics(diff_img, compressed_file, len(diff_list))

    # -----------------------------
    # Decompression (Açma) İşlemleri
    # -----------------------------
    # Sıkıştırılmış dosyadan fark dizisini geri kazan
    decompressed_diff = lzw_decompress(compressed_file)
    # Tek boyutlu dizi, orijinal fark görüntüsü boyutuna yeniden şekillendirilir.
    diff_img_restored = np.array(decompressed_diff, dtype=np.int16).reshape(diff_img.shape)

    # Farklardan orijinal resmi geri kazan
    restored_array = restore_image_from_diff(diff_img_restored)
    restored_img = Image.fromarray(restored_array)
    restored_img.save(restored_image_path)

    # Karşılaştırma: Orijinal ve açılmış görüntülerin piksel bazında aynı olup olmadığını kontrol edelim.
    original_array = np.array(img, dtype=np.uint8)
    if np.array_equal(original_array, restored_array):
        print("Başarılı: Orijinal ve restor edilmiş görüntüler aynı!")
    else:
        print("Hata: Görüntüler arasında fark var.")

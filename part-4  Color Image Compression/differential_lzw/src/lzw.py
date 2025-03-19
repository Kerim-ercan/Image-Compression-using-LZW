def lzw_compress_gray(data):
    """
    Compresses data using LZW algorithm with handling for negative differences
    """
    # Convert negative values to positive range (0-255)
    data = [(x + 256) % 256 for x in data]
    
    dictionary = {bytes([i]): i for i in range(256)}
    dict_size = 256
    max_dict_size = 65536  # 16-bit limit
    
    w = bytes([data[0]]) if data else bytes()
    result = []
    
    for i in range(1, len(data)):
        c = bytes([data[i]])
        wc = w + c
        if wc in dictionary:
            w = wc
        else:
            result.append(dictionary[w])
            if dict_size < max_dict_size:
                dictionary[wc] = dict_size
                dict_size += 1
            w = c
    
    if w:
        result.append(dictionary[w])
    
    return result

def lzw_decompress_gray(codes):
    """
    Decompresses LZW compressed data with handling for negative differences
    """
    if not codes:
        return []
        
    dictionary = {i: bytes([i]) for i in range(256)}
    dict_size = 256
    
    # Handle first code
    result = list(dictionary[codes[0]])
    w = dictionary[codes[0]]
    
    for code in codes[1:]:
        if code in dictionary:
            entry = dictionary[code]
        elif code == dict_size and w:
            entry = w + bytes([w[0]])
        else:
            raise ValueError(f"Invalid compressed code: {code}")
            
        result.extend(entry)
        
        if w and dict_size < 65536:
            dictionary[dict_size] = w + bytes([entry[0]])
            dict_size += 1
            
        w = entry
    
    # Convert back to signed values (-128 to 127)
    return [(x if x < 128 else x - 256) for x in result] 
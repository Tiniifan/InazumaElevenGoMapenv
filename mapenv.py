import re
import os
import zlib
import struct
import codecs
import argparse

def assign_value_to_nested_dict(keys, value, dictionary):
    temp = dictionary
    
    for key in keys[:-1]:
        if key not in temp:
            temp[key] = {}
        temp = temp[key]
    
    temp[keys[-1]] = value

def convert_to_type(value):
    try:
        valeur_int = int(value)
        return valeur_int
    except ValueError:
        try:
            valeur_float = float(value)
            return valeur_float
        except ValueError:
            return value 
    
def pack_variable(variable):
    if isinstance(variable, int):
        return struct.pack("i", variable)
    elif isinstance(variable, float):
        return struct.pack("f", variable)
    elif isinstance(variable, bool):
        return struct.pack("?", variable)
    elif isinstance(variable, str):
        encoded_string = variable.encode('shift-jis')
        string_length = len(encoded_string)
        format_string = f"{string_length}s"
        return struct.pack(format_string, encoded_string)
    else:
        raise ValueError("Unsupported variable type")    

def pack_type(variable):
    if isinstance(variable, int):
        return b"\x01\x01\xFF\xFF"
    elif isinstance(variable, float):
        return b"\x01\x02\xFF\xFF"
    elif isinstance(variable, bool):
        return b"\x01\x01\xFF\xFF"
    elif isinstance(variable, str):
        encoded_string = variable.encode('shift-jis')
        string_length = len(encoded_string)
        format_string = f"{string_length}s"
        return b"\x01\x01\xFF\xFF"
    else:
        raise ValueError("Unsupported variable type")    

def align_bytes(data, align_byte, align_size):
    current_size = len(data)
    remaining = align_size - (current_size % align_size)
    padding = bytes([align_byte]) * remaining
    return data + padding

def create_entries_header(strings):
    table_header = b"".join(struct.pack("<I", zlib.crc32(string.encode())) + struct.pack("<I", 0)  for string in strings)
    table_header = align_bytes(table_header, 0xFF, 16)
    table_text = b"".join(string.encode() + struct.pack("<I", 0) for string in strings)
    table_length = len(table_text)
    table_text = align_bytes(table_text, 0xFF, 16)
    table_offset = struct.pack("<I", len(table_header) + len(table_text) + 16) + struct.pack("<I", 3) + struct.pack("<I", len(table_header) + 16) + struct.pack("<I", table_length)
    table_final = table_offset + table_header + table_text + b"\x01\x74\x32\x62\xFE\x01\x00\x00\x01\x00"
    table_final = align_bytes(table_final, 0xFF, 16)    
    return table_final

def get_text_from_bytes(data, position):
    # Move to the specified position
    data = data[position:]
    
    # Find the index of the first zero (0)
    index = data.find(b'\x00')
    
    # Extract the bytes until the zero index
    bytes_until_zero = data[:index]
    
    # Convert the bytes to text using Shift-JIS encoding
    text = bytes_until_zero.decode('shift-jis')
    
    return text, index
    
def compile_mapenv(file_path):
    key_stack = []  # Stack to keep track of nested PTREE keys
    tags = []  # List to store encountered tags
    
    file_data = bytes()  # Placeholder for file data
    text_header = pack_variable('MAP_ENV') + b"\x00"  # Text header with 'MAP_ENV'
    lines = codecs.open(input_file, "r", "shift-jis").readlines()  # Read lines from input file
    
    entries_count = 0
    text_length = len(text_header)
    text_line_number = 1
    
    for line in lines:
        line = line.strip()
        
        if line.startswith("PTREE"):
            entries_count += 1
            text_line_number += 1
            
            if 'PTREE' not in tags: 
                tags.append('PTREE')  # Add PTREE tag to the list
                
            key = line[6:].replace('"', '').replace(',', ' ').replace(';', '')  # Extract PTREE key
            key_stack.append(key)  # Push key to the stack
            
            file_data += struct.pack("<I", zlib.crc32('PTREE'.encode()))  # Calculate CRC32 and pack it
            text_offset = len(text_header)  # Calculate text offset
            
            if key.startswith("MAP_ENV"):
                text_header += pack_variable(key.replace('MAP_ENV ', '')) + b"\x00"  # Pack variable and add to text header
                text_length = len(text_header)
                file_data += struct.pack("<H", 2)[:2] + b"\xFF\xFF"  # Pack type (2) and padding
                file_data += struct.pack("<I", 0)  # Pack text offset (0)
            else:
                text_header += pack_variable(key) + b"\x00"  # Pack variable and add to text header
                text_length = len(text_header)
                file_data += struct.pack("<H", 1)[:2] + b"\xFF\xFF"  # Pack type (1) and padding
                
            file_data += struct.pack("<I", text_offset)  # Pack text offset
            
        elif line == "_PTREE;":
            entries_count += 1
            
            if '_PTREE' not in tags: 
                tags.append('_PTREE')  # Add _PTREE tag to the list
                
            key_stack.pop()  # Pop key from the stack
            
            file_data += b"\x3E\xB8\xE6\xD4"  # Pack _PTREE data
            file_data += b"\x00\xFF\xFF\xFF"  # Pack padding
            
        elif line.startswith("PTVAL") and not line.startswith("PTVALS"):
            entries_count += 1
            
            if 'PTVAL' not in tags: 
                tags.append('PTVAL')  # Add PTVAL tag to the list
                
            values = line[6:][:-1]
            values = re.sub(r",\s+", ",", values).replace('"', '').split(',')  # Extract PTVAL values
            print(values)
            
            if len(values) == 1:
                value = convert_to_type(values[0])  # Convert value to appropriate type
                file_data += struct.pack("<I", zlib.crc32('PTVAL'.encode()))  # Calculate CRC32 and pack it
                file_data += pack_type(value)  # Pack value type
                file_data += pack_variable(value)  # Pack value as variable
                
            else:
                text_line_number += 1
                text_offset = len(text_header)  # Calculate text offset
                text_header += pack_variable(values[1]) + b"\x00"  # Pack variable and add to text header
                text_length = len(text_header)
                value = convert_to_type(values[0])  # Convert value to appropriate type
                file_data += struct.pack("<I", zlib.crc32('PTVAL'.encode()))  # Calculate CRC32 and pack it
                file_data += b"\x02\x01\xFF\xFF"  # Pack type (2), padding, and text offset
                file_data += pack_variable(value)  # Pack value as variable
                file_data += struct.pack("<I", text_offset)  # Pack text offset
                
        elif line.startswith("PTVALS"):
            entries_count += 1
            
            if 'PTVALS' not in tags: 
                tags.append('PTVALS')  # Add PTVALS tag to the list
                
            values = line[7:][:-1].split(',')  # Extract PTVALS values
            
            file_data += struct.pack("<I", zlib.crc32('PTVALS'.encode()))  # Calculate CRC32 and pack it
            file_data += struct.pack("<H", len(values))[:2] + b"\xFF\xFF"  # Pack values count and padding
            
            for i in range(len(values)):
                value = convert_to_type(values[i])  # Convert value to appropriate type
                file_data += pack_variable(value)  # Pack value as variable
    
    file_data += b"\x00"  # Add null terminator
    file_data = align_bytes(file_data, 0xFF, 16) # Align bytes
    text_header = text_header + b"\x00" # Add null terminator
    text_header = align_bytes(text_header, 0xFF, 16)  # Align bytes again
    file_header = struct.pack("<I", entries_count) + struct.pack("<I", len(file_data) + 16) + struct.pack("<I", len(text_header)) + struct.pack("<I", text_line_number)
    file_data = file_header + file_data + text_header
    file_data += create_entries_header(tags)  # Create entries header
    
    return file_data

def decompile_mapenv(file_path):
    file = open(file_path, "rb")
    file_size = os.path.getsize(file_path)
    text_output = ""

    entries_count = struct.unpack("<I", file.read(4))[0]
    text_offset = struct.unpack("<I", file.read(4))[0]
    text_length = struct.unpack("<I", file.read(4))[0]
    text_line_number = struct.unpack("<I", file.read(4))[0]

    file.seek(text_offset + text_length)
    table_data = file.read(file_size - (text_offset + text_length))
    table_length = struct.unpack("<I", table_data[0:4])[0]
    table_count = struct.unpack("<I", table_data[4:8])[0]
    table_text_offset = struct.unpack("<I", table_data[8:12])[0]
    table_text_length = struct.unpack("<I", table_data[12:16])[0]
    file.seek(text_offset + text_length + table_text_offset)
    table_text_data = file.read(table_text_length)
    file.seek(text_offset + text_length)

    tags = {}
    table_position = 16
    text_position = 0
    indent_level = 0  # Initial indentation level

    for i in range(table_count):
        text, index = get_text_from_bytes(table_text_data, text_position)
        text_position += index + 1
        tags[table_data[table_position:table_position + 4]] = text
        table_position += 8

    file.seek(text_offset)
    text_data = file.read(text_length)

    file.seek(16)
    for i in range(entries_count):
        current_tag = file.read(4)
        current_tag_config = file.read(4)
        tag_size = current_tag_config[0]
        type_size = current_tag_config[1]

        if current_tag == b'\xa2T\xde^':
            # PTREE
            if tag_size == 2:
                file.read(4)
                text_offset = struct.unpack("<I", file.read(4))[0]
                text, index = get_text_from_bytes(text_data, text_offset)
                text_output += ' ' * (indent_level * 4) + 'PTREE "MAP_ENV","' + text + '";\n'
                indent_level += 1  # Increment the indentation level
            else:
                text_offset = struct.unpack("<I", file.read(4))[0]
                text, index = get_text_from_bytes(text_data, text_offset)
                text_output += ' ' * (indent_level * 4) + 'PTREE "' + text + '";\n'
                indent_level += 1  # Increment the indentation level

        elif current_tag == b'\xde\x81gD':
            # PTVAL
            value = 0

            if type_size == 0:
                value = struct.unpack("<I", file.read(4))[0]
            elif type_size == 1:
                value = struct.unpack("<I", file.read(4))[0]
            elif type_size == 2:
                value = struct.unpack("f", file.read(4))[0]

            if tag_size == 2:
                text_offset = struct.unpack("<I", file.read(4))[0]
                text, index = get_text_from_bytes(text_data, text_offset)
                text_output += ' ' * (indent_level * 4) + 'PTVAL ' + str(value) + ', "' + text + '";\n'
            else:
                text_output += ' ' * (indent_level * 4) + 'PTVAL ' + str(value) + ';\n'
        elif current_tag == b'>\xb8\xe6\xd4':
            # _PTREE
            indent_level -= 1  # Decrement the indentation level
            
            current_position = file.tell()
            found_match = False

            while file.tell() <= file_size:
                chunk = file.read(4)
                for key in tags:
                    if key == chunk:
                        current_position = file.tell() - 4
                        found_match = True
                        break
                if found_match:
                    break

            file.seek(current_position)        
            text_output += ' ' * (indent_level * 4) + '_PTREE\n'

    return text_output

if __name__ == '__main__':    
    parser = argparse.ArgumentParser(description="Compile and decompile mapenv file")
    parser.add_argument('action', choices=['c', 'd'], help='Action to perform: -c to compile, -d to decompile')
    parser.add_argument('input_file', help='Path to the input file')
    parser.add_argument('output_file', help='Path to the output file')

    # Parse the arguments
    args = parser.parse_args()
    print(args)

    # Retrieve the argument values
    action = args.action
    input_file = args.input_file
    output_file = args.output_file

    if action == 'c':
        print('Compiling...')
        
        with open(output_file, 'wb') as file:
                file.write(compile_mapenv(input_file))
        
        print('File compiled successfully.')
    elif action == 'd':
        print('Decompiling...')

        with open(output_file, 'w') as file:
            file.write(decompile_mapenv(input_file))

        print('File decompiled successfully.')
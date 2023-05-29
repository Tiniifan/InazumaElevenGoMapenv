# Inazuma Eleven Go Mapenv Compiler & Decompiler
Python scrip to compile and decompile mapenv file

## Requirements
- Python 3: https://www.python.org/downloads/

## Usage
Assuming Python has been installed, you can invoke this script with the following in a command line/terminal:

  `python mapenv.py [c or d] [your input file path] [your output file path]`

Example decompile
  `python mapenv.py d mr02b02_mapenv.bin mr02b02.mapenv`  
Example compile
  `python mapenv.py c mr02b02.mapenv mr02b02_mapenv.bin`

## Arguments
```usage: mapenv.py [-h] {c,d} input_file output_file

  Compile and decompile mapenv file

  positional arguments:
    {c,d}        Action to perform: -c to compile, -d to decompile
    input_file   Path to the input file
    output_file  Path to the output file

  options:
    -h, --help   show this help message and exit
```

# Read with utf-8 as the file was written with utf-8
try:
    with open('mapping_debug.txt', 'r', encoding='utf-8') as f:
        print(f"--- Reading with utf-8 ---")
        print(f.read())
except Exception as e:
    print(f"Failed with utf-8: {e}")

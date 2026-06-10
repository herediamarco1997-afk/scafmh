import os, struct, re, subprocess

targets = [
    (r'D:\sistema de af\INSTLADOR VSIAF\vsiaf_v3.2p.exe', 'v3.2p installer'),
    (r'D:\sistema de af\INSTLADOR VSIAF\Archivo_Actualizador_2025.exe', 'Actualizador UFV 2025'),
    (r'D:\sistema de af\sistema_activos\vsiaf_v3.2p.exe', 'v3.2p (extracted)'),
]

# Extract v2.0 to compare
result = subprocess.run([
    'C:\\Program Files\\WinRAR\\UnRAR.exe', 'e', '-y',
    'D:\\sistema de af\\INSTLADOR VSIAF\\vsiaf_v2_0.rar',
    'D:\\sistema de af\\sistema_activos\\'
], capture_output=True, text=True)
print("Extract v2.0 result:", (result.stdout.strip()[-200:] if result.stdout else "nothing"))

for exe_path, label in targets:
    if not os.path.exists(exe_path):
        print(f"\n=== {label} - NOT FOUND ===")
        continue
    sz = os.path.getsize(exe_path)
    print(f"\n=== {label} ({sz:,} bytes) ===")
    with open(exe_path, 'rb') as f:
        data = f.read()
    
    # Check PE signature
    pe_off = struct.unpack('<I', data[0x3c:0x40])[0]
    magic = struct.unpack('<H', data[pe_off+0x18:pe_off+0x1a])[0]
    print(f'  Magic: {hex(magic)}', end='')
    if magic == 0x10b: print(' (PE32)')
    elif magic == 0x20b: print(' (PE32+)')
    elif magic == 0x454c: print(' (NE - 16-bit)')
    else: print()
    
    # Check for FoxPro specific strings
    search_terms = [b'FoxPro', b'VFP', b'Visual FoxPro', b'Microsoft(R) FoxPro',
                    b'Setup Factory', b'Setup.exe']
    for term in search_terms:
        p = data.find(term)
        if p >= 0:
            print(f'  Found [{term.decode()}] at offset {p}')
    
    # Find all readable strings
    strs = re.findall(rb'[\x20-\x7E]{8,}', data)
    narrativas = [s for s in strs if any(kw in s.upper() for kw in 
        [b'REPORT', b'DEPRECI', b'REVAL', b'UFV', b'ACTIVO', b'CODIGO',
         b'RESPONSABLE', b'OFICINA', b'GRUPO', b'BAJA', b'TRANSFER',
         b'COSTO', b'INVENTARIO', b'RESUMEN', b'IMPRIME'])]
    for s in set(narrativas):
        decoded = s.decode('ascii', errors='replace')
        if len(decoded) > 12:
            print(f'  STR: {decoded}')

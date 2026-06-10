import os, struct, re

path = r'D:\sistema de af\INSTLADOR VSIAF\vsiaf_v3.2p.exe'
with open(path, 'rb') as f:
    data = f.read()

# Extract text strings from the exe
print("=== STRINGS ENCONTRADOS ===")
# Find all readable strings of 6+ chars
pattern = re.compile(rb'[\x20-\x7E]{6,}')
matches = pattern.findall(data)
interesting = []
for m in matches:
    s = m.decode('ascii', errors='ignore')
    if any(kw in s.upper() for kw in ['REPORTE', 'DEPRECI', 'REVAL', 'UFV', 'BAJA', 
                                       'ACTIVO', 'CODIGO', 'DESCRIP', 'COSTO',
                                       'INVENTARIO', 'RESUMEN', 'TRANSFER', 'ACTA',
                                       'GRUPO', 'OFICINA', 'RESPONSABLE', 'AUXILIAR',
                                       'IMPRIME', 'VILLA', 'PAGINA']):
        interesting.append(s)

for s in sorted(set(interesting)):
    if len(s) > 8:
        print(s)

print("\n=== RECURSOS .rsrc ===")
# Extract the .rsrc section
pe_offset = struct.unpack('<I', data[0x3c:0x40])[0]
num_sections = struct.unpack('<H', data[pe_offset+6:pe_offset+8])[0]
magic = struct.unpack('<H', data[pe_offset+0x18:pe_offset+0x1a])[0]
section_start = pe_offset + 0x18 + (0xe0 if magic == 0x10b else 0xf0)

for i in range(num_sections):
    sec = data[section_start + i*40 : section_start + (i+1)*40]
    name = sec[:8].rstrip(b'\x00').decode('ascii', errors='replace')
    raw_addr = struct.unpack('<I', sec[20:24])[0]
    raw_size = struct.unpack('<I', sec[16:20])[0]
    if name == '.rsrc':
        rsrc_data = data[raw_addr:raw_addr+raw_size]
        print(f'.rsrc size: {raw_size} bytes')
        # Find all strings in .rsrc
        strs = pattern.findall(rsrc_data)
        for s in strs:
            decoded = s.decode('ascii', errors='ignore').strip()
            if len(decoded) > 4:
                print(f'  {decoded}')
        break

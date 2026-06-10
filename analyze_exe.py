import os, struct

path = r'D:\sistema de af\INSTLADOR VSIAF\vsiaf_v3.2p.exe'
sz = os.path.getsize(path)
print('Size: ' + str(sz) + ' bytes (' + str(sz/1024) + ' KB)')

with open(path, 'rb') as f:
    data = f.read()

print('First 4 bytes: ' + str(data[:4]))

# Look for 'Rar!' signature
rar_pos = data.find(b'Rar!')
print('RAR signature at: ' + str(rar_pos))

if rar_pos >= 0:
    print('This is a RAR SFX executable')
    # Show context
    print('Context before: ' + data[max(0,rar_pos-8):rar_pos].hex())
    print('Context after: ' + data[rar_pos:rar_pos+10].hex())
else:
    # Look for other known signatures
    # FoxPro compiled app
    fox_sigs = [(b'FXP', 'FXP signature'), (b'FOXPRO', 'FOXPRO string'),
                (b'Microsoft Visual FoxPro', 'VFP string')]
    for sig, name in fox_sigs:
        p = data.find(sig)
        if p >= 0:
            print(name + ' found at: ' + str(p))
        else:
            print(name + ' NOT found')
    
    # Check for .rsrc section
    pe_offset = struct.unpack('<I', data[0x3c:0x40])[0]
    print('PE header offset: ' + str(pe_offset))
    pe_sig = data[pe_offset:pe_offset+4]
    print('PE signature: ' + str(pe_sig))
    
    # Look for export table (DLLs) or import table
    # At pe_offset + 0x18 = optional header magic
    magic = struct.unpack('<H', data[pe_offset+0x18:pe_offset+0x1a])[0]
    print('Optional header magic: ' + hex(magic))
    if magic == 0x10b:
        print('PE32 executable')
    elif magic == 0x20b:
        print('PE32+ executable')
    
    # Count sections
    num_sections = struct.unpack('<H', data[pe_offset+6:pe_offset+8])[0]
    print('Number of sections: ' + str(num_sections))
    
    # List sections
    section_start = pe_offset + 0x18 + (0xe0 if magic == 0x10b else 0xf0)
    for i in range(num_sections):
        sec = data[section_start + i*40 : section_start + (i+1)*40]
        name = sec[:8].rstrip(b'\x00').decode('ascii', errors='replace')
        vaddr = struct.unpack('<I', sec[12:16])[0]
        vsize = struct.unpack('<I', sec[8:12])[0]
        raw_size = struct.unpack('<I', sec[16:20])[0]
        raw_addr = struct.unpack('<I', sec[20:24])[0]
        print('  Section: ' + name + ' VA=' + hex(vaddr) + ' VSz=' + str(vsize) + ' Raw=' + str(raw_addr) + ' RSz=' + str(raw_size))

print('\nDone.')

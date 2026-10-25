#!/usr/bin/env python3
"""Extract one bounded raw type-10 SMK entry from a BLB, with audit metadata."""
import argparse, hashlib, json, pathlib, struct

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('archive', type=pathlib.Path)
    ap.add_argument('entry_id', type=int)
    ap.add_argument('output_dir', type=pathlib.Path)
    a=ap.parse_args()
    data=a.archive.read_bytes()
    sig, version, ext, declared, count=struct.unpack_from('<IHHII', data, 0)
    if (sig,version,declared)!=(0x02004940,7,len(data)) or a.entry_id<0 or a.entry_id>=count:
        raise SystemExit('invalid BLB header or entry index')
    hashes=struct.unpack_from(f'<{count}I',data,16)
    records=16+count*4
    typ,comp,extoff,stamp,offset,disk,size=struct.unpack_from('<BBHIIII',data,records+a.entry_id*20)
    if typ!=10 or comp!=1 or offset>len(data) or disk>len(data)-offset or disk<20:
        raise SystemExit('entry is not an in-bounds uncompressed type-10 resource')
    payload=data[offset:offset+disk]
    if payload[:4] not in (b'SMK2',b'SMK4'):
        raise SystemExit('entry does not have SMK signature')
    w,h,frames,rawrate=struct.unpack_from('<IIIi',payload,4)
    if rawrate<0:
        fps_num,fps_den=100000,abs(rawrate)
    elif rawrate>0:
        fps_num,fps_den=1000,rawrate
    else:
        fps_num,fps_den=0,1
    import math
    g=math.gcd(fps_num,fps_den)
    if g: fps_num//=g; fps_den//=g
    a.output_dir.mkdir(parents=True,exist_ok=True)
    video=a.output_dir/'sample.smk'
    video.write_bytes(payload)
    meta={'archive':a.archive.name,'entry_id':a.entry_id,'hash':f'{hashes[a.entry_id]:08X}',
          'type':typ,'compression':comp,'offset':offset,'size':disk,'expanded_size':size,
          'dimensions':{'width':w,'height':h},'frames':frames,
          'frame_rate_raw_signed':rawrate,'fps':fps_num/fps_den if fps_num else None,
          'fps_rational':f'{fps_num}/{fps_den}' if fps_num else None,
          'format':payload[:4].decode('ascii'),'sha256':hashlib.sha256(payload).hexdigest()}
    (a.output_dir/'metadata.json').write_text(json.dumps(meta,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(meta,indent=2))
if __name__=='__main__': main()

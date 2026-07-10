from pathlib import Path
allowed = {0x00b7,0x2014,0x2026,0x2018,0x2019,0x201c,0x201d,0x00a5,0x2713,0x23f3,0x1f4dd,0x2022}
for p in Path('frontend/src').rglob('*.vue'):
    lines = p.read_text(encoding='utf-8').splitlines()
    found = False
    for i, line in enumerate(lines, 1):
        bad = []
        for ch in line:
            o = ord(ch)
            ok = (o <= 127 or 0x3400 <= o <= 0x9fff or 0x3000 <= o <= 0x303f or 0xff00 <= o <= 0xffef or o in allowed)
            if not ok:
                bad.append(ch)
        if bad:
            if not found:
                print(f'FILE {p}')
                found = True
            print(i, line.encode('unicode_escape').decode())

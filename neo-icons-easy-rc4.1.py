#!/usr/bin/env python3
# SAT Channel Manager Pro — safe Neo Icons / clearer installation patch.
# Intended for already-installed RC4.1 Easy Mode, OpenATV 8.0.1.
from pathlib import Path
import os,sys,shutil,tempfile,struct,zlib,math,hashlib

root=Path("/usr/lib/enigma2/python/Plugins/Extensions/SATChannelManager")
if len(sys.argv)==2: root=Path(sys.argv[1])
neo=root/"neo.py"
skin=root/"ui_skin.py"
if not neo.is_file() or not skin.is_file() or neo.is_symlink() or skin.is_symlink():
    raise SystemExit("ERROR: SAT Channel Manager installation not found or unsafe path.")
n=neo.read_text(encoding="utf-8")
s=skin.read_text(encoding="utf-8")
if "icons/install.png" in s and "self.smart_installation('preset')" in n:
    print("Neo icon patch already installed. Restart GUI if icons are not visible.")
    raise SystemExit(0)
if "0.4.1-rc4.1-easy" not in (root/"core.py").read_text(encoding="utf-8"):
    raise SystemExit("ERROR: this patch expects RC4.1 Easy Mode. No files changed.")
def once(text,old,new):
    if text.count(old)!=1: raise ValueError("Unexpected Enigma2 source layout: "+old[:70])
    return text.replace(old,new)
n=once(n,"self.smart_installation('selected' if self.selected else 'preset')","self.smart_installation('preset')")
n=once(n,"        rows = []\n        if self.selected:\n            rows.append(('Mettre a jour mes %d satellites coches (fusion)' % len(self.selected), 'smart_selected'))\n        rows.extend([\n            ('Mettre a jour Nilesat / Badr / Hot Bird / Astra', 'smart'),",
"""        rows = [('1. FREQUENCES : Nilesat 7W / Badr 26E / Hot Bird 13E / Astra 19.2E', 'smart')]
        if self.selected:
            rows.append(('2. FREQUENCES : mes %d satellites coches' % len(self.selected), 'smart_selected'))
        rows.extend([""")
n=once(n,"('Mettre a jour les frequences de 75W a 150E', 'smart_range')",
         "('3. FREQUENCES : plage 75W a 150E', 'smart_range')")
n=once(n,"('Rechercher les chaines du satellite (scan tuner)', 'scan_current')",
         "('4. CHAINES TV : scan avec le tuner', 'scan_current')")
n=once(n,"'Fusion de FREQUENCES, apercu, confirmation et backup.'",
         "'Frequences = satellites.xml ; chaines = scan DVB. Aucun import direct LyngSat.'")
n=once(n,"('Actualiser les donnees satellites', 'update_all')",
         "('Telecharger les FREQUENCES OE-Alliance + OpenPLi', 'update_all')")
n=once(n,"'Les chaines SAT, bouquets, lamedb et parametres tuner ne seront pas modifies.'",
         "'FREQUENCES seulement : aucune chaine TV ou bouquet importe.'")
n=once(n,"self['key_green'] = Label('VERT  MAJ / Scan')",
         "self['key_green'] = Label('FREQUENCES / SCAN')")
n=once(n,"self['key_yellow'] = Label('JAUNE  Mes bouquets')",
         "self['key_yellow'] = Label('MES BOUQUETS')")
n=once(n,"self['key_blue'] = Label('BLEU  Options')",
         "self['key_blue'] = Label('OPTIONS')")
# Skin is one Python string with literal backslash-n separators. No skin rewriting at runtime.
s=once(s,'name="key_green" position="284,651" size="270,30"',
       'name="key_green" position="324,651" size="242,30"')
s=once(s,'name="key_yellow" position="589,651" size="262,30"',
       'name="key_yellow" position="629,651" size="237,30"')
s=once(s,'name="key_blue" position="908,651" size="298,30"',
       'name="key_blue" position="952,651" size="250,30"')
icons=[
 ('install',284,(127,240,176)),
 ('bouquets',589,(255,210,123)),
 ('options',908,(125,184,255)),
]
tags=""
for name,x,_ in icons:
    tags+=' <ePixmap zPosition="6" position="%d,647" size="34,34" pixmap="%s" alphatest="blend" />\\n' % (x,str(root/"icons"/(name+".png")))
s=once(s,' <widget zPosition="5" name="key_green"',tags+' <widget zPosition="5" name="key_green"')
compile(n,str(neo),"exec")
compile(s,str(skin),"exec")
# Render three small, original UI button icons using only the Python standard library.
def draw_png(kind, color):
    w=h=48
    rgba=bytearray()
    lines={'install':[(24,9,24,31),(15,23,24,32),(24,32,33,23),(9,39,39,39),(9,33,9,39),(39,33,39,39)],
           'bouquets':[(12,10,38,10),(12,19,38,19),(12,28,28,28),(12,37,28,37),
                       (31,25,40,32),(40,32,31,39),(31,39,31,25)],
           'options':[(9,14,39,14),(9,25,39,25),(9,36,39,36)]}[kind]
    circles={'options':[(20,14),(31,25),(19,36)]}.get(kind,[])
    for y in range(h):
        rgba.append(0)
        for x in range(w):
            # dark round-corner rectangle; fully transparent outside
            dx=max(8-x,x-39,0);dy=max(8-y,y-39,0)
            inside=dx*dx+dy*dy<=64
            rgb=(20,35,51) if inside else (0,0,0)
            if inside:
                for x1,y1,x2,y2 in lines:
                    t=max(0,min(1,((x-x1)*(x2-x1)+(y-y1)*(y2-y1))/float(max(1,(x2-x1)**2+(y2-y1)**2))))
                    if (x-(x1+t*(x2-x1)))**2+(y-(y1+t*(y2-y1)))**2<3.8:rgb=color
                for cx,cy in circles:
                    d=(x-cx)**2+(y-cy)**2
                    if d<19:rgb=color if d>8 else (20,35,51)
            rgba.extend((*rgb,255 if inside else 0))
    def chunk(t,b):
        return struct.pack(">I",len(b))+t+b+struct.pack(">I",zlib.crc32(t+b)&0xffffffff)
    return (b"\x89PNG\r\n\x1a\n"+chunk(b"IHDR",struct.pack(">IIBBBBB",w,h,8,6,0,0,0))+
            chunk(b"IDAT",zlib.compress(bytes(rgba),9))+chunk(b"IEND",b""))
for item,data in ((neo,n.encode()),(skin,s.encode())):
    saved=item.with_name(item.name+".bak-before-neo-icons")
    if not saved.exists():shutil.copy2(item,saved)
    fd,tmp=tempfile.mkstemp(prefix=".sat-icons-",dir=str(root))
    try:
        with os.fdopen(fd,"wb") as out:
            out.write(data);out.flush();os.fsync(out.fileno())
        os.chmod(tmp,item.stat().st_mode & 0o777)
        os.replace(tmp,item)
    finally:
        if os.path.exists(tmp):os.unlink(tmp)
icon_dir=root/"icons";icon_dir.mkdir(exist_ok=True)
for kind,_,rgb in icons:
    target=icon_dir/(kind+".png")
    target.write_bytes(draw_png(kind,rgb))
    assert target.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
print("Neo icons added (3), four-satellite preset restored, frequency/channel distinction improved.")
print("Python files backed up as *.bak-before-neo-icons. Restart the Enigma2 GUI.")

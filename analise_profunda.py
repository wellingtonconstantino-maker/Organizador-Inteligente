"""Comparação conservadora de fotos, PDFs e CBZ. Nenhuma exclusão."""
from pathlib import Path
from collections import defaultdict
import hashlib, io, os, re, zipfile
from PySide6.QtCore import QThread, Signal

IMAGE_EXT={'.jpg','.jpeg','.png','.webp','.bmp','.tif','.tiff','.gif'}

def dhash(im):
    from PIL import ImageOps
    im=ImageOps.exif_transpose(im).convert('L').resize((9,8))
    p=list(im.getdata());return sum((p[y*9+x]>p[y*9+x+1])<<(y*8+x) for y in range(8) for x in range(8))

def image_fingerprint(p):
    from PIL import Image
    with Image.open(p) as im:
        w,h=im.size
        return dhash(im),w*h

def pdf_fingerprint(p):
    import fitz
    with fitz.open(p) as d:
        pages=len(d)
        s=' '.join(page.get_text('text') for page in d)
    s=re.sub(r'\s+',' ',s).casefold().strip()
    return hashlib.sha256(s.encode()).hexdigest() if len(s)>100 else None,pages

def cbz_fingerprint(p):
    from PIL import Image
    with zipfile.ZipFile(p) as z:
        names=sorted(n for n in z.namelist() if Path(n).suffix.lower() in IMAGE_EXT)
        if not names:return None,0
        with Image.open(io.BytesIO(z.read(names[0]))) as im: first=dhash(im)
        with Image.open(io.BytesIO(z.read(names[-1]))) as im: last=dhash(im)
        return (first,last),len(names)

class DeepWorker(QThread):
    progress=Signal(int,int)
    completed=Signal(object,object)
    def __init__(self,root):super().__init__();self.root=Path(root)
    def run(self):
        images=[];pdfs=defaultdict(list);comics=[];errors=[]
        files=[]
        for root,dirs,names in os.walk(self.root,followlinks=False):
            dirs[:]=[d for d in dirs if d not in ('Quarentena_Constantino','.constantino_quarentena','Fotografias organizadas') and not (Path(root)/d).is_symlink()]
            for name in names:
                p=Path(root)/name
                if p.is_symlink():continue
                if p.suffix.lower() in IMAGE_EXT|{'.pdf','.cbz'}:files.append(p)
        for i,p in enumerate(files,1):
            try:
                ext=p.suffix.lower()
                if ext in IMAGE_EXT:
                    h,quality=image_fingerprint(p);images.append((p,h,quality))
                elif ext=='.pdf':
                    h,pages=pdf_fingerprint(p)
                    if h:pdfs[h].append((p,pages))
                elif ext=='.cbz':
                    h,pages=cbz_fingerprint(p)
                    if h:comics.append((p,h,pages))
            except Exception as e:errors.append(f'{p}: {str(e)[:100]}')
            self.progress.emit(i,max(1,len(files)))
        results=[]
        # Compara imagens perceptualmente. Não presume equivalência apenas pelo hash.
        buckets=defaultdict(list)
        for p,h,q in images:
            # Divisão por 8 blocos: até 5 bits de diferença garantem um bloco idêntico.
            for part in range(8):buckets[(part,(h>>(part*8))&255)].append((p,h,q))
        seen=set()
        for group in buckets.values():
            if len(group)>500:continue
            for i in range(len(group)):
                for j in range(i+1,len(group)):
                    a,ha,qa=group[i];b,hb,qb=group[j]
                    key=tuple(sorted((str(a),str(b))))
                    if key in seen:continue
                    seen.add(key)
                    distance=(ha^hb).bit_count()
                    if distance<=5:
                        results.append(('Fotografia semelhante — revisar',str(a),str(b),f'Distância visual {distance}/64; pixels {qa} e {qb}'))
        for records in pdfs.values():
            if len(records)>1:
                for p,pages in records[1:]:results.append(('PDF com texto equivalente',str(records[0][0]),str(p),f'{pages} páginas; conferir edição'))
        for i,(p,h,n) in enumerate(comics):
            for q,k,m in comics[i+1:]:
                if n==m and (h[0]^k[0]).bit_count()<=3 and (h[1]^k[1]).bit_count()<=3:
                    results.append(('CBZ possivelmente equivalente',str(p),str(q),f'{n} páginas; conferir visualmente'))
        self.completed.emit(results,errors)

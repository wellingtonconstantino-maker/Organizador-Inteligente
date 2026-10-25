"""Organização reversível de fotografias por ano. Nunca sobrescreve arquivos."""
from pathlib import Path
from datetime import datetime
import csv, os, shutil, uuid
from PIL import Image
from PIL.ExifTags import TAGS

EXTS={'.jpg','.jpeg','.png','.webp','.bmp','.tif','.tiff','.gif','.heic','.heif','.dng','.cr2','.nef','.arw'}

def year_for(p):
    try:
        with Image.open(p) as im:
            exif=im.getexif()
            try: original=exif.get_ifd(0x8769).get(36867)
            except Exception: original=None
            if original:
                y=int(str(original)[:4])
                if 1900<=y<=datetime.now().year:return str(y),'EXIF'
            for key,value in exif.items():
                if TAGS.get(key) in ('DateTimeOriginal','DateTimeDigitized','DateTime'):
                    y=int(str(value)[:4]);
                    if 1900<=y<=datetime.now().year:return str(y),'EXIF'
    except Exception:pass
    try:
        y=datetime.fromtimestamp(p.stat().st_mtime).year
        return str(y),'modificação (aproximada)'
    except OSError:return 'Data desconhecida','sem data'

def plan(root):
    root=Path(root).resolve();dest=root/'Fotografias organizadas';rows=[]
    for base,dirs,files in os.walk(root,followlinks=False):
        dirs[:]=[d for d in dirs if d not in ('Fotografias organizadas','.constantino_quarentena','Quarentena_Constantino') and not (Path(base)/d).is_symlink()]
        for name in files:
            p=Path(base)/name
            if p.suffix.lower() not in EXTS or p.is_symlink():continue
            y,source=year_for(p)
            rows.append((p,dest/y/p.name,source))
    return rows

def execute(root,rows):
    root=Path(root).resolve();base=root/'Fotografias organizadas';base.mkdir(parents=True,exist_ok=True)
    manifest=base/('manifesto_organizacao_'+datetime.now().strftime('%Y%m%d_%H%M%S')+'_'+uuid.uuid4().hex[:6]+'.csv')
    done=[];errors=[]
    with manifest.open('w',newline='',encoding='utf-8-sig') as f:
        writer=csv.writer(f,delimiter=';');writer.writerow(['origem','destino','fonte_data'])
        for src,dst,source in rows:
            try:
                dst.parent.mkdir(parents=True,exist_ok=True)
                if dst.exists():dst=dst.with_name(dst.stem+'_'+uuid.uuid4().hex[:8]+dst.suffix)
                # Persistir registro antes de mover; caso interrompido, verificar existência.
                writer.writerow([str(src),str(dst),source]);f.flush();os.fsync(f.fileno())
                shutil.move(str(src),str(dst));done.append((src,dst))
            except (OSError,shutil.Error) as e:errors.append(f'{src}: {e}')
    return manifest,done,errors

def undo(manifest):
    manifest=Path(manifest);done=[];errors=[]
    with manifest.open(encoding='utf-8-sig',newline='') as f:
        for r in csv.DictReader(f,delimiter=';'):
            src=Path(r['origem']);dst=Path(r['destino'])
            try:
                if src.exists() or not dst.is_file():raise FileExistsError('origem ocupada ou destino ausente')
                src.parent.mkdir(parents=True,exist_ok=True);shutil.move(str(dst),str(src));done.append(src)
            except (OSError,shutil.Error) as e:errors.append(f'{dst}: {e}')
    return done,errors

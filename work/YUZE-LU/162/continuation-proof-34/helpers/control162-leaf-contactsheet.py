"""Preview actual delivered PNGs only; no modification of accepted files."""
from pathlib import Path
from PIL import Image,ImageOps,ImageDraw
import zipfile,io,json
root=Path(r'D:\Data\电路实验\LLMHardwareDesign-deliveries\issue-162\blocks-ready140');out=root/'previews';out.mkdir(exist_ok=False)
leaves=json.loads((root/'SOURCE_INDEX.json').read_text())['leaves'];width=350;height=390
sheet=Image.new('RGB',(width*4,height*6),'white');draw=ImageDraw.Draw(sheet)
for i,row in enumerate(leaves):
 top=row['top']
 with zipfile.ZipFile(root/(top+'.zip'))as archive:
  names=[n for n in archive.namelist()if n.endswith('layout.png')];assert len(names)==1
  blob=archive.read(names[0]);(out/(top+'.png')).write_bytes(blob)
  png=Image.open(io.BytesIO(blob));png.load();png=png.convert('RGB');png.thumbnail((330,345))
 x=(i%4)*width;y=(i//4)*height;sheet.paste(png,(x+(width-png.width)//2,y+30+(345-png.height)//2))
 draw.text((x+8,y+8),top,fill='black');draw.text((x+8,y+372),f"setup {row['minimum_setup_ns']:.6f} ns / hold {row['minimum_hold_ns']:.6f} ns",fill='black')
sheet.save(out/'qualified-blocks-contactsheet.png');print(out/'qualified-blocks-contactsheet.png')

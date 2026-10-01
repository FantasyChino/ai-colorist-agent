"""Reproduce photo-specific showcase LUT tables offline; no photos are processed."""
from pathlib import Path
import json
import sys
import cv2
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from build_creative_looks import encode_gamut


def bake(item):
    recipe,strength,extra=item["recipe"],item["strength"],item["extra"]
    b,g,r=np.indices((33,)*3,dtype=np.float32)
    rgb=np.stack((r,g,b),axis=-1).reshape(-1,3)/32
    original=cv2.cvtColor(rgb.reshape(1,-1,3),cv2.COLOR_RGB2Lab).reshape(-1,3).astype(float)
    lab=original.copy()
    light=original[:,0]
    lab[:,0]=light+strength*(np.interp(light,recipe["knots"],recipe["values"])-light)
    chroma=np.linalg.norm(original[:,1:],axis=1)
    lab[:,1:]*=1+strength*(recipe["chroma"]-1)
    hue=np.arctan2(original[:,2],original[:,1])
    distance=np.arctan2(np.sin(hue-.95),np.cos(hue-.95))
    warm=np.exp(-.5*(distance/.70)**2)*(1-np.exp(-chroma/12))
    fade=np.sin(np.pi*light/100)**1.1
    warm_weight=warm*(.30+.70*light/100)
    cool_weight=(1-warm)*(.9-.45*light/100)
    if "cool_highlight_fade" in extra:
        low,high=extra["cool_highlight_fade"]
        x=np.clip((light-low)/(high-low),0,1)
        cool_weight*=1-x*x*(3-2*x)
    tint=warm_weight[:,None]*np.array(recipe["warm_ab"])+cool_weight[:,None]*np.array(recipe["cool_ab"])
    if "rose_boost" in extra:
        tint[:,0]+=extra["rose_boost"]*np.clip(original[:,1]/18,0,1)*(1-np.exp(-chroma/12))
    if "neutral_chroma_reduction" in extra:
        neutral=np.exp(-.5*(chroma/18)**2)
        lab[:,1:]*=(1-extra["neutral_chroma_reduction"]*neutral)[:,None]
    lab[:,1:]+=strength*fade[:,None]*tint
    output=encode_gamut(lab)
    output[0],output[-1]=0,1
    return output


def main():
    # Store regenerated examples outside the distributed originals.
    output=ROOT/"assets/luts/derived/showcase-rebuilt"
    output.mkdir(parents=True,exist_ok=True)
    items=json.loads((ROOT/"examples/grades/recipes.json").read_text(encoding="utf-8"))["recipes"]
    for item in items:
        with (output/f'{item["id"]}.cube').open("w",encoding="ascii",newline="\n") as stream:
            stream.write(f'TITLE "Showcase {item["id"]}"\nLUT_3D_SIZE 33\nDOMAIN_MIN 0 0 0\nDOMAIN_MAX 1 1 1\n')
            np.savetxt(stream,bake(item),fmt="%.9f")
    print(json.dumps({"count":len(items),"output":str(output)}))

if __name__=="__main__":main()

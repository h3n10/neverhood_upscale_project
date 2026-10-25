"""Screen an upscaled image against source by downscaling to source geometry.
Metrics are descriptive gates, not evidence of recovered truth or artistic approval.
Uses Pillow only; see knowledge/qa_process.md before interpreting thresholds.
"""
import argparse, json, math
from pathlib import Path
from PIL import Image, ImageFilter, ImageStat

def hist_tv(a, b, bins=32):
    vals=[]
    for plane_a, plane_b in zip(a.split(), b.split()):
        ha=plane_a.histogram(); hb=plane_b.histogram()
        ha=[sum(ha[i*256//bins:(i+1)*256//bins]) for i in range(bins)]
        hb=[sum(hb[i*256//bins:(i+1)*256//bins]) for i in range(bins)]
        sa=sum(ha) or 1; sb=sum(hb) or 1
        vals.append(0.5*sum(abs(x/sa-y/sb) for x,y in zip(ha,hb)))
    return sum(vals)/3

def calc(original, candidate):
    src=Image.open(original).convert('RGB')
    cand=Image.open(candidate).convert('RGB')
    scale=(cand.width/src.width, cand.height/src.height)
    back=cand.resize(src.size, Image.Resampling.LANCZOS)
    gs=src.convert('L'); gb=back.convert('L')
    s1=ImageStat.Stat(gs); s2=ImageStat.Stat(gb)
    m1,m2=s1.mean[0],s2.mean[0]
    v1,v2=s1.stddev[0]**2,s2.stddev[0]**2
    cov=2*ImageStat.Stat(Image.blend(gs,gb,0.5)).stddev[0]**2-(v1+v2)/2
    # Population covariance recovered from variance of the midpoint image.
    c1=(0.01*255)**2; c2=(0.03*255)**2
    ssim=((2*m1*m2+c1)*(2*cov+c2))/((m1*m1+m2*m2+c1)*(v1+v2+c2))
    flat=lambda im: list(im.get_flattened_data()) if hasattr(im, "get_flattened_data") else list(im.getdata())
    mse=sum((x-y)**2 for x,y in zip(flat(gs),flat(gb)))/(src.width*src.height)
    psnr=99.0 if mse==0 else 10*math.log10(255**2/mse)
    lab1=src.convert('LAB'); lab2=back.convert('LAB')
    de=[]
    for p,q in zip(flat(lab1),flat(lab2)):
        dl=(p[0]-q[0])*100/255
        da=p[1]-q[1]; db=p[2]-q[2]
        de.append(math.sqrt(dl*dl+da*da+db*db))
    de.sort()
    e1=gs.filter(ImageFilter.FIND_EDGES).point(lambda x:255 if x>=48 else 0)
    e2=gb.filter(ImageFilter.FIND_EDGES).point(lambda x:255 if x>=48 else 0)
    a=flat(e1); b=flat(e2)
    n1=sum(x>0 for x in a); n2=sum(x>0 for x in b); inter=sum(x>0 and y>0 for x,y in zip(a,b))
    prec=inter/n2 if n2 else (1.0 if not n1 else 0.0)
    rec=inter/n1 if n1 else (1.0 if not n2 else 0.0)
    return {
      'original':str(original),'candidate':str(candidate),'original_size':[src.width,src.height],
      'candidate_size':[cand.width,cand.height],'scale_x':scale[0],'scale_y':scale[1],
      'downscale_back':{'psnr_db':round(psnr,3),'global_ssim':round(ssim,6)},
      'lab_vs_source':{'mean_delta_e76_approx':round(sum(de)/len(de),3),'p95_delta_e76_approx':round(de[int(.95*(len(de)-1))],3),'mean_32bin_channel_TV':round(hist_tv(lab1,lab2),6)},
      'luminance_0_255':{'source_mean':round(m1,3),'candidate_back_mean':round(m2,3),'source_std':round(math.sqrt(v1),3),'candidate_back_std':round(math.sqrt(v2),3)},
      'edge_overlap_threshold_48':{'precision':round(prec,5),'recall':round(rec,5),'f1':round(2*prec*rec/(prec+rec),5) if prec+rec else 1.0},
      'note':'Screening metrics only. Candidate was Lanczos-downscaled to source dimensions; Lab is an approximate Pillow conversion; global SSIM is not a local SSIM map.'}

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--original',required=True,type=Path); p.add_argument('--candidate',required=True,type=Path)
    p.add_argument('--json',type=Path)
    a=p.parse_args(); r=calc(a.original,a.candidate); out=json.dumps(r,indent=2)
    print(out)
    if a.json: a.json.parent.mkdir(parents=True,exist_ok=True); a.json.write_text(out+'\n',encoding='utf-8')
if __name__=='__main__': main()

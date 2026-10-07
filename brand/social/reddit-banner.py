#!/usr/bin/env python3
"""Draw the Reddit banner (1920x384): the mark as an account (the owner, 6 Oct 2026).

The dot is the account's equity; the two floors are the daily limit, which steps with each day's start, and the static
max loss. Whichever floor is closer that day is drawn brighter, so the bright line hands over from the daily steps to the
flat max loss on the day the account starts at the crossover. The example is the 6 Oct 2026 Reddit post's: $100,000,
4% daily on the starting balance ($4,000), 6% static max ($94,000), crossover $98,000; the dot at $96,800.

Reddit's phone app shows only about x 655-1265, y 150-300 of the image (measured from the owner's screenshots, 6 Oct
2026), dimmed: the dot and the hand-over sit inside it, and the two labels sit right of x 1265 so the phone never shows a
cut word. Colours and the background gradient are BRAND.md's.

  python brand/social/reddit-banner.py     # writes brand/social/reddit-banner-1920x384.png
"""
import random
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
K=2; W,H=1920*K,384*K
def hx(h): h=h.lstrip('#'); return tuple(int(h[i:i+2],16) for i in (0,2,4))
BG=[(0,hx('0e1a2e')),(.28,hx('0a1220')),(.70,hx('070b12')),(1,hx('070b12'))]
INK,DIM,LINE,SIG=hx('e6edf5'),hx('7d8aa0'),hx('1c2839'),hx('4da3ff')
img=Image.new('RGB',(W,H)); d0=ImageDraw.Draw(img)
for y in range(H):
    t=y/(H-1)
    for (a,ca),(b,cb) in zip(BG,BG[1:]):
        if a<=t<=b: f=(t-a)/(b-a); c=tuple(round(ca[i]+(cb[i]-ca[i])*f) for i in range(3)); break
    d0.line([(0,y),(W,y)],fill=c)
img=img.convert('RGBA'); ov=Image.new('RGBA',(W,H),(0,0,0,0)); d=ImageDraw.Draw(ov)
Q,DL,MX=100_000,4_000,94_000
starts=[100_000,100_400,99_600,99_900,99_100,98_600,98_900,98_000,97_400,96_500]
X0,XN=80,1150                      # first day start .. the dot (phone shows ~x 655-1265)
dw=(XN-X0)/(len(starts)-1+0.55)    # today is 55% done
def X(x): return round(x*K)
def Y(v): return round((150+(100_800-v)/(100_800-93_000)*150)*K)   # phone shows ~y 150-300
# day hairlines
for i in range(len(starts)):
    x=X(X0+i*dw); d.line([(x,Y(100_900)),(x,Y(92_300))],fill=LINE+(150,),width=K)
# floors: binding stretch brighter
def seg(x1,x2,v,bind): d.line([(X(x1),Y(v)),(X(x2),Y(v))],fill=INK+((170 if bind else 46),),width=3*K//2+1)
for i,ds in enumerate(starts):
    x1=X0+i*dw; x2=(X0+(i+1)*dw) if i<len(starts)-1 else 1920
    df=ds-DL
    for v,b in sorted(((df,df>=MX),(MX,MX>df)),key=lambda t:t[1]): seg(x1,x2,v,b)
    if i: d.line([(X(x1),Y(starts[i-1]-DL)),(X(x1),Y(df))],fill=INK+(40,),width=K)
seg(0,X0,MX,False)
# equity: wanders inside each day, closes at the next day's start
random.seed(6); pts=[]
for i,ds in enumerate(starts):
    end=starts[i+1] if i<len(starts)-1 else 96_800
    span=1 if i<len(starts)-1 else 0.55
    n=40 if i<len(starts)-1 else 22
    for k in range(n):
        f=k/n*span; v=ds+(end-ds)*f/span+random.gauss(0,110)*((f/span)*(1-f/span))**.5*2
        pts.append((X0+(i+f)*dw,v))
pts.append((XN,96_800))
d.line([(X(x),Y(v)) for x,v in pts],fill=DIM+(230,),width=2*K,joint='curve')
fnt=ImageFont.truetype(str(HERE.parent / 'PlexMono-Regular.ttf'),17*K)
for v,t in ((MX,'max loss'),(starts[-1]-DL,'daily limit')):
    w=d.textlength(t,font=fnt); d.text((X(1840)-w,Y(v)-24*K),t,font=fnt,fill=DIM+(255,))
# the dot, with its 18% halo
cx,cy=X(XN),Y(96_800)
for r,a in ((27,46),(16,255)):
    d.ellipse([cx-r*K,cy-r*K,cx+r*K,cy+r*K],fill=SIG+(a,))
out=Image.alpha_composite(img,ov).resize((1920,384),Image.LANCZOS).convert('RGB')
out.save(HERE / 'reddit-banner-1920x384.png', optimize=True)

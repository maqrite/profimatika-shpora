# Векторизация логотипа через libpotrace (ctypes) -> логотип.pdf и фи.pdf
# Запуск: python3 инструменты/obvesti_logotip.py картинка.png стиль/бренд
import ctypes as C, sys
from PIL import Image
lib=C.CDLL("libpotrace.so.0")
W=C.c_ulong; N=C.sizeof(W)*8
class Bitmap(C.Structure): _fields_=[("w",C.c_int),("h",C.c_int),("dy",C.c_int),("map",C.POINTER(W))]
class DP(C.Structure): _fields_=[("x",C.c_double),("y",C.c_double)]
class Curve(C.Structure): _fields_=[("n",C.c_int),("tag",C.POINTER(C.c_int)),("c",C.POINTER(DP*3))]
class Path(C.Structure): pass
Path._fields_=[("area",C.c_int),("sign",C.c_int),("curve",Curve),("next",C.POINTER(Path)),("childlist",C.POINTER(Path)),("sibling",C.POINTER(Path)),("priv",C.c_void_p)]
class State(C.Structure): _fields_=[("status",C.c_int),("plist",C.POINTER(Path)),("priv",C.c_void_p)]
class Progress(C.Structure): _fields_=[("callback",C.c_void_p),("data",C.c_void_p),("min",C.c_double),("max",C.c_double),("epsilon",C.c_double)]
class Param(C.Structure): _fields_=[("turdsize",C.c_int),("turnpolicy",C.c_int),("alphamax",C.c_double),("opticurve",C.c_int),("opttolerance",C.c_double),("progress",Progress)]
lib.potrace_param_default.restype=C.POINTER(Param)
lib.potrace_trace.restype=C.POINTER(State)
lib.potrace_trace.argtypes=[C.POINTER(Param),C.POINTER(Bitmap)]

def trace(mask, w, h):
    dy=(w+N-1)//N
    arr=(W*(dy*h))()
    for y in range(h):
        row=mask[y]
        for x in range(w):
            if row[x]:
                yy=h-1-y   # potrace: y снизу вверх
                arr[yy*dy+x//N] |= (1<<(N-1-(x%N)))
    bm=Bitmap(w,h,dy,C.cast(arr,C.POINTER(W)))
    par=lib.potrace_param_default(); par.contents.turdsize=4; par.contents.alphamax=1.0; par.contents.opttolerance=0.2
    st=lib.potrace_trace(par,C.byref(bm))
    assert st.contents.status==0
    ops=[]
    p=st.contents.plist
    while p:
        cv=p.contents.curve; n=cv.n
        s=cv.c[n-1][2]; ops.append("%.2f %.2f m"%(s.x,s.y))
        for i in range(n):
            seg=cv.c[i]
            if cv.tag[i]==1:
                ops.append("%.2f %.2f %.2f %.2f %.2f %.2f c"%(seg[0].x,seg[0].y,seg[1].x,seg[1].y,seg[2].x,seg[2].y))
            else:
                ops.append("%.2f %.2f l %.2f %.2f l"%(seg[1].x,seg[1].y,seg[2].x,seg[2].y))
        ops.append("h")
        p=p.contents.next
    return "\n".join(ops)

def pdf(fname, layers, w, h):
    content="\n".join("%s rg\n%s\nf*"%(col,path) for col,path in layers).encode()
    objs=[b"<< /Type /Catalog /Pages 2 0 R >>",
          b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
          ("<< /Type /Page /Parent 2 0 R /MediaBox [0 0 %d %d] /Contents 4 0 R /Resources << >> >>"%(w,h)).encode(),
          b"<< /Length %d >>\nstream\n"%len(content)+content+b"\nendstream"]
    out=b"%PDF-1.4\n"; offs=[]
    for i,o in enumerate(objs):
        offs.append(len(out)); out+=b"%d 0 obj\n"%(i+1)+o+b"\nendobj\n"
    x=len(out); out+=b"xref\n0 %d\n0000000000 65535 f \n"%(len(objs)+1)
    for o in offs: out+=b"%010d 00000 n \n"%o
    out+=b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n"%(len(objs)+1,x)
    open(fname,"wb").write(out)

im=Image.open(sys.argv[1]).convert("RGBA")
bb=im.getbbox(); im=im.crop(bb); w,h=im.size
px=im.load()
def m(pred): return [[pred(px[x,y]) for x in range(w)] for y in range(h)]
blue=lambda p: p[3]>127 and p[2]>p[0]+80
black=lambda p: p[3]>127 and not blue(p)
B=m(blue); K=m(black)
# базовая линия: низ буквы «п» (первый столбец с чёрным)
col=[y for y in range(h) if K[y][10]]; base=max(col)+1
print("size",w,h,"baseline from top",base,"descender",h-base)
pk=trace(K,w,h); pb=trace(B,w,h)
pdf(sys.argv[2]+"/логотип.pdf",[("0 0 0",pk),("0 0.604 1",pb)],w,h)
# отдельная φ — обрезать по её рамке
xs=[x for y in range(h) for x in range(w) if B[y][x]]; ys=[y for y in range(h) for x in range(w) if B[y][x]]
x0,x1,y0,y1=min(xs),max(xs)+1,min(ys),max(ys)+1
Bf=[row[x0:x1] for row in B[y0:y1]]
pdf(sys.argv[2]+"/фи.pdf",[("0 0.604 1",trace(Bf,x1-x0,y1-y0))],x1-x0,y1-y0)
print("fi box",x1-x0,y1-y0)

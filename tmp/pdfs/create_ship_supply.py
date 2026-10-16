from pathlib import Path
from decimal import Decimal
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.pagesizes import A4
from reportlab.lib.colors import HexColor, white
from pypdf import PdfReader
import fitz

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'output/pdf/선박_물품공급명세서_예시.pdf'
OUT.parent.mkdir(parents=True, exist_ok=True)
pdfmetrics.registerFont(TTFont('KR', '/System/Library/Fonts/Supplemental/Arial Unicode.ttf'))
W,H=A4
M=32
CW=W-M*2
NAVY=HexColor('#20364D'); INK=HexColor('#202B35'); GRAY=HexColor('#64717D')
LINE=HexColor('#BBC6D0'); PALE=HexColor('#F0F4F7')
c=canvas.Canvas(str(OUT),pagesize=A4)
c.setTitle('선박 물품 공급명세서 - 데이터 추출용 가상 예시')
c.setAuthor('')

def text(x,y,s,size=8.6,color=INK,align='left'):
    c.setFillColor(color); c.setFont('KR',size)
    getattr(c, {'left':'drawString','right':'drawRightString','center':'drawCentredString'}[align])(x,y,str(s))

def line(x1,y1,x2,y2):
    c.setStrokeColor(LINE); c.setLineWidth(.5); c.line(x1,y1,x2,y2)

def box(x,top,width,title,rows):
    c.setFillColor(PALE); c.rect(x,top-23,width,23,fill=1,stroke=0)
    text(x+9,top-16,title,10,NAVY)
    for i,(label,val) in enumerate(rows):
        yy=top-41-i*18
        text(x+9,yy,label,8.1,GRAY)
        text(x+66,yy,val,8.5)
    bottom=top-105
    for a,b,d,e in [(x,top,x+width,top),(x,bottom,x+width,bottom),(x,top,x,bottom),(x+width,top,x+width,bottom)]:line(a,b,d,e)

items=[
('EN-101','주기관 윤활유','SAE 40 / 20 L',12,'통',98000),
('EN-102','유압 작동유','ISO VG 46 / 20 L',6,'통',87000),
('EN-103','오일 필터','OF-220 / 카트리지',8,'개',32500),
('EN-104','연료 필터','FF-310 / 10 μm',10,'개',28000),
('EN-105','해수 펌프 임펠러','IMP-65 / Ø65 mm',3,'개',145000),
('DK-201','계선 로프','PP / Ø24 mm × 200 m',2,'롤',385000),
('DK-202','와이어 로프','6×19 / Ø12 mm × 50 m',2,'롤',215000),
('DK-203','샤클','SUS316 / M20',20,'개',18500),
('SF-301','구명조끼','성인용 / 150 N',15,'벌',68000),
('SF-302','안전모','턱끈형 / 백색',12,'개',24500),
('SF-303','분말 소화기','ABC / 3.3 kg',6,'대',42000),
('EL-401','LED 작업등','AC 220 V / 50 W',8,'개',56000),
('EL-402','선박용 케이블','3C × 2.5 mm² / 100 m',2,'롤',248000),
('PT-501','방청 프라이머','회색 / 18 L',4,'통',135000),
('PT-502','갑판용 페인트','녹색 / 18 L',4,'통',158000),
('CS-601','흡착 패드','유흡착용 / 100매',5,'박스',59000),
]
subtotal=sum(q*price for code,name,spec,q,unit,price in items)
vat=int(Decimal(subtotal)*Decimal('0.10'))
total=subtotal+vat

c.setFillColor(NAVY);c.rect(M,H-38,28,3,fill=1,stroke=0)
text(M,H-69,'선박 물품 공급명세서',22,NAVY)
text(M,H-89,'SHIP SUPPLY STATEMENT / 납품 및 인수 확인',9.2,GRAY)
text(W-M,H-46,'문서번호  HBM-SS-2026-1015-001',8.4,INK,'right')
text(W-M,H-63,'발행일자  2026-10-15',8.4,INK,'right')
text(W-M,H-80,'거래구분  선용품 일괄 공급',8.4,INK,'right')

bw=(CW-12)/2
box(M,735,bw,'공급자 | 한빛마린서플라이㈜',[
    ('대표자','이도현'),('소재지','부산광역시 영도구 해양로 120'),
    ('담당자','김민수 / 영업팀'),('연락처','supply@example.com')])
box(M+bw+12,735,bw,'공급받는 자 | 청해해운㈜',[
    ('대표자','박서윤'),('소재지','부산광역시 중구 중앙대로 88'),
    ('담당자','정우진 / 자재구매팀'),('연락처','purchasing@example.com')])

text(M+2,612,'선박명  M/V CHEONGHAE STAR',9)
text(M+282,612,'발주번호  CHS-PO-2026-1008',9)
text(M+2,593,'공급일  2026-10-15',9)
text(M+171,593,'공급장소  부산항 제3부두',9)
text(M+364,593,'납품상태  전 품목 인도 완료',9)
text(M,570,'공급 물품 내역',11,NAVY)
text(W-M,570,'통화: KRW / 단가·금액: 부가세 별도',8.2,GRAY,'right')

top=558; head=25; rh=21
widths=[20,44,101,99,23,25,54,CW-366]
labels=['번호','품목코드','품명','규격 / 사양','수량','단위','단가 (원)','금액 (원)']
assert abs(sum(widths)-CW)<.01
c.setFillColor(NAVY);c.rect(M,top-head,CW,head,fill=1,stroke=0)
xs=[M]
for w in widths:xs.append(xs[-1]+w)
for j,label in enumerate(labels):text((xs[j]+xs[j+1])/2,top-16,label,7.9,white,'center')
for i,(code,name,spec,q,unit,price) in enumerate(items):
    yt=top-head-i*rh
    if i%2==1:
        c.setFillColor(PALE);c.rect(M,yt-rh,CW,rh,fill=1,stroke=0)
    vals=[str(i+1),code,name,spec,str(q),unit,f'{price:,}',f'{q*price:,}']
    for j,value in enumerate(vals):
        fs=7.7 if j in [1,3] else 8.2
        if j in [0,4,5]:text((xs[j]+xs[j+1])/2,yt-14,value,fs,INK,'center')
        elif j in [6,7]:text(xs[j+1]-5,yt-14,value,fs,INK,'right')
        else:text(xs[j]+5,yt-14,value,fs)
    line(M,yt-rh,W-M,yt-rh)
bottom=top-head-len(items)*rh
for x in xs:line(x,top-head,x,bottom)

yt=bottom-8
sum_width=CW/3
for i,(label,value) in enumerate([('공급가액',subtotal),('부가세 (10%)',vat),('합계금액',total)]):
    x=M+i*sum_width
    c.setFillColor(PALE if i<2 else NAVY);c.rect(x,yt-31,sum_width,31,fill=1,stroke=0)
    color=INK if i<2 else white
    text(x+8,yt-19,label,8.3,color)
    text(x+sum_width-8,yt-19,f'{value:,} 원',10,color,'right')

y=yt-50
text(M,y,'지급조건  납품일로부터 30일 이내 계좌이체  |  포장·운송비  공급자 부담',8.5)
text(M,y-17,'비고  전 품목 주문 수량대로 공급 완료. 오일 필터 및 연료 필터는 기관실에 직접 인도함.',8.5)
text(M,y-36,'위 물품을 공급하였으며, 공급받는 자는 품목 및 수량을 확인하고 인수하였습니다.',9,NAVY)
line(M,y-45,W-M,y-45)
text(M+8,y-63,'공급 담당  김민수  (예시)',9)
text(M+270,y-63,'인수 담당  정우진 / 1등 기관사  (예시)',9)
text(M+8,y-81,'공급일자  2026-10-15',8.5,GRAY)
text(M+270,y-81,'인수일자  2026-10-15',8.5,GRAY)
line(M,35,W-M,35)
text(M,22,'데이터 추출 연습용 가상 문서 · 회사, 선박, 거래 내역 및 확인자 정보는 모두 예시입니다.',7.7,GRAY)
text(W-M,22,'1 / 1',8,GRAY,'right')
c.save()

r=PdfReader(str(OUT))
assert len(r.pages)==1
t=r.pages[0].extract_text()
assert '�' not in t
for code,name,spec,q,unit,price in items:
    assert code in t and name in t and f'{q*price:,}' in t
assert f'{total:,}' in t
doc=fitz.open(OUT)
assert all(b[0]>=M-1 and b[2]<=W-M+1 and b[1]>=10 and b[3]<=H-10 for b in doc[0].get_text('blocks'))
doc[0].get_pixmap(matrix=fitz.Matrix(2,2)).save(str(ROOT/'tmp/pdfs/ship_supply_preview.png'))
print({'pages':len(r.pages),'items':len(items),'subtotal':subtotal,'vat':vat,'total':total,'output':str(OUT),'signature_bottom':y-81})

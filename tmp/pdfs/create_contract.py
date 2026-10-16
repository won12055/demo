from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import HexColor, white
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph
from reportlab.lib.pagesizes import A4
from pypdf import PdfReader
import fitz

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'output/pdf/물품공급계약서_양식.pdf'
OUT.parent.mkdir(parents=True, exist_ok=True)
pdfmetrics.registerFont(TTFont('KR', '/System/Library/Fonts/Supplemental/Arial Unicode.ttf'))
W, H = A4
M = 43
CW = W - 2*M
NAVY = HexColor('#20354B')
TEAL = HexColor('#256D74')
INK = HexColor('#252F39')
GRAY = HexColor('#687480')
LINE = HexColor('#C8D0D8')
PALE = HexColor('#F2F5F7')
c = canvas.Canvas(str(OUT), pagesize=A4)
c.setTitle('물품 공급계약서 - 기입식 양식')
c.setAuthor('')

def text(x, y, s, size=9.3, color=INK):
    c.setFont('KR', size)
    c.setFillColor(color)
    c.drawString(x, y, s)

def para(s, x, top, width, size=9.3, leading=15, color=INK):
    p = Paragraph(s, ParagraphStyle('p', fontName='KR', fontSize=size,
        leading=leading, textColor=color, wordWrap='CJK'))
    _, h = p.wrap(width, 1000)
    p.drawOn(c, x, top-h)
    return h

def line(x1, y1, x2, y2, color=LINE):
    c.setStrokeColor(color)
    c.setLineWidth(.55)
    c.line(x1, y1, x2, y2)

def section(y, n, title):
    text(M, y, n, 9, TEAL)
    text(M+25, y, title, 11.5, NAVY)
    line(M, y-9, W-M, y-9)
    return y-20

def header(page, subtitle):
    c.setFillColor(NAVY)
    c.rect(M, H-49, 28, 4, fill=1, stroke=0)
    text(M, H-81, '물품 공급계약서', 24, NAVY)
    text(M, H-103, subtitle, 9.1, GRAY)
    text(W-M-118, H-56, '일반 거래용 · 기입식 양식', 8.3, GRAY)
    line(M, 38, W-M, 38)
    text(M, 24, '물품 공급계약서 | 거래 조건과 특약을 작성한 뒤 서명 또는 날인하세요.', 7.4, GRAY)
    text(W-M-26, 24, f'{page} / 2', 8, GRAY)

def field_rows(x, top, width, rows, height=27, label_width=87):
    for i, (label, value) in enumerate(rows):
        y=top-i*height
        c.setFillColor(PALE)
        c.rect(x, y-height, label_width, height, stroke=0, fill=1)
        text(x+9, y-height/2-3.3, label, 9)
        text(x+label_width+9, y-height/2-3.3, value, 9)
        line(x, y, x+width, y)
    bottom=top-len(rows)*height
    line(x, bottom, x+width, bottom)
    line(x, top, x, bottom)
    line(x+label_width, top, x+label_width, bottom)
    line(x+width, top, x+width, bottom)
    return bottom

header(1, '01  계약 당사자 및 거래 조건')
para('아래 구매자(이하 “갑”)와 공급자(이하 “을”)는 다음 거래 조건 및 제2쪽의 계약 조항에 따라 물품 공급계약을 체결한다.', M, 718, CW, 9.4, 15)
y=section(671, '01', '계약 당사자')
gap=14
bw=(CW-gap)/2
for x, name in [(M,'구매자 (갑)'), (M+bw+gap,'공급자 (을)')]:
    c.setFillColor(PALE)
    c.rect(x, y-25, bw, 25, stroke=0, fill=1)
    text(x+10, y-17, name, 10.3, NAVY)
    for j, label in enumerate(['상호 / 성명', '사업자등록번호', '대표자', '주소', '담당자 / 연락처']):
        yy=y-45-j*23
        text(x+8, yy, label, 8.5, GRAY)
        line(x+83, yy-3, x+bw-8, yy-3)
    line(x, y, x+bw, y)
    line(x, y-151, x+bw, y-151)
    line(x, y, x, y-151)
    line(x+bw, y, x+bw, y-151)
y=section(476, '02', '공급 물품 및 계약금액')
widths=[26,133,108,45,38,79,CW-429]
labels=['번호','품명 / 모델명','규격 / 사양','수량','단위','단가 (원)','공급가액 (원)']
top=y
rh=27
c.setFillColor(PALE)
c.rect(M, top-rh, CW, rh, fill=1, stroke=0)
xx=M
for width, label in zip(widths,labels):
    c.setFont('KR', 8.1)
    c.setFillColor(INK)
    c.drawCentredString(xx+width/2, top-17, label)
    line(xx, top, xx, top-rh*5)
    xx+=width
line(W-M,top,W-M,top-rh*5)
for i in range(6):
    line(M,top-rh*i,W-M,top-rh*i)
for i in range(4):
    text(M+10,top-rh*(i+1)-17,str(i+1),8.5,GRAY)
text(M, top-rh*5-16, '※ 품목이 많으면 별지 명세서를 첨부하고, 각 품목의 공급가액은 수량 × 단가로 기재합니다.', 8, GRAY)
y=top-rh*5-29
y=field_rows(M,y,CW,[('계약금액','공급가액:                      원    +    부가세:                      원'),('합계 (원)','금                                                        원정  (₩                                )')],25)
y=section(y-28,'03','납품 · 검수 · 대금 지급')
y=field_rows(M,y,CW,[('납품일 / 장소','           년         월         일  /'),('배송 · 설치비','부담자:                              / 포함 범위:'),('검수 / 품질보증','수령 후           일 이내 검수 / 검수 완료일부터           개월'),('지급 일정','선금:                       원 (       /       )  / 잔금:                       원 (       /       )'),('입금 계좌','은행:                       / 계좌번호:                                / 예금주:')],26)
text(M, y-17, '※ 지급일은 연·월·일까지 명확히 적고, 선금과 잔금의 합계가 계약금액과 일치하는지 확인합니다.', 8, GRAY)
c.showPage()

header(2, '02  계약 조항 및 서명')
y=718
clauses=[
('제1조  목적 및 계약 내용', '을은 제1쪽의 물품을 갑에게 공급하고 갑은 약정한 대금을 지급한다. 품질·사양은 이 계약 및 당사자가 확인한 명세서에 따른다. 변경 사항은 당사자가 서면으로 합의한다.'),
('제2조  납품 및 검수', '을은 약정한 기일과 장소에 물품을 납품한다. 갑은 제1쪽의 기간 내에 수량·사양·외관 등을 검수하고 불일치 사항을 을에게 알린다. 단순 수령이나 검수 기간 경과만으로 숨은 하자에 관한 권리를 포기한 것으로 보지 않는다.'),
('제3조  대금 지급', '갑은 제1쪽의 지급 일정과 계좌에 따라 대금을 지급한다. 을은 관련 법령에 따른 증빙을 발행한다. 지급 조건이나 납품 일정의 변경이 필요한 경우 당사자가 서면으로 정한다.'),
('제4조  하자 및 품질보증', '을의 책임으로 발생한 하자 또는 계약 내용과 다른 물품은 을이 비용을 부담하여 합리적인 기간 내에 수리 또는 교환한다. 이행이 불가능하거나 시정되지 않으면 당사자는 대금 감액 또는 해당 물품의 반품·환급을 협의한다. 품질보증 약정은 법령상 권리를 제한하지 않는다.'),
('제5조  계약 위반 및 해제', '일방이 계약을 위반하면 상대방은 서면으로 상당한 시정 기간을 정하여 이행을 요구하고, 기간 내 시정되지 않으면 계약을 해제할 수 있다. 해제 시 물품 반환과 대금 환급 등 정산을 진행한다. 귀책 있는 당사자는 법령에 따른 손해배상 책임을 부담한다.'),
('제6조  불가항력', '천재지변 등 당사자가 합리적으로 통제할 수 없는 사유가 발생하면 지체 없이 상대방에게 알리고 피해를 줄이기 위해 노력한다. 이행 기간의 연장이나 계약 종료 및 정산은 당사자가 협의한다.'),
('제7조  분쟁 해결 및 기타', '이 계약은 대한민국 법령에 따른다. 분쟁은 우선 협의로 해결하며, 협의가 이루어지지 않으면 관계 법령에 따른 관할 법원에서 해결한다. 별지 명세서와 서면 특약은 계약의 일부이며, 강행법규에 반하지 않는 범위에서 특약을 우선 적용한다.'),
]
for title, body in clauses:
    text(M,y,title,10.2,NAVY)
    h=para(body,M,y-10,CW,9.1,14)
    y-=10+h+13

y=section(y-1,'04','특약 사항 및 첨부 문서')
for i in range(2):
    line(M, y-17-i*23,W-M,y-17-i*23)
text(M,y-57,'첨부: 물품 명세서 (        쪽) / 기타:                                                                  ',8.6,GRAY)
y-=82
para('갑과 을은 계약 내용을 확인하고 계약서 2부를 작성하여 서명 또는 날인한 뒤 각 1부씩 보관한다.',M,y,CW,9.2,15)
y-=37
c.setFont('KR',11)
c.setFillColor(NAVY)
c.drawCentredString(W/2,y,'계약 체결일:                 년             월             일')
y-=21
for x,label in [(M,'구매자 (갑)'),(M+bw+gap,'공급자 (을)')]:
    c.setStrokeColor(LINE)
    c.setLineWidth(.6)
    c.rect(x,y-76,bw,76,stroke=1,fill=0)
    text(x+10,y-19,label,10,NAVY)
    text(x+10,y-43,'상호 / 성명:',9)
    text(x+10,y-63,'대표자:',9)
    text(x+bw-69,y-63,'(서명 / 인)',9,GRAY)
text(M, 51, '양식 참고: 국가법령정보센터, 민법 제563조·제568조 | 일반 물품 거래에 맞게 빈칸과 특약을 작성하세요.',7.1,GRAY)
c.linkURL('https://www.law.go.kr/lsInfoP.do?ancYnChk=0&lsId=001706',(M,48,W-M,61),relative=0)
c.save()

r=PdfReader(str(OUT))
assert len(r.pages)==2
for i,p in enumerate(r.pages):
    t=p.extract_text()
    assert '물품 공급계약서' in t
    assert '�' not in t
    print(f'page {i+1}: {len(t)} extracted characters')
doc=fitz.open(OUT)
for i,page in enumerate(doc):
    page.get_pixmap(matrix=fitz.Matrix(1.6,1.6)).save(str(ROOT/f'tmp/pdfs/contract_page_{i+1}.png'))
print(OUT)
print(f'page2 signature bottom: {y-76:.1f} pt')

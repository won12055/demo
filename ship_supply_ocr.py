#!/usr/bin/env python3
"""선박 물품 공급명세서 OCR 예제 (Python 3.9 이상, 소스 파일 1개).

설치:
    python3 -m pip install pymupdf pillow tesserocr
실행 (같은 폴더의 예시 PDF를 자동 선택):
    python3 ship_supply_ocr.py
다른 경로 지정:
    python3 ship_supply_ocr.py "공급명세서.pdf" --out "output/ocr"

PDF를 300 DPI 이미지로 렌더링한 뒤 Tesseract로 실제 OCR을 수행한다.
PDF 텍스트 레이어나 원본 생성 코드의 물품 데이터는 읽지 않는다.
처음 실행할 때 공식 tessdata_fast의 한국어/영어 모델을 내려받는다.
이후에는 모델을 재사용하며 로컬에서 OCR한다. 별도 API 키는 필요 없다.

대상: 함께 만든 '선박_물품공급명세서_예시.pdf'의 A4 세로 8열 표.
같은 비율의 PNG/JPG도 입력 가능하다. 다른 양식은 아래 TABLE_AREA와
COLUMN_EDGES를 수정해야 한다. 회전/원근이 있는 사진은 먼저 보정해야 한다.
행은 이미지의 가로 구분선을 탐지한다. 품목 내용/개수/정답은 내장하지 않는다.
OCR 결과는 정답을 보장하지 않으므로 raw_cells, confidence, issues를 확인한다.

출력: <원본명>_items.csv, <원본명>_result.json, <원본명>_ocr.txt
종료 코드: 0=추출 및 금액 검증 통과, 1=실행 오류, 2=검토 필요.

참고 API:
https://pypi.org/project/tesserocr/
https://pymupdf.readthedocs.io/en/latest/recipes-images.html
https://github.com/tesseract-ocr/tessdata_fast
"""

import argparse
import csv
import json
import re
import sys
import unicodedata
from contextlib import ExitStack
from decimal import Decimal
from pathlib import Path
from urllib.request import urlopen

# 원본 PDF의 포인트 좌표를 사용하며, 실제 이미지 크기에 비례해 환산한다.
PAGE_WIDTH, PAGE_HEIGHT = 595.2756, 841.8898
# (왼쪽, 위, 오른쪽, 아래): 머리글 하단부터 마지막 품목 바로 아래까지.
TABLE_AREA = (32, 303, 563.2756, 648)
COLUMN_EDGES = (32, 52, 96, 197, 296, 319, 344, 398, 563.2756)
FIELDS = ("번호", "품목코드", "품명", "규격", "수량", "단위", "단가", "금액")
NUMBER_FIELDS = {"번호", "수량", "단가", "금액"}
# 합계 요약 칸도 OCR로 읽어, 품목 금액 합계와 대조한다.
SUMMARY_BOXES = {
    "공급가액": (91, 654, 208, 682),
    "부가세": (272, 654, 386, 682),
    "합계금액": (447, 654, 559, 682),
}


def ensure_models(directory):
    """학습 데이터만 다운로드한다. 사용자 문서는 전송하지 않는다."""
    directory.mkdir(parents=True, exist_ok=True)
    for language in ("kor", "eng"):
        target = directory / f"{language}.traineddata"
        if target.is_file() and target.stat().st_size > 100_000:
            continue
        url = f"https://raw.githubusercontent.com/tesseract-ocr/tessdata_fast/main/{language}.traineddata"
        print(f"OCR 모델 다운로드: {language}", flush=True)
        partial = target.with_suffix(".download")
        try:
            with urlopen(url, timeout=90) as response, partial.open("wb") as f:
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    f.write(chunk)
            if partial.stat().st_size < 100_000:
                raise RuntimeError(f"{language} 모델 파일이 비정상적으로 작습니다.")
            partial.replace(target)
        finally:
            partial.unlink(missing_ok=True)


def load_pages(path, dpi):
    from PIL import Image, ImageOps
    import pymupdf

    if path.suffix.lower() == ".pdf":
        with pymupdf.open(path) as document:
            if document.needs_pass:
                raise ValueError("암호화된 PDF입니다. 암호를 해제한 파일을 사용하세요.")
            for page in document:
                pixmap = page.get_pixmap(dpi=dpi, colorspace=pymupdf.csRGB, alpha=False)
                yield Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)
    else:
        with Image.open(path) as source:
            yield ImageOps.exif_transpose(source).convert("RGB")


def crop(image, box, padding=0):
    sx, sy = image.width / PAGE_WIDTH, image.height / PAGE_HEIGHT
    left, top, right, bottom = box
    return image.crop((round((left+padding)*sx), round((top+padding)*sy),
                       round((right-padding)*sx), round((bottom-padding)*sy)))


def find_rows(image):
    """긴 가로 구분선을 찾아 각 행의 위아래 경계를 반환한다."""
    sx, sy = image.width / PAGE_WIDTH, image.height / PAGE_HEIGHT
    left, top, right, bottom = TABLE_AREA
    gray = image.convert("L")
    x0, x1 = round((left+2)*sx), round((right-2)*sx)
    groups = []
    for y in range(round(top*sy), round(bottom*sy)):
        histogram = gray.crop((x0, y, x1, y+1)).histogram()
        is_line = sum(histogram[:225]) / (x1-x0) >= 0.93
        if is_line:
            if groups and y == groups[-1][-1]+1:
                groups[-1].append(y)
            else:
                groups.append([y])
    # 처음 구간은 진한 머리글이므로 그 구간의 마지막 픽셀을 사용한다.
    edges = [(g[-1] if i == 0 else sum(g)/len(g))/sy
             for i,g in enumerate(groups)]
    rows = [(a,b) for a,b in zip(edges,edges[1:]) if 15 <= b-a <= 28]
    if not rows or len(rows) != len(edges)-1:
        raise ValueError("품목 표의 행 구분선을 찾지 못했습니다. 양식·해상도·회전을 확인하세요.")
    return rows


def recognize(api, image, whitelist=""):
    """한 칸을 읽고, 정규화 전 원문과 엔진 신뢰도를 함께 돌려준다."""
    from PIL import ImageOps
    api.SetVariable("tessedit_char_whitelist", whitelist)
    gray = image.convert("L")
    # 진한 배경의 합계 칸은 흑백을 반전하여 읽는다.
    if gray.resize((1,1)).getpixel((0,0)) < 140:
        gray = ImageOps.invert(gray)
    gray = ImageOps.autocontrast(gray)
    gray = ImageOps.expand(gray, border=12, fill=255)
    api.SetImage(gray)
    raw = api.GetUTF8Text().strip()
    confidence = api.MeanTextConf()
    return raw, confidence


def integer_or_none(raw):
    """인식 불가 숫자를 0으로 바꾸거나 추측하여 채우지 않는다."""
    value = re.sub(r"\s+", "", unicodedata.normalize("NFKC",raw)).replace("원", "").replace("₩", "")
    if not re.fullmatch(r"(?:\d+|\d{1,3}(?:,\d{3})+)", value):
        return None
    return int(value.replace(",", ""))


def extract_page(image, page_number, text_api, number_api, spec_api, confidence_threshold):
    if abs(image.width/image.height - PAGE_WIDTH/PAGE_HEIGHT) > 0.015:
        raise ValueError("A4 세로 비율의 문서가 아닙니다. 현재 코드는 예시 명세서 양식용입니다.")
    rows = find_rows(image)
    items, issues = [], []
    for row_number, (top,bottom) in enumerate(rows,1):
        values, raw_cells, confidences = {}, {}, {}
        spec_alternative = None
        for j,field in enumerate(FIELDS):
            cell = crop(image, (COLUMN_EDGES[j], top, COLUMN_EDGES[j+1], bottom), padding=1.8)
            numeric = field in NUMBER_FIELDS
            english = numeric or field == "품목코드"
            whitelist = "0123456789," if numeric else (
                "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-" if field == "품목코드" else "")
            api = number_api if english else (spec_api if field == "규격" else text_api)
            raw, conf = recognize(api, cell, whitelist)
            if field == "규격":
                # 언어 우선순위를 바꾸어 다시 읽고, 결과가 다르면 사람이 확인한다.
                alternate, alternate_conf = recognize(text_api,cell)
                spec_alternative = {"text":alternate,"confidence":alternate_conf}
            raw_cells[field], confidences[field] = raw, conf
            values[field] = integer_or_none(raw) if numeric else " ".join(unicodedata.normalize("NFKC",raw).split())
        row_issues = []
        for field,value in values.items():
            if value is None or value == "":
                row_issues.append(f"{field}: 값 인식 실패")
            if confidences[field] < confidence_threshold:
                row_issues.append(f"{field}: 낮은 OCR 신뢰도 ({confidences[field]})")
        if values["번호"] != row_number:
            row_issues.append(f"행 번호 불일치: 위치 {row_number}, 인식 {values['번호']}")
        if not re.fullmatch(r"[A-Z]{2}-\d{3}", values["품목코드"]):
            row_issues.append("품목코드 형식 확인 필요")
        compare = lambda s: re.sub(r"\s+","",unicodedata.normalize("NFKC",s))
        if compare(raw_cells["규격"]) != compare(spec_alternative["text"]):
            row_issues.append("규격: 언어 우선순위에 따른 인식 차이, 원문 대조 필요")
        if any(symbol in values["규격"] for symbol in ("@","?")):
            row_issues.append("규격: 기술 기호 오인식 가능성, 원문 대조 필요")
        q,p,a = values["수량"],values["단가"],values["금액"]
        matches = q*p == a if all(v is not None for v in (q,p,a)) else None
        if matches is not True:
            row_issues.append("수량 × 단가와 금액이 다르거나 검증 불가")
        items.append({"페이지":page_number, **values, "금액검증":matches,
                      "검토필요":bool(row_issues), "issues":row_issues,
                      "raw_cells":raw_cells, "confidence":confidences,
                      "규격_대체인식":spec_alternative})
        issues.extend(f"{row_number}행: {message}" for message in row_issues)
        print(f"  {row_number:2d}행 | {values['품목코드']} | {values['품명']} | 금액 {a}", flush=True)

    summary, summary_raw, summary_confidence = {}, {}, {}
    for field,box in SUMMARY_BOXES.items():
        raw, conf = recognize(text_api, crop(image,box,1))
        summary[field], summary_raw[field], summary_confidence[field] = integer_or_none(raw),raw,conf
        if summary[field] is None or conf < confidence_threshold:
            issues.append(f"요약 {field}: 인식 결과/신뢰도 확인 필요 ({raw!r}, {conf})")
    amounts = [item["금액"] for item in items]
    calculated = sum(amounts) if all(a is not None for a in amounts) else None
    checks = {
        "모든_행_금액일치":all(item["금액검증"] is True for item in items),
        "품목합계_공급가액일치":calculated == summary["공급가액"] if calculated is not None and summary["공급가액"] is not None else None,
        "부가세_10퍼센트일치":int(Decimal(summary["공급가액"])*Decimal("0.10")) == summary["부가세"] if summary["공급가액"] is not None and summary["부가세"] is not None else None,
        "최종합계일치":summary["공급가액"]+summary["부가세"] == summary["합계금액"] if all(v is not None for v in summary.values()) else None,
    }
    issues.extend(name for name,ok in checks.items() if ok is not True)
    return {"페이지":page_number, "품목수":len(items), "품목":items,
            "요약":summary, "요약원문":summary_raw, "요약신뢰도":summary_confidence,
            "계산한공급가액":calculated, "검증":checks, "issues":issues}


def save_results(result, output_dir, stem):
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / f"{stem}_result.json"
    csv_path = output_dir / f"{stem}_items.csv"
    raw_path = output_dir / f"{stem}_ocr.txt"
    json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    columns = ["페이지", *FIELDS, "금액검증", "검토필요", "검토사유"]
    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f,fieldnames=columns)
        writer.writeheader()
        for page in result["pages"]:
            for item in page["품목"]:
                row = {key:item.get(key) for key in columns if key != "검토사유"}
                row["검토사유"] = " / ".join(item["issues"])
                writer.writerow(row)
    lines=[]
    for page in result["pages"]:
        lines.append(f"[페이지 {page['페이지']}]")
        lines.append("\t".join(FIELDS))
        for item in page["품목"]:
            lines.append("\t".join(item["raw_cells"][field].replace("\n"," ") for field in FIELDS))
        lines.append("요약 OCR: " + json.dumps(page["요약원문"],ensure_ascii=False))
    raw_path.write_text("\n".join(lines)+"\n",encoding="utf-8")
    return csv_path,json_path,raw_path


def main(argv=None):
    base = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("input",nargs="?",type=Path,default=base/"output/pdf/선박_물품공급명세서_예시.pdf")
    parser.add_argument("--out",type=Path,default=base/"output/ocr",help="결과를 저장할 폴더")
    parser.add_argument("--tessdata",type=Path,help="언어 모델 폴더 (기본: 결과 폴더의 .tessdata)")
    parser.add_argument("--dpi",type=int,default=300,help="PDF 이미지 해상도 (기본 300)")
    parser.add_argument("--min-confidence",type=int,default=70,help="이 값 미만인 칸을 검토 대상으로 표시")
    args=parser.parse_args(argv)
    if not args.input.is_file():
        parser.error(f"입력 파일이 없습니다: {args.input}")
    if not 150 <= args.dpi <= 600:
        parser.error("--dpi는 150~600 사이로 지정하세요.")
    if not 0 <= args.min_confidence <= 100:
        parser.error("--min-confidence는 0~100 사이로 지정하세요.")
    try:
        import pymupdf
        from PIL import Image
        from tesserocr import PyTessBaseAPI, PSM, OEM
    except ImportError as exc:
        print(f"필수 라이브러리를 설치하세요: python3 -m pip install pymupdf pillow tesserocr\n{exc}",file=sys.stderr)
        return 1
    try:
        model_dir=args.tessdata or args.out/".tessdata"
        ensure_models(model_dir)
        pages=[]
        with ExitStack() as stack:
            options={"path":str(model_dir),"psm":PSM.SINGLE_LINE,"oem":OEM.LSTM_ONLY}
            text_api=stack.enter_context(PyTessBaseAPI(lang="kor+eng",**options))
            number_api=stack.enter_context(PyTessBaseAPI(lang="eng",**options))
            spec_api=stack.enter_context(PyTessBaseAPI(lang="eng+kor",**options))
            for number,image in enumerate(load_pages(args.input,args.dpi),1):
                print(f"페이지 {number} OCR 처리 중...",flush=True)
                try:
                    pages.append(extract_page(image,number,text_api,number_api,spec_api,args.min_confidence))
                finally:
                    image.close()
        if not pages:
            raise ValueError("입력에 처리할 페이지가 없습니다.")
        needs_review=any(page["issues"] for page in pages)
        result={"source":str(args.input.resolve()),"engine":"Tesseract / tesserocr",
                "template":"선박_물품공급명세서_예시", "needs_review":needs_review,"pages":pages}
        paths=save_results(result,args.out,args.input.stem)
        print(f"\n완료: {len(pages)}쪽 / {sum(page['품목수'] for page in pages)}개 품목")
        for path in paths:
            print(f"저장: {path.resolve()}")
        if needs_review:
            print("검토 필요: JSON의 issues 및 raw_cells를 확인하세요.")
            return 2
        print("행별 금액, 공급가액, 부가세, 합계금액 검증 통과")
        return 0
    except Exception as exc:
        print(f"OCR 실행 실패: {exc}",file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

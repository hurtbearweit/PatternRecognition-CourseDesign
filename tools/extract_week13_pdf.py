from pathlib import Path


pdf_path = Path(r"D:\大三下\模式识别课设\本周进展说明及下周计划报告\十三周\41-无人机视角下目标检测-十三周工作进展及下周计划报告.pdf")

try:
    import fitz

    doc = fitz.open(str(pdf_path))
    for i, page in enumerate(doc, start=1):
        print(f"\n===== PAGE {i} =====")
        print(page.get_text())
except Exception as exc:
    print(f"PyMuPDF failed: {exc}")
    try:
        from pypdf import PdfReader

        reader = PdfReader(str(pdf_path))
        for i, page in enumerate(reader.pages, start=1):
            print(f"\n===== PAGE {i} =====")
            print(page.extract_text())
    except Exception as exc2:
        print(f"pypdf failed: {exc2}")

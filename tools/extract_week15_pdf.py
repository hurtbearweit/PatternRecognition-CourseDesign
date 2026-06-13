from pathlib import Path

pdf_path = Path(r"D:\大三下\模式识别课设\本周进展说明及下周计划报告\十五周\第十五周小组任务安排.pdf")

try:
    from pypdf import PdfReader

    reader = PdfReader(str(pdf_path))
    for i, page in enumerate(reader.pages, start=1):
        print(f"\n===== PAGE {i} =====")
        print(page.extract_text() or "")
except Exception as exc:
    print(f"PDF extraction failed: {exc}")

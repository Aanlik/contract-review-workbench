from pathlib import Path

import fitz


def main() -> int:
    output = Path("data/samples/sample-scanned-contract.pdf")
    output.parent.mkdir(parents=True, exist_ok=True)
    document = fitz.open()
    page = document.new_page(width=595, height=842)
    page.insert_text((72, 96), "合同签订日期：2026年7月18日", fontsize=22, fontname="china-s")
    page.insert_text((72, 140), "甲方盖章：有", fontsize=22, fontname="china-s")
    page.insert_text((72, 184), "乙方盖章：有", fontsize=22, fontname="china-s")
    pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
    image_pdf = fitz.open()
    image_page = image_pdf.new_page(width=595, height=842)
    image_page.insert_image(image_page.rect, pixmap=pixmap)
    image_pdf.save(output)
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

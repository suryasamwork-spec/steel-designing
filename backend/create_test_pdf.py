import fitz

def create_test_pdf(filename):
    doc = fitz.open()
    page = doc.new_page()
    # Add some text that matches our regex
    page.insert_text((100, 100), "W12x26 (12)")
    page.insert_text((100, 150), "[EL. 10'-0\"]")
    doc.save(filename)
    doc.close()
    print(f"Created valid test PDF: {filename}")

if __name__ == "__main__":
    create_test_pdf("test_valid.pdf")

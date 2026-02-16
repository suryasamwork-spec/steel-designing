import fitz
import io
print(f"✅ fitz version: {fitz.__doc__}")

# Create a dummy PDF with 1 page
doc = fitz.open()
page = doc.new_page()
page.insert_text((100, 100), "Test PDF Rendering")

# Convert to bytes
pdf_bytes = doc.tobytes()
doc.close()

# Try opening it from bytes
try:
    doc2 = fitz.open(stream=pdf_bytes, filetype="pdf")
    print(f"✅ Successfully opened PDF from stream. Pages: {len(doc2)}")
    page2 = doc2[0]
    pix = page2.get_pixmap()
    print(f"✅ Successfully rendered pixmap: {pix.width}x{pix.height}")
    doc2.close()
except Exception as e:
    print(f"❌ fitz error: {e}")

import io
import re
import numpy as np
import fitz  # PyMuPDF
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from PIL import Image, ImageFilter
import cv2
import tempfile
import os

app = FastAPI(title="Structural Drawing API")

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize EasyOCR reader (lazy load)
ocr_reader = None

def get_ocr_reader():
    global ocr_reader
    if ocr_reader is None:
        import easyocr
        print("🔄 Initializing EasyOCR...")
        # gpu=False for cpu-only environments
        ocr_reader = easyocr.Reader(['en'], gpu=False)
        print("✅ EasyOCR ready!")
    return ocr_reader

@app.get("/")
async def root():
    return {"message": "Structural Drawing API is running"}

@app.post("/api/render-page")
async def render_page(
    pdf: UploadFile = File(...),
    page_num: int = Form(0),
    zoom: float = Form(2.0)
):
    """Render a PDF page to an image for the frontend."""
    print(f"📥 Render request: Page {page_num}, Zoom {zoom}")
    try:
        import traceback
        pdf_bytes = await pdf.read()
        print(f"📄 Read {len(pdf_bytes)} bytes")
        
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        if page_num >= len(doc):
            doc.close()
            raise HTTPException(status_code=400, detail="Page number out of range")
        
        page = doc[page_num]
        print(f"📄 Page Dim: {page.rect.width}x{page.rect.height}")
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat)
        print(f"🖼️ Pixmap Generated: {pix.width}x{pix.height}")
        
        img_bytes = pix.tobytes("png")
        print(f"📦 Encoded to PNG: {len(img_bytes)} bytes")
        doc.close()
        
        from fastapi import Response
        return Response(content=img_bytes, media_type="image/png")
    except Exception as e:
        print("❌ Render Error:")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/extract-text")
async def extract_text(
    pdf: UploadFile = File(...),
    x: float = Form(...),
    y: float = Form(...),
    width: float = Form(...),
    height: float = Form(...),
    page_num: int = Form(0)
):
    print(f"📥 Extraction Request: Page {page_num}, Region ({x},{y}) {width}x{height}")
    tmp_path = None
    doc = None
    try:
        # Save uploaded PDF to a temporary file
        contents = await pdf.read()
        print(f"📄 Read {len(contents)} bytes for extraction")
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(contents)
            tmp_path = tmp.name
            
        print(f"💾 Saved to temp file: {tmp_path}")
        doc = fitz.open(tmp_path)
        
        if page_num >= len(doc):
            doc.close()
            raise HTTPException(status_code=400, detail="Page number out of range")
            
        page = doc[page_num]
        
        # Define crop rectangle (PDF coordinates)
        rect = fitz.Rect(x, y, x + width, y + height)
        
        # Extract text directly from PDF for accuracy
        text_instances = page.get_text("words", clip=rect)
        std_text = " ".join([w[4] for w in text_instances])
        
        # Convert crop to image for OCR
        pix = page.get_pixmap(clip=rect, matrix=fitz.Matrix(3, 3)) # High res for OCR
        img_data = pix.tobytes("png")
        
        # Image Processing
        original_pil = Image.open(io.BytesIO(img_data)).convert('L')
        original_cv = np.array(original_pil)
        
        reader = get_ocr_reader()
        
        # Pass 1: Sharpened
        img_sharpened = original_pil.filter(ImageFilter.SHARPEN)
        res1 = reader.readtext(np.array(img_sharpened), allowlist='0123456789()[]-"\' .', detail=1)
        
        # Pass 2: Dilated (for thin bracket lines)
        img_inv = cv2.bitwise_not(original_cv)
        img_dilated = cv2.dilate(img_inv, np.ones((2,2), np.uint8), iterations=1)
        img_final = cv2.bitwise_not(img_dilated)
        res2 = reader.readtext(img_final, allowlist='0123456789()[]-"\' .', detail=1)
        
        # Merged OCR results collection
        all_ocr_results = []
        all_ocr_results.extend(res1)  # Sharpened
        all_ocr_results.extend(res2)  # Dilated
        
        # Rotation Helpers
        def map_bbox(bbox, rotation, w, h):
            new_bbox = []
            for [x, y] in bbox:
                if rotation == 90:
                    new_bbox.append([y, h - x])
                elif rotation == 270:
                    new_bbox.append([w - y, x])
                else:
                    new_bbox.append([x, y])
            return new_bbox

        h, w = original_cv.shape
        
        # Pass 3: Rotated (90 degrees)
        img_90 = cv2.rotate(img_final, cv2.ROTATE_90_CLOCKWISE)
        res_90 = reader.readtext(img_90, allowlist='0123456789()[]-"\' .', detail=1)
        all_ocr_results.extend([(map_bbox(b, 90, w, h), t, c) for (b, t, c) in res_90])

        # Pass 4: Rotated (270 degrees)
        img_270 = cv2.rotate(img_final, cv2.ROTATE_90_COUNTERCLOCKWISE)
        res_270 = reader.readtext(img_270, allowlist='0123456789()[]-"\' .', detail=1)
        all_ocr_results.extend([(map_bbox(b, 270, w, h), t, c) for (b, t, c) in res_270])
        
        extracted_texts = []
        seen_results = [] 
        
        for (bbox, text_val, conf) in all_ocr_results:
            clean_t = text_val.strip()
            if len(clean_t) < 1: continue
            
            norm_t = clean_t.replace('|', '(').replace('{', '(').replace('}', ')')
            norm_t = re.sub(r'\s+', '', norm_t)
            
            cx = sum(p[0] for p in bbox) / 4
            cy = sum(p[1] for p in bbox) / 4
            
            is_dupe = False
            for (s_text, s_cx, s_cy) in seen_results:
                if s_text == norm_t:
                    dist = ((cx - s_cx)**2 + (cy - s_cy)**2)**0.5
                    if dist < 20: 
                        is_dupe = True
                        break
            
            if not is_dupe:
                print(f"DEBUG - New OCR Result: '{norm_t}' at ({cx:.1f}, {cy:.1f})")
                seen_results.append((norm_t, cx, cy))
                extracted_texts.append(norm_t)

        combined_text = std_text + " " + "  ".join(extracted_texts) + " "
        combined_text = re.sub(r'\s+', ' ', combined_text) 
        print(f"DEBUG - Final Combined Text: {combined_text}")
        
        pattern_stud_label = r'([Ww]?\d+x\d+)\s*[\(\[\|]\s*(\d+)\s*[\)\]\|]'
        
        elevations = []
        pattern_elevation = r'[\[\(\{]\s*([^\]\)\}]*?[\d"\']+[^\]\)\}]*?)\s*[\]\)\}]'
        potential_elevations = re.findall(pattern_elevation, combined_text)
        for match in potential_elevations:
            clean_match = match.strip()
            if any(char.isdigit() for char in clean_match):
                elevations.append(clean_match)
        
        studs = []
        profiles = {} # Dictionary to store beam profiles: { "W12x19": [18, 29, 11] }

        # Find all stud labels: Beam(Count)
        matches = re.findall(pattern_stud_label, combined_text)
        total_studs = 0
        sum_bracketed_values = 0

        for beam, val in matches:
            v_int = int(val)
            print(f"✅ Match (Label): {beam}({v_int})")
            studs.append(v_int)
            total_studs += 1
            sum_bracketed_values += v_int
            
            # Store in profiles
            if beam not in profiles:
                profiles[beam] = []
            profiles[beam].append(v_int)
        
        # Fallback: if we found no labels but found brackets with numbers, maybe the beam label was far
        if not studs:
            pattern_isolated_brackets = r'[\(\[\|]\s*(\d+)\s*[\)\]\|]'
            potential_studs = re.findall(pattern_isolated_brackets, combined_text)
            for val in potential_studs:
                v_int = int(val)
                if val.isdigit() and v_int < 100: 
                    print(f"✅ Match (Isolated): ({v_int})")
                    studs.append(v_int)
                    sum_bracketed_values += v_int
                    total_studs += 1
                else:
                    print(f"⚠️ Reject (Isolated Too Large/Non-Digit): ({val})")

        return {
            "success": True,
            "elevations": list(set(elevations)),
            "studs": studs,
            "profiles": profiles,
            "studs_total": sum_bracketed_values,
            "studs_count": total_studs,
            "raw_text": combined_text
        }

    except Exception as e:
        print("❌ Extraction Error:")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if doc:
            try:
                doc.close()
            except:
                pass
        
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
                print(f"🧹 Removed temp file: {tmp_path}")
            except Exception as cleanup_err:
                print(f"⚠️ Cleanup failed: {cleanup_err}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5001)

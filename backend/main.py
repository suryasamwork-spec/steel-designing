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
        # High DPI: Scale 6.0 ~ 432 DPI (Extra detail for distinguishing similar numbers)
        pix = page.get_pixmap(clip=rect, matrix=fitz.Matrix(6, 6)) 
        img_data = pix.tobytes("png")
        
        # Image Processing
        original_pil = Image.open(io.BytesIO(img_data)).convert('L') # Grayscale
        original_cv = np.array(original_pil)
        
        # 1. Sharpening Filter (helps define edges for digits like 2, 3, 5, 6)
        kernel_sharpen = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]])
        img_sharpened = cv2.filter2D(original_cv, -1, kernel_sharpen)
        
        # 2. Adaptive Thresholding (use sharpened image)
        # Block Size: 21 (Larger block for smoother background), C: 4
        img_adaptive = cv2.adaptiveThreshold(
            img_sharpened, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 21, 4
        )
        
        # Debug: Save processed image if needed (uncomment for local debug)
        # cv2.imwrite("debug_ocr_input.png", img_adaptive)

        reader = get_ocr_reader()
        
        # Pass 1: Sharpened Grayscale (Clean native look)
        allowlist_chars = '0123456789()[]{}-"\' .kKlIOoSsZzBWwxX|'
        res1 = reader.readtext(img_sharpened, allowlist=allowlist_chars, detail=1)
        all_ocr_results = list(res1)
        
        # Pass 2: Adaptive Threshold (Binarized look)
        res2 = reader.readtext(img_adaptive, allowlist=allowlist_chars, detail=1)
        all_ocr_results.extend(res2)
        
        # Pass 3: Light Dilation (Helps with thin/faint lines) 
        img_inv = cv2.bitwise_not(img_adaptive)
        img_dilated = cv2.dilate(img_inv, np.ones((2,2), np.uint8), iterations=1)
        img_final = cv2.bitwise_not(img_dilated)
        res3 = reader.readtext(img_final, allowlist=allowlist_chars, detail=1)
        all_ocr_results.extend(res3)

        # Pass 3 & 4: Rotated (Helps with vertical text)
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
        
        img_90 = cv2.rotate(img_final, cv2.ROTATE_90_CLOCKWISE)
        res_90 = reader.readtext(img_90, allowlist=allowlist_chars, detail=1)
        all_ocr_results.extend([(map_bbox(b, 90, w, h), t, c) for (b, t, c) in res_90])

        img_270 = cv2.rotate(img_final, cv2.ROTATE_90_COUNTERCLOCKWISE)
        res_270 = reader.readtext(img_270, allowlist=allowlist_chars, detail=1)
        all_ocr_results.extend([(map_bbox(b, 270, w, h), t, c) for (b, t, c) in res_270])
        
        extracted_texts = []
        seen_results = [] 
        
        # Typo Correction Map
        char_map = {
            'k': '1', 'K': '1', 'l': '1', 'I': '1', '|': '1',
            'O': '0', 'o': '0', 'D': '0', 'Q': '0',
            'S': '5', 's': '5',
            'Z': '2', 'z': '2',
            'B': '8',
            '{': '(', '}': ')', 
            # STRICT CHANGE: Unmap [] so they are NOT converted to ()
            # '[': '(', ']': ')' 
        }
        
        for (bbox, text_val, conf) in all_ocr_results:
            clean_t = text_val.strip()
            if len(clean_t) < 1: continue
            
            # 1. Apply Character Mapping
            norm_t = ""
            for char in clean_t:
                norm_t += char_map.get(char, char)
            
            # 2. Normalize Spacing (remove all spaces for de-duplication)
            # We will use a spaced version for the final string though
            dedupe_key = re.sub(r'\s+', '', norm_t)
            
            cx = sum(p[0] for p in bbox) / 4
            cy = sum(p[1] for p in bbox) / 4
            
            is_dupe = False
            for (s_key, s_cx, s_cy) in seen_results:
                if s_key == dedupe_key:
                    dist = ((cx - s_cx)**2 + (cy - s_cy)**2)**0.5
                    if dist < 20: 
                        is_dupe = True
                        break
            
            if not is_dupe:
                print(f"DEBUG - New OCR Result: '{clean_t}' -> '{norm_t}' at ({cx:.1f}, {cy:.1f})")
                seen_results.append((dedupe_key, cx, cy))
                extracted_texts.append(norm_t)

        # ---------------------------------------------------------
        # SPATIAL EXTRACTION LOGIC (Per User Request)
        # ---------------------------------------------------------
        
        # Regexes
        regex_beam = re.compile(r'([Ww]\d+[xX]\d+)', re.IGNORECASE)
        regex_bracket = re.compile(r'\[\s*(\d+)\s*\]') # Strict Square Brackets

        beams = []
        candidates = []

        for (bbox, text_val, conf) in all_ocr_results:
            clean_t = text_val.strip()
            
            # fix common typos in clean_t before regex
            # e.g. 'W12x14' often read as 'W12x14' (correct) but sometimes 'W12x1A'
            # For now, rely on strict regex, but normalize spaces
            clean_t_nospace = re.sub(r'\s+', '', clean_t)
            
            # Check for Beam Label
            beam_match = regex_beam.search(clean_t_nospace)
            if beam_match:
                # Calculate Centroid
                cx = sum(p[0] for p in bbox) / 4
                cy = sum(p[1] for p in bbox) / 4
                label = beam_match.group(1).upper()
                beams.append({'label': label, 'cx': cx, 'cy': cy, 'bbox': bbox})
                continue # Don't double count as a candidate

            # Check for Square Bracket Value
            # We use the spaced 'clean_t' here to allow '[ 12 ]'
            # Also apply char map to fix 'l' -> '1', 'O' -> '0' inside brackets?
            # Let's do a local cleanup for candidate check
            mapped_t = ""
            for char in clean_t:
                mapped_t += char_map.get(char, char)
            
            brack_match = regex_bracket.search(mapped_t)
            if brack_match:
                val = int(brack_match.group(1))
                if 6 <= val <= 60: # Strict Range
                    cx = sum(p[0] for p in bbox) / 4
                    cy = sum(p[1] for p in bbox) / 4
                    candidates.append({'val': val, 'cx': cx, 'cy': cy})

        # Linking Phase
        # For each candidate, find the NEAREST beam label.
        # Threshold: How far can a label be? 
        # At 6.0 scale, text is large. Let's say ~300-400px is reasonable for "associated"
        # but sometimes it's far. Let's try 1500px diagonal max (generous but keeps locality).
        
        MAX_DIST = 1500 
        
        studs = []
        profiles = {}
        total_studs = 0
        sum_bracketed_values = 0

        for cand in candidates:
            best_beam = None
            min_dist = float('inf')
            
            for beam in beams:
                dist = ((cand['cx'] - beam['cx'])**2 + (cand['cy'] - beam['cy'])**2)**0.5
                if dist < min_dist:
                    min_dist = dist
                    best_beam = beam
            
            if best_beam and min_dist <= MAX_DIST:
                # Associated!
                b_label = best_beam['label']
                val = cand['val']
                
                print(f"✅ Linked [{val}] to {b_label} (dist: {min_dist:.1f})")
                
                studs.append(val)
                total_studs += 1
                sum_bracketed_values += val
                
                if b_label not in profiles:
                    profiles[b_label] = []
                profiles[b_label].append(val)
            else:
                print(f"⚠️ Ignored Isolated [{cand['val']}] - Nearest Beam dist: {min_dist:.1f}")

        print(f"DEBUG - Final Spatial Profiles: {profiles.keys()}")
        
        return {
            "success": True,
            "elevations": list(set(elevations)), # (Legacy, mostly empty now)
            "studs": studs,
            "profiles": profiles,
            "studs_total": sum_bracketed_values,
            "studs_count": total_studs,
            "raw_text": "" # No longer relevant in spatial mode
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

import os
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import LETTER  
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.platypus import BaseDocTemplate, Frame, PageTemplate, Paragraph
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph
import xml.sax.saxutils as saxutils
import boto3
            
from .excel_generator import generate_excel  # relative import
    
# === COLOR PALETTE ===
bg_color = colors.HexColor("#FEFDF9") 
text_color = colors.HexColor("#3D4335")
        
# === STYLES ===
styles = getSampleStyleSheet()
body_style = ParagraphStyle(
    name="Body",
    parent=styles["BodyText"],
    fontName="Helvetica",
    fontSize=12,
    leading=16,
    textColor=text_color,
    allowWidows=1,
    allowOrphans=1,
)
just_style = ParagraphStyle(
    name="Justification", parent=body_style, fontSize=10, leading=14
)
            
def generate_pdf(logo_path, client_name, claim_text, estimate_data):
    out_dir = "app/finalized_pdfs"
    os.makedirs(out_dir, exist_ok=True)
    pdf_path = os.path.join(out_dir, f"{client_name.replace(' ','_')}_Claim.pdf")
        
    c = canvas.Canvas(pdf_path, pagesize=LETTER)
    width, height = LETTER
        
    # Layout constants
    cat_x = inch
    cat_w = 1.5 * inch
    desc_x = cat_x + cat_w + 0.2 * inch
    desc_w = 1.8 * inch
    just_x = desc_x + desc_w + 0.2 * inch
    just_w = 1.8 * inch
    bottom_margin = inch
    total_x = width - inch           # ← add this
    
    def start_claim_page():
        c.setFillColor(bg_color)
        c.rect(0, 0, width, height, fill=1, stroke=0)
        c.setFillColor(text_color)
        try:
            img = ImageReader(logo_path)
            c.drawImage(
                img,
                0.5*inch, height - 1.4*inch,
                width=3.2*inch, height=1.2*inch,
                preserveAspectRatio=True
            )
        except:
            pass
        c.setFont("Helvetica-Bold", 20)
        c.drawCentredString(width/2, height - 2.5*inch, "Claim Package")
    
    def start_contents_page(include_title: bool):
        c.setFillColor(bg_color)
        c.rect(0, 0, width, height, fill=1, stroke=0)
        c.setFillColor(text_color)
        try:
            img = ImageReader(logo_path)
            c.drawImage(
                img,
                0.5*inch, height - 1.4*inch,
                width=3.2*inch, height=1.2*inch,
                preserveAspectRatio=True
            )
        except:
            pass
        if include_title:
            c.setFont("Helvetica-Bold", 20)
            c.drawCentredString(width/2, height - 1.9*inch, "Contents Estimate")

    def _platypus_start_claim_page(canvas, doc):
        # adapter for Platypus: call your existing zero-arg header function
        start_claim_page()
    
    def draw_table_headers(y_pos):
        c.setFont("Helvetica-Bold", 12)
        c.drawString(cat_x, y_pos, "Category")
        c.drawString(desc_x, y_pos, "Description")
        c.drawString(just_x, y_pos, "Justification")
        c.drawRightString(width - inch, y_pos, "Total")
        y2 = y_pos - 0.3*inch
        c.line(cat_x, y2, width - inch + 0.1*inch, y2)
        return y2 - 0.2*inch
    

    # === PAGE 1+: Claim Package (with pagination) ===
    # 1) Escape & wrap the entire claim_text into a Paragraph
    esc = saxutils.escape(claim_text or "")
    esc = (
        esc.replace('\t', '&nbsp;'*4)
           .replace('\r\n', '\n')
           .replace('\n', '<br/>')
    )
    para = Paragraph(esc, body_style)

    # 2) Set up your margins & compute the body area
    left_margin   = inch
    right_margin  = inch
    top_margin    = 3 * inch
    bottom_margin = inch

    y_top       = height - top_margin
    body_width  = width  - left_margin - right_margin
    body_height = y_top   - bottom_margin

    # 3) Split the Paragraph into page-sized chunks
    chunks = para.split(body_width, body_height)

    # 4) Draw each chunk, paginating when necessary
    start_claim_page()      # draw header/logo on the very first page
    y_cursor = y_top
    for idx, chunk in enumerate(chunks):
        if idx > 0:
            c.showPage()
            start_claim_page()      # redraw header/logo on new page
            y_cursor = y_top

        w, h = chunk.wrap(body_width, body_height)
        chunk.drawOn(c, left_margin, y_cursor - h)
        y_cursor -= h
    
    # === PAGE 2+: Contents Estimate ===
    start_contents_page(True)
        
    # Metadata
    y = height - 2.5*inch
    for label in ["claimant","property","estimator","estimate_type","date_entered","date_completed"]:
        text = f"{label.replace('_',' ').title()}: "
        val  = estimate_data.get(label, "")
        c.setFont("Helvetica-Bold", 12)
        c.drawString(inch, y, text)
        lw = c.stringWidth(text, "Helvetica-Bold", 12)
        c.setFont("Helvetica", 12)
        c.drawString(inch + lw, y, val)
        y -= 0.3*inch
        
    # Grand total centered
    y -= 0.3*inch
    total_sum = sum(r.get("total", 0) for r in estimate_data.get("rows", []))
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(width/2, y, f"Total Replacement Cost Value: ${total_sum:,.2f}")
    y -= 0.6*inch
        
    # Table headers
    y = draw_table_headers(y)
        
    # Rows
    for row in estimate_data.get("rows", []):
        avail_h = y - bottom_margin

        # ——— pagination check ———
        # wrap each cell so we know how tall this row wants to be
        tmp_cat = Paragraph(row.get("category","—"), just_style)
        w_cat, h_cat = tmp_cat.wrap(cat_w, avail_h)

        tmp_desc = Paragraph(saxutils.escape(row.get("description","—")), just_style)
        w_desc, h_desc = tmp_desc.wrap(desc_w, avail_h)

        raw_j = row.get("justification","—")
        esc_j = saxutils.escape(raw_j).replace('\t','&nbsp;'*4).replace('\r\n','\n').replace('\n','<br/>')
        tmp_just = Paragraph(esc_j, just_style)
        w_just, h_just = tmp_just.wrap(just_w, avail_h)

        row_h = max(h_cat, h_desc, h_just, 14)
        if y - row_h < bottom_margin:
            # new page
            c.showPage()
            start_contents_page(False)
            y = height - 1.9*inch
            y = draw_table_headers(y)
            avail_h = y - bottom_margin
        # ——— end pagination check ———
        
        # Category
        cat_para = Paragraph(row.get("category", "—"), just_style)
        w_cat, h_cat = cat_para.wrap(cat_w, avail_h)
        cat_para.drawOn(c, cat_x + (cat_w - w_cat)/2, y - h_cat)
    
        # Description 
        desc_para = Paragraph(saxutils.escape(row.get("description", "—")), just_style)
        w_desc, h_desc = desc_para.wrap(desc_w, avail_h)
        desc_para.drawOn(c, desc_x + (desc_w - w_desc)/2, y - h_desc)
    
        # Justification
        raw_j = row.get("justification", "—")
        esc_j = saxutils.escape(raw_j).replace('\t','&nbsp;'*4).replace('\r\n','\n').replace('\n','<br/>')
        just_para = Paragraph(esc_j, just_style)
        w_just, h_just = just_para.wrap(just_w, avail_h)
        just_para.drawOn(c, just_x + (just_w - w_just)/2, y - h_just)
    
        # Total (right-aligned)
        row_h = max(h_cat, h_desc, h_just, 14)
        c.setFont("Helvetica", 10)
        c.drawRightString(
            width - inch,
            y - (row_h/2) + 4,
            f"${row.get('total', 0):,.2f}"
        )
        
        y -= (row_h + 6)
    
    c.save()
        
    # Upload PDF to S3...
    s3 = boto3.client(
        "s3",
        region_name=os.getenv("S3_REGION"),
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    )
    key = f"finalized/{os.path.basename(pdf_path)}"
    s3.upload_file(pdf_path, os.getenv("S3_BUCKET_NAME"), key, ExtraArgs={"ACL":"public-read"})
    pdf_url = f"https://{os.getenv('S3_BUCKET_NAME')}.s3.{os.getenv('S3_REGION')}.amazonaws.com/{key}"
        
    # Generate & upload Excel
    excel_url = generate_excel(pdf_path, logo_path, claim_text, estimate_data, client_name)
    return pdf_url, excel_url


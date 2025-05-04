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
    allowSplitting=True,    # ← add this
    allowWidows=1,
    allowOrphans=1,
)
just_style = ParagraphStyle(
    name="Justification", parent=body_style, fontSize=10, leading=14
)
            
def generate_pdf(logo_path, client_name, claim_text, estimate_data):

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

    # 1) Prepare output directory and file path
    out_dir = "app/finalized_pdfs"
    os.makedirs(out_dir, exist_ok=True)
    pdf_path = os.path.join(out_dir, f"{client_name.replace(' ', '_')}_Claim.pdf")

    # 2) Create canvas
    c = canvas.Canvas(pdf_path, pagesize=LETTER)
    width, height = LETTER

    # Helper: draw Claim Package header/logo
    def start_claim_page():
        c.setFillColor(bg_color)
        c.rect(0, 0, width, height, fill=1, stroke=0)
        c.setFillColor(text_color)
        try:
            img = ImageReader(logo_path)
            c.drawImage(
                img,
                0.5 * inch,
                height - 1.4 * inch,
                width=3.2 * inch,
                height=1.2 * inch,
                preserveAspectRatio=True
            )
        except Exception:
            pass
        c.setFont("Helvetica-Bold", 20)
        c.drawCentredString(width / 2, height - 2.5 * inch, "Claim Package")

    # 3) Manual pagination for Claim Package text
    esc = saxutils.escape(claim_text or "")
    esc = esc.replace('\t', '&nbsp;'*4).replace('\r\n', '\n').replace('\n', '<br/>')
    para = Paragraph(esc, body_style)

    left_margin = inch
    right_margin = inch
    top_margin = 3 * inch
    bottom_margin = inch

    y_start = height - top_margin
    body_width = width - left_margin - right_margin
    body_height = y_start - bottom_margin

    chunks = para.split(body_width, body_height)

    start_claim_page()
    y = y_start
    for chunk in chunks:
        w, h = chunk.wrap(body_width, body_height)
        if y - h < bottom_margin:
            c.showPage()
            start_claim_page()
            y = y_start
        chunk.drawOn(c, left_margin, y - h)
        y -= h

    # 4) Contents Estimate section
    # Draw contents page(s) as before
    start_contents_page(True)
    y = height - 2.5 * inch
    for label in ["claimant", "property", "estimator", "estimate_type", "date_entered", "date_completed"]:
        text = f"{label.replace('_',' ').title()}: "
        val = estimate_data.get(label, "")
        c.setFont("Helvetica-Bold", 12)
        c.drawString(inch, y, text)
        lw = c.stringWidth(text, "Helvetica-Bold", 12)
        c.setFont("Helvetica", 12)
        c.drawString(inch + lw, y, val)
        y -= 0.3 * inch

    y -= 0.3 * inch
    total_sum = sum(r.get("total", 0) for r in estimate_data.get("rows", []))
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(width/2, y, f"Total Replacement Cost Value: ${total_sum:,.2f}")
    y -= 0.6 * inch

    y = draw_table_headers(y)
    for row in estimate_data.get("rows", []):
        avail_h = y - bottom_margin
        tmp_cat = Paragraph(row.get("category","—"), just_style)
        w_cat, h_cat = tmp_cat.wrap(cat_w, avail_h)
        tmp_desc = Paragraph(saxutils.escape(row.get("description","—")), just_style)
        w_desc, h_desc = tmp_desc.wrap(desc_w, avail_h)
        esc_j = saxutils.escape(row.get("justification","—")).replace('\t','&nbsp;'*4).replace('\r\n','\n').replace('\n','<br/>')
        tmp_just = Paragraph(esc_j, just_style)
        w_just, h_just = tmp_just.wrap(just_w, avail_h)
        row_h = max(h_cat, h_desc, h_just, 14)
        if y - row_h < bottom_margin:
            c.showPage()
            start_contents_page(False)
            y = height - 1.9 * inch
            y = draw_table_headers(y)
            avail_h = y - bottom_margin
        cat_para = Paragraph(row.get("category","—"), just_style)
        w_cat, h_cat = cat_para.wrap(cat_w, avail_h)
        cat_para.drawOn(c, cat_x + (cat_w - w_cat)/2, y - h_cat)
        desc_para = Paragraph(saxutils.escape(row.get("description","—")), just_style)
        w_desc, h_desc = desc_para.wrap(desc_w, avail_h)
        desc_para.drawOn(c, desc_x + (desc_w - w_desc)/2, y - h_desc)
        just_para = Paragraph(esc_j, just_style)
        w_just, h_just = just_para.wrap(just_w, avail_h)
        just_para.drawOn(c, just_x + (just_w - w_just)/2, y - h_just)
        c.setFont("Helvetica", 10)
        c.drawRightString(width - inch, y - (row_h/2) + 4, f"${row.get('total', 0):,.2f}")
        y -= (row_h + 6)

    # === PAGE 1 Pageless Claim Package ===
    # 1) Escape & wrap the entire claim_text into a Paragraph
    esc = saxutils.escape(claim_text or "")
    esc = (
        esc.replace('\t', '&nbsp;'*4)
           .replace('\r\n', '\n')
           .replace('\n', '<br/>')
    )
    para = Paragraph(esc, body_style)

    # 2) Compute margins & full paragraph height
    left_margin   = inch
    right_margin  = inch
    top_margin    = 3 * inch
    bottom_margin = inch

    body_width = width - left_margin - right_margin
    # pretend we have infinite vertical room
    _, full_text_height = para.wrap(body_width, 1e6)

    # total page height = header + text + footer
    page_height = top_margin + full_text_height + bottom_margin

    # 3) Recreate your Canvas with that custom height
    c = canvas.Canvas(pdf_path, pagesize=(width, page_height))
    # override height so your header draws correctly
    height = page_height

    # 4) Draw header/logo once at the top
    start_claim_page()

    # 5) Draw the paragraph in one go
    #    y = page_height - top_margin - full_text_height
    para.drawOn(
        c,
        left_margin,
        height - top_margin - full_text_height
    )
    
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


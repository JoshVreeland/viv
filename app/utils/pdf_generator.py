import os
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import LETTER  
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.platypus import BaseDocTemplate, Frame, PageTemplate, Paragraph
from reportlab.platypus import Paragraph
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.utils import simpleSplit
from reportlab.platypus import XPreformatted
from xml.sax import saxutils
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
    allowSplitting=True,    # still allow paragraph → next page splits
    splitLongWords=False,   # ← do NOT break words in half
    allowWidows=1,
    allowOrphans=1,
    wordWrap='LTR',         # wrap at spaces, not mid-word
)

just_style = ParagraphStyle(
    name="Justification", parent=body_style, fontSize=12, leading=14
)

estimate_body_style = ParagraphStyle(
    name="EstimateBody",
    parent=body_style,
    fontSize=body_style.fontSize - 2,   # 12 → 10
    leading=body_style.leading - 2,     # 16 → 14
)
estimate_just_style = ParagraphStyle(
    name="EstimateJust",
    parent=just_style,
    fontSize=just_style.fontSize - 2,   # 10 → 8
    leading=just_style.leading - 2,     # 14 → 12
)

def generate_pdf(logo_path, client_name, claim_text, estimate_data):
            
    # 1) Prepare output path
    out_dir = "app/finalized_pdfs"
    os.makedirs(out_dir, exist_ok=True)
    pdf_path = os.path.join(out_dir, f"{client_name.replace(' ', '_')}_Claim.pdf")

    # 2) Create Canvas
    c = canvas.Canvas(pdf_path, pagesize=LETTER)
    width, height = LETTER

    # 3) Layout constants
    left_margin   = inch
    right_margin  = inch
    top_margin    = 3 * inch
    bottom_margin = inch

    # table columns (for Contents Estimate)
    cat_x, cat_w   = left_margin,           1.5 * inch
    desc_x, desc_w = cat_x + cat_w + 0.2*inch, 1.8 * inch
    just_x, just_w = desc_x + desc_w + 0.2*inch, 1.8 * inch

    # 4) Helper functions
    def start_claim_page():
        c.setFillColor(colors.HexColor("#FEFDF9"))
        c.rect(0, 0, width, height, fill=1, stroke=0)
        c.setFillColor(colors.HexColor("#3D4335"))
        try:
            img = ImageReader(logo_path)
            c.drawImage(img, 0.5*inch, height - 1.4*inch,
                        width=3.2*inch, height=1.2*inch,
                        preserveAspectRatio=True)
        except:
            pass
        c.setFont("Helvetica-Bold", 20)
        c.drawCentredString(width/2, height - 1.9*inch, "Claim Package")

    def start_contents_page(include_title: bool):
        c.setFillColor(colors.HexColor("#FEFDF9"))
        c.rect(0, 0, width, height, fill=1, stroke=0)
        c.setFillColor(colors.HexColor("#3D4335"))
        try:
            img = ImageReader(logo_path)
            c.drawImage(img, 0.5*inch, height - 1.4*inch,
                        width=3.2*inch, height=1.2*inch,
                        preserveAspectRatio=True)
        except:
            pass
        if include_title:
            c.setFont("Helvetica-Bold", 20)
            c.drawCentredString(width/2, height - 1.9*inch, "Contents Estimate")

    def draw_table_headers(y_pos):
        c.setFont("Helvetica-Bold", 12)
        c.drawString(cat_x,   y_pos, "Category")
        c.drawString(desc_x,  y_pos, "Description")
        c.drawString(just_x,  y_pos, "Justification")
        c.drawRightString(width - right_margin, y_pos, "Total")
        y2 = y_pos - 0.3*inch
        c.line(cat_x, y2, width - right_margin + 0.1*inch, y2)
        return y2 - 0.2*inch

    # 5) Claim Package pagination

    claim_text = (claim_text or "").expandtabs(4)

    # ——— Claim Package via XPreformatted ———

    claim_text = (claim_text or "").expandtabs(4)
    pref       = XPreformatted(claim_text, body_style)
    avail_h    = y - bottom_margin
    w, h       = pref.wrap(avail_w, avail_h)
    if h > avail_h:
        c.showPage()
        start_claim_page()
        y        = y_start
        avail_h  = y - bottom_margin
        w, h     = pref.wrap(avail_w, avail_h)
    pref.drawOn(c, left_margin, y - h)
    y -= h

    # ——— end Claim Package ———

    # style for the per-row total cell
    estimate_total_style = ParagraphStyle(
        name='EstimateTotal',
        fontName='Helvetica',
        fontSize=12,
        leading=14,
        alignment=TA_RIGHT
    )

    # ── table + pagination ──
    y = draw_table_headers(y)

    cat_x   = left_margin
    desc_x  = cat_x    + cat_w  + 0.2 * inch
    just_x  = desc_x   + desc_w + 0.2 * inch
    total_x = just_x   + just_w + 0.2 * inch
    total_w = width    - right_margin - total_x

    for row in estimate_data.get("rows", []):
        tmp_cat  = Paragraph(row.get("category", "—"), estimate_body_style)
        tmp_desc = Paragraph(
            saxutils.escape(row.get("description", "—")),
            estimate_body_style
        )
        esc_j = (
            saxutils.escape(row.get("justification", "—"))
            .replace('\t', '&nbsp;' * 4)
            .replace('\r\n', '\n')
            .replace('\n', '<br/>')
        )
        tmp_just = Paragraph(esc_j, estimate_just_style)
        tmp_tot  = Paragraph(f"${row.get('total', 0):,.2f}", estimate_total_style)

        w_cat,  h_cat  = tmp_cat.wrap(cat_w,   y - bottom_margin)
        w_desc, h_desc = tmp_desc.wrap(desc_w, y - bottom_margin)
        w_just, h_just = tmp_just.wrap(just_w, y - bottom_margin)
        w_tot,  h_tot  = tmp_tot.wrap(total_w, y - bottom_margin)

        row_h = max(h_cat, h_desc, h_just, h_tot)

        if y - row_h < bottom_margin:
            c.showPage()
            start_contents_page(False)
            y = height - 1.9 * inch
            y = draw_table_headers(y)

        tmp_cat.drawOn(c,   cat_x,   y - h_cat)
        tmp_desc.drawOn(c,  desc_x,  y - h_desc)
        tmp_just.drawOn(c,  just_x,  y - h_just)
        tmp_tot.drawOn(c,   total_x, y - h_tot)

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


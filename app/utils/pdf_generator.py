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
from reportlab.platypus import Preformatted
import xml.sax.saxutils as saxutils
import boto3
from .excel_generator import generate_excel  # relative import
from html import unescape
import re

# === sanitize_claim_text ====================================================
def sanitize_claim_text(html: str) -> str:
    """
    Convert simple Quill/HTML lists into bullets+newlines, strip tags,
    unescape entities, collapse excess blank lines.
    """
    if not html:
        return ""
    # 1) <li>…</li> → “• content\n”
    html = re.sub(
        r'<li[^>]*>(.*?)</li>',
        lambda m: "• " + unescape(m.group(1).strip()) + "\n",
        html,
        flags=re.S | re.I
    )
    # 2) <br> or </p> → newline
    html = re.sub(r'<br\s*/?>', '\n', html, flags=re.I)
    html = re.sub(r'</p\s*>', '\n', html, flags=re.I)
    # 3) strip any other tags
    html = re.sub(r'<[^>]+>', '', html)
    # 4) unescape entities
    text = unescape(html)
    # 5) collapse 3+ newlines to just 2
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()
    
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
    textColor=colors.HexColor("#3D4335"),
    allowSplitting=True,
    splitLongWords=False,
    allowWidows=1,
    allowOrphans=1,
    wordWrap="LTR"
)

just_style = ParagraphStyle(
    name='Justification',
    parent=body_style,
    fontSize=10,
    leading=14,
    splitLongWords=True,
    wordWrap='CJK'
)

desc_style = ParagraphStyle(
    name="Description",
    parent=body_style,
    fontSize=10,
    leading=14,
    splitLongWords=True,
    wordWrap="CJK"
)

estimate_body_style = ParagraphStyle(
    name="EstimateBody",
    parent=body_style,
    fontSize=10,
    leading=14
)

estimate_just_style = ParagraphStyle(
    name="EstimateJust",
    parent=just_style,
    fontSize=8,
    leading=12
)

estimate_total_style = ParagraphStyle(
    name="EstimateTotal",
    parent=body_style,
    fontName="Helvetica",
    fontSize=12,
    leading=14,
    alignment=TA_RIGHT
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
    left_margin = inch
    right_margin = inch
    bottom_margin = inch


    # Define column widths for each section
    cat_x, cat_w = left_margin, 1.5 * inch           # Category column, width 1.5 inches
    desc_x, desc_w = cat_x + cat_w + 0.2 * inch, 2.0 * inch  # Description column, width 2.5 inches
    just_x, just_w = desc_x + desc_w + 0.2 * inch, 1.5 * inch  # Justification column, width 2.5 inches
    total_x = width - right_margin  # Total column, right-aligned

    # Helper functions
    def start_claim_page():
        c.setFillColor(colors.HexColor("#FEFDF9"))
        c.rect(0, 0, width, height, fill=1, stroke=0)
        c.setFillColor(colors.HexColor("#3D4335"))
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
        except:
            pass
        c.setFont("Helvetica-Bold", 20)
        c.drawCentredString(width / 2, height - 1.9 * inch, "Claim Package")

    def start_contents_page(include_title: bool):
        c.setFillColor(colors.HexColor("#FEFDF9"))
        c.rect(0, 0, width, height, fill=1, stroke=0)
        c.setFillColor(colors.HexColor("#3D4335"))
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
        except:
            pass
        if include_title:
            c.setFont("Helvetica-Bold", 20)
            c.drawCentredString(width / 2, height - 1.9 * inch, "Contents Estimate")

    def draw_table_headers(y_pos):
        c.setFont("Helvetica-Bold", 12)
        # Left-aligned headers for Category, Description, and Justification
        c.drawString(cat_x, y_pos, "Category")
        c.drawString(desc_x, y_pos, "Description")
        c.drawString(just_x, y_pos, "Justification")
        # Right-aligned Total
        c.drawRightString(total_x, y_pos, "Total")
    
        # Draw a line under the headers
        y2 = y_pos - 0.3 * inch
        c.line(cat_x, y2, total_x + 0.1 * inch, y2)
        return y2 - 0.2 * inch

    # === Claim Package ===
    title_y = height - 1.9 * inch
    y_start = title_y - 0.5 * inch
    avail_w = width - left_margin - right_margin
    y = y_start

    # Draw first page header/logo/title
    start_claim_page()

    # ─── Claim Package (with proper wrapping + pagination) ───

    # prepare and clean text
    cleaned = sanitize_claim_text(claim_text or "")
    # Preformatted preserves spaces, tabs, newlines
    pre_style = ParagraphStyle(
        name="PreFormattedBody",
        parent=body_style,
        splitLongWords=False,
        allowSplitting=True,
        wordWrap="LTR"
    )
    pref = Preformatted(cleaned, pre_style)

    # split into page-sized chunks
    chunks = pref.split(avail_w, avail_h)
    y = y_start
    for i, chunk in enumerate(chunks):
        if i > 0:
            c.showPage()
            start_claim_page()
            y = y_start
        w, h = chunk.wrap(avail_w, avail_h)
        chunk.drawOn(c, left_margin, y - h)
        y -= h

    # ─── PAGE 2+: Contents Estimate ───
    c.showPage()
    start_contents_page(True)

    # metadata lines
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

    # grand total
    y -= 0.3*inch
    total_sum = sum(r.get("total",0) for r in estimate_data.get("rows",[]))
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(width/2, y, f"Total Replacement Cost Value: ${total_sum:,.2f}")
    y -= 0.6*inch

    # ── four-column layout & pagination ──
    cat_x,  cat_w  = inch,                    1.5 * inch
    desc_x, desc_w = cat_x + cat_w + 0.2*inch, 2.0 * inch
    just_x, just_w = desc_x + desc_w + 0.2*inch, 1.5 * inch
    total_x        = width - inch

    # draw headers
    y = draw_table_headers(y)

    # ── Rows with wrap + pagination in one pass ──
    for row in estimate_data.get("rows", []):
        avail_h = y - bottom_margin

        # build and wrap each Paragraph
        cat_para  = Paragraph(row.get("category", "—"), just_style)
        w_cat, h_cat = cat_para.wrap(cat_w, avail_h)

        desc_para = Paragraph(
            saxutils.escape(row.get("description", "—")),
            just_style
        )
        w_desc, h_desc = desc_para.wrap(desc_w, avail_h)

        raw_j = row.get("justification", "—")
        esc_j = (
            saxutils.escape(raw_j)
            .replace('\t', '&nbsp;'*4)
            .replace('\r\n','\n')
            .replace('\n','<br/>')
        )
        just_para = Paragraph(esc_j, just_style)
        w_just, h_just = just_para.wrap(just_w, avail_h)

        row_h = max(h_cat, h_desc, h_just, 14)

        # pagination break
        if y - row_h < bottom_margin:
            c.showPage()
            start_contents_page(False)
            y = height - 1.9*inch
            y = draw_table_headers(y)
            avail_h = y - bottom_margin

            # re-wrap now that widths/avail_h are same
            w_cat, h_cat = cat_para.wrap(cat_w, avail_h)
            w_desc, h_desc = desc_para.wrap(desc_w, avail_h)
            w_just, h_just = just_para.wrap(just_w, avail_h)
            row_h = max(h_cat, h_desc, h_just, 14)

        # draw each cell, centered horizontally in its column
        cat_para.drawOn(
            c,
            cat_x + (cat_w - w_cat) / 2,
            y - h_cat
        )
        desc_para.drawOn(
            c,
            desc_x + (desc_w - w_desc) / 2,
            y - h_desc
        )
        just_para.drawOn(
            c,
            just_x + (just_w - w_just) / 2,
            y - h_just
        )

        # total, right-aligned
        c.setFont("Helvetica", 10)
        c.drawRightString(
            total_x,
            y - (row_h / 2) + 4,
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


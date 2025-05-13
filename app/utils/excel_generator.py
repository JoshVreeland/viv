from PIL import Image
import os
import xlsxwriter
import boto3
from openpyxl.styles import Border, Side, Alignment
import re
from html import unescape


def sanitize_claim_text(html: str) -> str:
    """
    Strip out any HTML tags from Quill output and turn <li>…</li> into bullets + newlines.
    """
    # Convert closing </li> into newline
    text = re.sub(r'</li\s*>', '\n', html or '', flags=re.IGNORECASE)
    # Convert opening <li…> into bullet + space
    text = re.sub(r'<li[^>]*>', '• ', text, flags=re.IGNORECASE)
    # Strip all other tags
    text = re.sub(r'<[^>]+>', '', text)
    return text

def generate_excel(pdf_path: str,
                   logo_path: str,
                   claim_text: str,
                   estimate_data: dict,
                   client_name: str) -> str:
    # ———————————————————————————————
    # Guard against tuple/list
    if isinstance(pdf_path, (tuple, list)):
        pdf_path = pdf_path[0]
    # ———————————————————————————————
    out_dir = os.path.dirname(pdf_path)
    os.makedirs(out_dir, exist_ok=True)

    safe = client_name.replace(" ", "_")
    excel_path = os.path.join(out_dir, f"{safe}_Claim.xlsx")

    wb = xlsxwriter.Workbook(excel_path)

    # === COMMON FORMATS ===
    common_fmt = lambda **kw: wb.add_format({
        'font_name': 'Arial',
        'align': 'center',
        'valign': 'vcenter',
        'text_wrap': True,
        **kw
    })
    
    # define our thick border and an “empty” border
    thick = Side(border_style="thick", color="000000")
    none  = Side(border_style=None)
    
    bg_fmt          = common_fmt(bg_color='#FFFDFA', align='center', valign='vcenter', text_wrap=True, border=0)
    border_fmt      = common_fmt(bg_color='#FFFDFA', align='center', valign='vcenter', text_wrap=True, border=5)
    currency_fmt    = common_fmt(bg_color='#FFFDFA', align='center', valign='vcenter', text_wrap=True, num_format='$#,##0.00', border=1)
    yellow_bold_fmt = common_fmt(bg_color='#F2CC0C', bold=True, align='center', valign='vcenter', text_wrap=True, border=1)
    dark_fmt        = common_fmt(bg_color='#3B4232')
    grey_bold_fmt   = common_fmt(bg_color='#D4D4C9', bold=True, font_size=14, align='center', valign='vcenter', text_wrap=True, border=1)
    header_fmt      = common_fmt(bg_color='#3d4336', font_color='#FFFFFF', text_wrap=True, align='center', valign='vcenter', border=1)
    top_fmt         = common_fmt(bg_color='#FFFDFA', text_wrap=True, indent=1,  align='left', valign='top', border=0)

    # === SHEET 1: Claim Package ===
    ws1 = wb.add_worksheet('Claim Package')
    for r in range(100):
        for c in range(30):
            ws1.write_blank(r, c, None, bg_fmt)

    ws1.hide_gridlines(2)
    ws1.set_tab_color('#FFFDFA')
    ws1.set_column('A:H', 15)
    for r in range(40):
        for c in range(8):
            ws1.write_blank(r, c, None, bg_fmt)
    for r in range(9, 15):
        ws1.set_row(r, 20, border_fmt)
    ws1.merge_range('A1:H15', '', border_fmt)
    ws1.insert_image('A1', logo_path, {'x_scale': 0.39, 'y_scale': 0.36})

    # ——— Claim Package body, sanitized & wrapped ———
    # sanitize Quill HTML → plain text with bullets & newlines
    clean = sanitize_claim_text(claim_text or "")
    # expand tabs → 4 spaces, keep line breaks
    plain = clean.expandtabs(4)

    # 3) write your entire text into the merged cell
    ws1.merge_range('A16:H61', plain, top_fmt)
    # hide everything past column H
    ws1.set_column('AA:XFD', None, None, {'hidden': True})

    # === SHEET 2: Contents Estimate (your specific tweaks) ===
    ws2 = wb.add_worksheet('Contents Estimate')
    # fill background & hide gridlines
    for r in range(100):
        for c in range(100):
            ws2.write_blank(r, c, None, bg_fmt)
    ws2.hide_gridlines(2)
    ws2.set_tab_color('#FFFDFA')
    ws2.set_column('A:D', 31, bg_fmt)
    for r in range(100):
        ws2.set_row(r, 15)

    # 1) A1:D15 dark background (#3d4336)
    header_bg = common_fmt(bg_color='#3d4336', font_color='#FFFFFF', align='center', valign='vcenter', border=1)
    for r in range(15):
        for c in range(4):
            ws2.write_blank(r, c, None, header_bg)

    ws2.merge_range('A1:D15', '', header_fmt)

    sheet2_logo = os.path.abspath('app/static/logo1.jpg')
    ws2.insert_image(
        'A1',
        sheet2_logo,
        {
            'x_scale': 0.60,
            'y_scale': 0.50
        }
    )

    # 3) Metadata rows A2:D7 (Claimant, Property, etc.) on dark background
    labels = ["Claimant", "Property", "Estimator", "Estimate Type", "Date Entered", "Date Completed"]
    for idx, label in enumerate(labels):
        row_idx = 16 + idx         # Excel rows 2–7
        key     = label.lower().replace(" ", "_")
        val     = estimate_data.get(key, "")
        ws2.merge_range(row_idx, 0, row_idx, 1, label, yellow_bold_fmt)
        ws2.merge_range(row_idx, 2, row_idx, 3, val,   yellow_bold_fmt)

    # 4) Row 16 (A16:D16) bold, size 14, height 20
    subtitle_fmt = common_fmt(bold=True, font_size=14, bg_color='#3d4336', font_color='#FFFFFF', align='center', valign='vcenter')
    ws2.merge_range('A16:D16',
                    'Your Valley Isle Valuation L.L.C., Claim Package:',
                    subtitle_fmt)
    ws2.set_row(15, 20)

    # 5) A17:D22 yellow background (#f2cc0c)
    yellow_bg = common_fmt(bg_color='#f2cc0c', align='center', valign='vcenter', border=1)
    for r in range(16, 22):
        ws2.set_row(r, None, yellow_bg)

    ws2.merge_range('A23:D23', '', header_bg)

    # 6) A24:D24 white darker 5% (#F2F2F2)
    # make your white_bg5 format bold with 14-pt font:
    white_bg5 = common_fmt(
        bg_color='#F2F2F2',
        align='center',
        valign='vcenter',
        border=1,
        bold=True,
        font_size=14
    )
    total_val = sum(row.get('total', 0.0) for row in estimate_data.get('rows', []))
    ws2.merge_range('A24:D24',
                    f"Total Replacement Cost Value: ${total_val:,.2f}",
                    white_bg5)
    ws2.set_row(23, None)

    # 7) Row 25 headers (A25:D25) dark background with white bold text
    header2 = common_fmt(bg_color='#3d4336', font_color='#FFFFFF', bold=True, align='center', valign='vcenter', border=1)
    ws2.set_row(24, 20, header2)
    for col, h in enumerate(['Category', 'Description', 'Justification', 'Total']):
        ws2.write(24, col, h, header2)

    # 8) Data rows start at row 26 (index 25)
    cell_fmt    = common_fmt(bg_color='#F2F2F2', align='center', valign='vcenter', border=1)
    desc_fmt    = common_fmt(bg_color='#F2F2F2', italic=True, align='center', valign='vcenter', border=1)
    total_fmt   = common_fmt(bg_color='#f2cc0c', bold=True, num_format='$#,##0.00', align='center', valign='vcenter', border=1)
    for i, row in enumerate(estimate_data.get('rows', [])):
        r = 25 + i
        ws2.write(r, 0, row.get('category', ''),    cell_fmt)
        ws2.write(r, 1, row.get('description', ''),  desc_fmt)
        ws2.write(r, 2, row.get('justification', ''),cell_fmt)
        ws2.write(r, 3, row.get('total', 0.0),       total_fmt)

    ws2.set_column('AA:XFD', None, None, { 'hidden': True })

    wb.close()

    # === UPLOAD TO S3 (public) ===
    s3 = boto3.client(
        "s3",
        region_name=os.getenv("S3_REGION"),
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    )
    filename = os.path.basename(excel_path)
    s3_key   = f"finalized/{filename}"
    bucket   = os.getenv("S3_BUCKET_NAME")
    s3.upload_file(
        excel_path,
        bucket,
        s3_key,
        ExtraArgs={"ACL": "public-read"}
    )

    region = os.getenv("S3_REGION")
    return f"https://{bucket}.s3.{region}.amazonaws.com/{s3_key}"


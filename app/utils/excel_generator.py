import os
import xlsxwriter
import boto3

# Path to new Contents Estimate logo (sheet 2)
SHEET2_LOGO_PATH = 'app/static/logo1.jpg'


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

    # === FORMATS ===
    # Sheet 1 formats
    header_fmt_1 = wb.add_format({
        'font_name': 'Times New Roman', 'bold': True,
        'font_color': '#FFFFFF', 'align': 'center',
        'valign': 'vcenter', 'bg_color': '#3d4336'
    })
    subtitle_fmt = wb.add_format({
        'font_name': 'Times New Roman', 'bold': True,
        'font_color': '#FFFFFF', 'align': 'center',
        'valign': 'vcenter'
    })
    area_fmt_1 = wb.add_format({
        'font_name': 'Times New Roman',
        'align': 'center', 'valign': 'vcenter',
        'bg_color': '#f2cc0c'
    })
    total_bg_fmt_1 = wb.add_format({
        'font_name': 'Times New Roman',
        'align': 'center', 'valign': 'vcenter',
        'bg_color': '#F2F2F2'
    })

    # Sheet 2 formats
    header_fmt_2 = wb.add_format({
        'font_name': 'Times New Roman', 'bold': True,
        'font_color': '#FFFFFF', 'align': 'center',
        'valign': 'vcenter', 'bg_color': '#3d4336'
    })
    cell_fmt   = wb.add_format({
        'font_name': 'Times New Roman',
        'align': 'center', 'valign': 'vcenter',
        'bg_color': '#F2F2F2'
    })
    desc_fmt   = wb.add_format({
        'font_name': 'Times New Roman', 'italic': True,
        'align': 'center', 'valign': 'vcenter',
        'bg_color': '#F2F2F2'
    })
    total_fmt  = wb.add_format({
        'font_name': 'Times New Roman', 'bold': True,
        'align': 'center', 'valign': 'vcenter',
        'bg_color': '#f2cc0c', 'num_format': '$#,##0.00'
    })

    # === SHEET 1: Claim Package ===
    ws1 = wb.add_worksheet('Claim Package')
    ws1.hide_gridlines(2)
    ws1.set_column('A:H', 15)

    # A1:D1 background
    ws1.merge_range('A1:D1', '', header_fmt_1)
    ws1.set_row(0, 20)
    # Logo (same size as sheet 2)
    ws1.insert_image('A1', logo_path, {'x_scale': 0.39, 'y_scale': 0.36})

    # Subtitle at A16:D16
    ws1.merge_range(
        'A16:D16',
        'Your Valley Isle Valuation L.L.C., Claim Package:',
        subtitle_fmt
    )
    ws1.set_row(15, 20)

    # A17:D22 background
    for r in range(16, 22):
        ws1.set_row(r, None, area_fmt_1)

    # A24:D24 background
    ws1.set_row(23, None, total_bg_fmt_1)

    # === SHEET 2: Contents Estimate ===
    ws2 = wb.add_worksheet('Contents Estimate')
    ws2.hide_gridlines(2)
    ws2.set_column('A:D', 20)

    # A1:D1 header background
    ws2.merge_range('A1:D1', '', header_fmt_2)
    ws2.set_row(0, 20)
    # Logo on sheet 2
    ws2.insert_image('A1', SHEET2_LOGO_PATH, {'x_scale': 0.39, 'y_scale': 0.36})

    # Metadata rows A2:D7
    for r in range(1, 7):
        ws2.set_row(r, None, total_bg_fmt_1)

    # Total replacement row A8:D8
    total_val = sum(r.get('total', 0) for r in estimate_data.get('rows', []))
    ws2.merge_range(
        'A8:D8',
        f"Total Replacement Cost Value: ${total_val:,.2f}",
        total_bg_fmt_1
    )
    ws2.set_row(7, None)

    # Remove original row 25 (index 24) if present
    # Now set headers at row 25 (index 24)
    ws2.set_row(24, 20, header_fmt_2)
    headers = ['Category', 'Description', 'Justification', 'Total']
    for col, hdr in enumerate(headers):
        ws2.write(24, col, hdr, header_fmt_2)

    # Data rows start at 26 (index 25)
    for i, row in enumerate(estimate_data.get('rows', [])):
        r = 25 + i
        ws2.write(r, 0, row.get('category', ''), cell_fmt)
        ws2.write(r, 1, row.get('description', ''), desc_fmt)
        ws2.write(r, 2, row.get('justification', ''), cell_fmt)
        ws2.write(r, 3, row.get('total', 0), total_fmt)

    wb.close()
    return excel_path


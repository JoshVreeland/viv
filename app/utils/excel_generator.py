import os
import xlsxwriter
import boto3

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
    bg_fmt          = wb.add_format({
        'font_name': 'Times New Roman',
        'bg_color': '#FFFDFA',
        'align': 'center',
        'valign': 'vcenter',
        'text_wrap': True,
        'border': 0
    })
    border_fmt      = wb.add_format({
        'font_name': 'Times New Roman',
        'bg_color': '#FFFDFA',
        'align': 'center',
        'valign': 'vcenter',
        'text_wrap': True,
        'border': 1
    })
    currency_fmt    = wb.add_format({
        'font_name': 'Times New Roman',
        'bg_color': '#FFFDFA',
        'align': 'center',
        'valign': 'vcenter',
        'num_format': '$#,##0.00',
        'border': 1
    })
    yellow_bold_fmt = wb.add_format({
        'font_name': 'Times New Roman',
        'bg_color': '#F6E60B',
        'bold': True,
        'align': 'center',
        'valign': 'vcenter',
        'text_wrap': True,
        'border': 1
    })
    grey_bold_fmt   = wb.add_format({
        'font_name': 'Times New Roman',
        'bg_color': '#D4D4C9',
        'bold': True,
        'font_size': 14,
        'align': 'center',
        'valign': 'vcenter',
        'text_wrap': True,
        'border': 1
    })

    # === SHEET 1: Claim Package (unchanged) ===
    ws1 = wb.add_worksheet('Claim Package')
    for r in range(100):
        for c in range(100):
            ws1.write_blank(r, c, None, bg_fmt)
    ws1.hide_gridlines(2)
    ws1.set_tab_color('#FFFDFA')
    ws1.set_column('A:H', 15)
    for r in range(40):
        for c in range(8):
            ws1.write_blank(r, c, None, bg_fmt)
    for r in range(9, 15):
        ws1.set_row(r, 20, bg_fmt)
    ws1.merge_range('A1:H15', '', border_fmt)
    ws1.insert_image('A1', logo_path, {'x_scale': 0.39, 'y_scale': 0.36})
    ws1.merge_range('A16:H40', claim_text, border_fmt)

    # === SHEET 2: Contents Estimate (with your specific tweaks) ===
    ws2 = wb.add_worksheet('Contents Estimate')
    ws2.hide_gridlines(2)
    ws2.set_tab_color('#FFFDFA')
    ws2.set_column('A:D', 31, bg_fmt)
    for r in range(100):
        ws2.set_row(r, 15)

    # 1) A1:D15 background = #3d4336
    header_bg = wb.add_format({
        'font_name': 'Times New Roman',
        'bg_color': '#3d4336',
        'align': 'center',
        'valign': 'vcenter'
    })
    for r in range(15):
        for c in range(4):
            ws2.write_blank(r, c, None, header_bg)

    # 2) Logo at same scale as Sheet 1
    sheet2_logo = os.path.abspath('app/static/logo1.jpg')
    ws2.insert_image('A1', sheet2_logo, {'x_scale': 0.39, 'y_scale': 0.36})

    # 3) Metadata A2:D7 (Claimant, Property, etc.) over dark background
    meta_label = wb.add_format({
        'font_name': 'Times New Roman',
        'bold': True,
        'font_color': '#FFFFFF',
        'bg_color': '#3d4336',
        'align': 'center',
        'valign': 'vcenter'
    })
    meta_val = wb.add_format({
        'font_name': 'Times New Roman',
        'font_color': '#FFFFFF',
        'bg_color': '#3d4336',
        'align': 'center',
        'valign': 'vcenter'
    })
    labels = [
        "Claimant", "Property", "Estimator",
        "Estimate Type", "Date Entered", "Date Completed"
    ]
    for idx, label in enumerate(labels):
        row_idx = 1 + idx  # Excel rows 2–7
        key = label.lower().replace(" ", "_")
        val = estimate_data.get(key, "")
        ws2.merge_range(row_idx, 0, row_idx, 1, label, meta_label)
        ws2.merge_range(row_idx, 2, row_idx, 3, val,   meta_val)

    # 4) Row 16 (Excel) bold, font 14, height 20
    subtitle_fmt = wb.add_format({
        'font_name': 'Times New Roman',
        'bold': True,
        'font_size': 14,
        'align': 'center',
        'valign': 'vcenter',
        'bg_color': '#3d4336'
    })
    ws2.merge_range('A16:D16',
                    'Your Valley Isle Valuation L.L.C., Claim Package:',
                    subtitle_fmt)
    ws2.set_row(15, 20)  # row index 15 → Excel row 16

    # 5) Header row 25 (unchanged from before)
    ws2.write(24, 0, 'Category', yellow_bold_fmt)
    ws2.write(24, 1, 'Description', yellow_bold_fmt)
    ws2.write(24, 2, 'Justification', yellow_bold_fmt)
    ws2.write(24, 3, 'Total', yellow_bold_fmt)

    # 6) Data rows: A–C white background (#F2F2F2), Times New Roman
    white_bg = wb.add_format({
        'font_name': 'Times New Roman',
        'bg_color': '#F2F2F2',
        'align': 'center',
        'valign': 'vcenter',
        'border': 1
    })
    total_fmt = wb.add_format({
        'font_name': 'Times New Roman',
        'bold': True,
        'num_format': '$#,##0.00',
        'align': 'center',
        'valign': 'vcenter',
        'border': 1
    })
    start_row = 25
    for i, row in enumerate(estimate_data.get('rows', [])):
        r = start_row + i
        ws2.write(r, 0, row.get('category', ''), white_bg)
        ws2.write(r, 1, row.get('description', ''), white_bg)
        ws2.write(r, 2, row.get('justification', ''), white_bg)
        ws2.write(r, 3, row.get('total', 0.0), total_fmt)

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


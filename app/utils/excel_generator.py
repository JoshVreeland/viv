import os
import xlsxwriter
import boto3

def generate_excel(pdf_path: str,
                   logo_path: str,
                   claim_text: str,
                   estimate_data: dict,
                   client_name: str) -> str:
    # ———————————————————————————————
    # Guard against tuple/list (e.g. if pdf_path was returned as (path, ...))
    if isinstance(pdf_path, (tuple, list)):
        pdf_path = pdf_path[0]
    # ———————————————————————————————

    out_dir = os.path.dirname(pdf_path)
    os.makedirs(out_dir, exist_ok=True)

    safe = client_name.replace(" ", "_")
    excel_path = os.path.join(out_dir, f"{safe}_Claim.xlsx")

    wb = xlsxwriter.Workbook(excel_path)

    # === FORMATS ===
    bg_fmt = wb.add_format({
        'bg_color': '#FFFDFA',
        'align': 'center',
        'valign': 'vcenter',
        'text_wrap': True,
        'border': 0
    })
    border_fmt = wb.add_format({
        'bg_color': '#FFFDFA',
        'align': 'center',
        'valign': 'vcenter',
        'text_wrap': True,
        'border': 1
    })
    currency_fmt = wb.add_format({
        'bg_color': '#FFFDFA',
        'align': 'center',
        'valign': 'vcenter',
        'num_format': '$#,##0.00',
        'border': 1
    })

    dark_fmt = wb.add_format({'bg_color': '#3B4232'})
    yellow_bold_fmt = wb.add_format({
        'bg_color': '#F6E60B',
        'bold': True,
        'align': 'center',
        'valign': 'vcenter',
        'text_wrap': True,
        'border': 1
    })

    grey_bold_fmt = wb.add_format({
        'bg_color': '#D4D4C9',
        'bold': True,
        'font_size': 14,
        'align': 'center',
        'valign': 'vcenter',
        'text_wrap': True,
        'border': 1
    })

    # === SHEET 1: Claim Package ===
    ws1 = wb.add_worksheet('Claim Package')
    for row in range(100):
        for col in range(100):
            ws1.write_blank(row, col, None, bg_fmt)
    ws1.hide_gridlines(2)
    ws1.set_tab_color('#FFFDFA')
    ws1.set_column('A:H', 15)
    for row in range(40):
        for col in range(8):
            ws1.write_blank(row, col, None, bg_fmt)
    for r in range(9, 15):
        ws1.set_row(r, 20, bg_fmt)
    ws1.merge_range('A1:H15', '', border_fmt)
    ws1.insert_image('A1', logo_path, {'x_scale': 0.39, 'y_scale': 0.36})
    ws1.merge_range('A16:H40', claim_text, border_fmt)

    # === SHEET 2: Contents Estimate ===
    ws2 = wb.add_worksheet("Contents Estimate")
    for row in range(100):
        for col in range(100):
            ws2.write_blank(row, col, None, bg_fmt)
    ws2.hide_gridlines(2)
    ws2.set_tab_color('#FFFDFA')
    ws2.set_column('A:D', 31, bg_fmt)
    for r in range(100):
        ws2.set_row(r, 15)
    for col in range(4):
        ws2.write(15, col, '', dark_fmt)
        ws2.write(22, col, '', dark_fmt)
        ws2.write(24, col, '', dark_fmt)
    ws2.merge_range('A1:D15', '', border_fmt)
    ws2.insert_image('A1', logo_path, {'x_scale': 0.39, 'y_scale': 0.36})

    labels = [
        "Claimant", "Property", "Estimator",
        "Estimate Type", "Date Entered", "Date Completed"
    ]
    for idx, label in enumerate(labels):
        r = 16 + idx
        key = label.lower().replace(" ", "_")
        val = estimate_data.get(key, "")
        ws2.merge_range(r, 0, r, 1, label, yellow_bold_fmt)
        ws2.merge_range(r, 2, r, 3, val, yellow_bold_fmt)

    ws2.set_row(23, 49)
    total = sum(row.get("total", 0.0) for row in estimate_data.get("rows", []))
    ws2.merge_range(
        'A24:D24',
        f"Total Replacement Cost Value: ${total:,.2f}",
        grey_bold_fmt
    )

    ws2.write(25, 0, 'Category', yellow_bold_fmt)
    ws2.merge_range(25, 1, 25, 2, 'Defensible Justification', yellow_bold_fmt)
    ws2.write(25, 3, 'Total', yellow_bold_fmt)

    start_row = 26
    for i, row in enumerate(estimate_data.get('rows', [])):
        r = start_row + i
        ws2.write(r, 0, row.get('category', ""), border_fmt)
        ws2.merge_range(r, 1, r, 2, row.get('justification', ""), border_fmt)
        ws2.write(r, 3, row.get('total', 0.0), currency_fmt)

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
        ExtraArgs={"ACL": "public-read"}      # <<< make it publicly readable
    )

    # build the permanent URL
    region = os.getenv("S3_REGION")
    public_url = f"https://{bucket}.s3.{region}.amazonaws.com/{s3_key}"

    return public_url

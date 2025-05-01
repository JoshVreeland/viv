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

    # === FORMATS (shared) ===
    bg_fmt         = wb.add_format({'bg_color': '#FFFDFA','align': 'center','valign': 'vcenter','text_wrap': True,'border': 0})
    border_fmt     = wb.add_format({'bg_color': '#FFFDFA','align': 'center','valign': 'vcenter','text_wrap': True,'border': 1})
    currency_fmt   = wb.add_format({'bg_color': '#FFFDFA','align': 'center','valign': 'vcenter','num_format': '$#,##0.00','border': 1})
    dark_fmt       = wb.add_format({'bg_color': '#3B4232'})
    yellow_bold_fmt= wb.add_format({'bg_color': '#F6E60B','bold': True,'align': 'center','valign': 'vcenter','text_wrap': True,'border': 1})
    grey_bold_fmt  = wb.add_format({'bg_color': '#D4D4C9','bold': True,'font_size': 14,'align': 'center','valign': 'vcenter','text_wrap': True,'border': 1})

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
    # fill background
    for r in range(100):
        for c in range(100):
            ws2.write_blank(r, c, None, bg_fmt)
    ws2.hide_gridlines(2)
    ws2.set_tab_color('#FFFDFA')
    ws2.set_column('A:D', 31, bg_fmt)
    for r in range(100):
        ws2.set_row(r, 15)
    # dark header rows
    for col in range(4):
        ws2.write(15, col, '', dark_fmt)
        ws2.write(22, col, '', dark_fmt)
        ws2.write(24, col, '', dark_fmt)

    # original header block
    ws2.merge_range('A1:D15', '', border_fmt)
    # sheet2 logo (logo1.jpg) at same scale as sheet1
    sheet2_logo = os.path.abspath('app/static/logo1.jpg')
    ws2.insert_image('A1', sheet2_logo, {'x_scale': 0.39, 'y_scale': 0.36})

    # your custom subtitle in A16:D16
    subtitle_fmt = wb.add_format({'bold': True, 'font_color': '#FFFFFF','align':'center','valign':'vcenter','bg_color':'#3B4232'})
    ws2.merge_range('A16:D16',
                    'Your Valley Isle Valuation L.L.C., Claim Package:',
                    subtitle_fmt)
    ws2.set_row(15, 20)

    # A17:D22 background #f2cc0c
    yellow_bg = wb.add_format({'bg_color':'#f2cc0c','align':'center','valign':'vcenter'})
    for r in range(16, 22):
        ws2.set_row(r, None, yellow_bg)

    # A24:D24 white, darker 5% (#F2F2F2)
    white_bg = wb.add_format({'bg_color':'#F2F2F2','align':'center','valign':'vcenter','border':1})
    total = sum(row.get('total',0.0) for row in estimate_data.get('rows', []))
    ws2.merge_range('A24:D24',
                    f"Total Replacement Cost Value: ${total:,.2f}",
                    white_bg)
    ws2.set_row(23, None)

    # delete original row25 (index24) styling and rewrite headers at row25
    header_fmt2 = wb.add_format({'bg_color':'#3d4336','font_color':'#FFFFFF','bold':True,'align':'center','valign':'vcenter'})
    ws2.set_row(24, 20, header_fmt2)
    headers = ['Category','Description','Justification','Total']
    for col, h in enumerate(headers):
        ws2.write(24, col, h, header_fmt2)

    # data rows from row26 onward
    italic_fmt = wb.add_format({'italic': True,'border':1,'align':'center','valign':'vcenter'})
    bold_total = wb.add_format({'num_format':'$#,##0.00','bold':True,'border':1,'align':'center','valign':'vcenter','bg_color':'#f2cc0c'})
    for i, row in enumerate(estimate_data.get('rows', [])):
        r = 25 + i
        ws2.write(r, 0, row.get('category',''), border_fmt)
        ws2.write(r, 1, row.get('description',''), italic_fmt)
        ws2.write(r, 2, row.get('justification',''), border_fmt)
        ws2.write(r, 3, row.get('total',0.0), bold_total)

    wb.close()

    # === UPLOAD TO S3 (public) ===
    s3 = boto3.client(
        's3',
        region_name=os.getenv('S3_REGION'),
        aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
    )
    filename = os.path.basename(excel_path)
    s3_key   = f'finalized/{filename}'
    bucket   = os.getenv('S3_BUCKET_NAME')
    s3.upload_file(excel_path, bucket, s3_key, ExtraArgs={'ACL':'public-read'})

    # build public URL
    region = os.getenv('S3_REGION')
    return f"https://{bucket}.s3.{region}.amazonaws.com/{s3_key}"


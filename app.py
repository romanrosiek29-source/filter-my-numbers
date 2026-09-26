import csv
import io
import os
from flask import Flask, Response, render_template_string, request
import phonenumbers
from phonenumbers import carrier, geocoder

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024

PAGE = '''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Filter my Numbers</title><style>body{font-family:system-ui,sans-serif;background:#f5f7fb;color:#172033;margin:0}main{max-width:900px;margin:48px auto;padding:24px}form,.card{background:white;padding:24px;border-radius:12px;box-shadow:0 2px 12px #17203312;margin:18px 0}label{display:block;margin:14px 0 6px}input{max-width:100%}button,.button{display:inline-block;background:#3156db;color:white;border:0;border-radius:8px;padding:12px 18px;cursor:pointer;text-decoration:none}.error{color:#a21c32}.note{color:#596579}table{width:100%;border-collapse:collapse;background:white}td,th{padding:10px;border-bottom:1px solid #ddd;text-align:left}.scroll{overflow-x:auto}</style></head><body><main><h1>Filter my Numbers</h1><p class="note">Numbering-plan validation only. This does not confirm a number is active, reachable, or registered on an app.</p><form method="post" action="/check" enctype="multipart/form-data"><label for="file">CSV or TXT file (one number per line; CSV: first column)</label><input id="file" name="file" type="file" accept=".csv,.txt" required><label for="region">Two-letter region for local numbers (for example PK)</label><input id="region" name="region" maxlength="2" pattern="[A-Za-z]{2}" placeholder="PK"><p class="note">Maximum 5,000 numbers and 2 MB. Files are processed in memory, not stored.</p><button>Check numbers</button></form>{% if error %}<p class="error" role="alert">{{error}}</p>{% endif %}{% if results is not none %}<div class="card"><h2>Results</h2><p>{{results|length}} checked; {{results|selectattr('valid')|list|length}} valid by numbering plan.</p><a class="button" id="download" href="#">Download CSV</a></div><div class="scroll"><table><thead><tr><th>Input</th><th>Valid</th><th>E.164</th><th>Region</th><th>Carrier (original allocation)</th><th>Type</th><th>Note</th></tr></thead><tbody>{% for r in results[:100] %}<tr><td>{{r.input}}</td><td>{{'Yes' if r.valid else 'No'}}</td><td>{{r.e164}}</td><td>{{r.region}}</td><td>{{r.carrier}}</td><td>{{r.type}}</td><td>{{r.note}}</td></tr>{% endfor %}</tbody></table></div><p class="note">Showing first 100 rows; download for all results. Preview is not saved after you leave this page.</p><script>const rows={{ csvrows|tojson }};const escape=v=>'"'+String(v).replaceAll('"','""')+'"';const csv=rows.map(row=>row.map(escape).join(',')).join('\r\n');const blob=new Blob(['\ufeff',csv],{type:'text/csv;charset=utf-8'});const url=URL.createObjectURL(blob);const link=document.getElementById('download');link.href=url;link.download='filter-my-numbers.csv';window.addEventListener('pagehide',()=>URL.revokeObjectURL(url));</script>{% endif %}</main></body></html>'''

HEADERS = ('input', 'valid', 'e164', 'region', 'carrier', 'type', 'note')

def safe_cell(value):
    text = str(value)
    return "'" + text if text.lstrip().startswith(('=', '+', '-', '@', '\t', '\r')) else text

def check_number(raw, region):
    result = dict(input=raw, valid=False, e164='', region='', carrier='', type='', note='')
    try:
        parsed = phonenumbers.parse(raw, region)
        result['e164'] = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
        result['region'] = phonenumbers.region_code_for_number(parsed) or ''
        result['valid'] = phonenumbers.is_valid_number(parsed)
        if result['valid']:
            result['carrier'] = carrier.name_for_number(parsed, 'en') or 'Unknown'
            result['type'] = str(phonenumbers.number_type(parsed))
            result['note'] = geocoder.description_for_number(parsed, 'en') or ''
        else:
            result['note'] = 'Not valid under current numbering plan'
    except phonenumbers.NumberParseException as exc:
        result['note'] = str(exc)
    return result

@app.get('/')
def index():
    return render_template_string(PAGE, results=None, error=None)

@app.post('/check')
def check():
    uploaded = request.files.get('file')
    region = request.form.get('region', '').strip().upper() or None
    if region and (len(region) != 2 or not region.isascii() or not region.isalpha()):
        return render_template_string(PAGE, results=None, error='Use a two-letter ISO country code.'), 400
    if not uploaded or not uploaded.filename.lower().endswith(('.csv', '.txt')):
        return render_template_string(PAGE, results=None, error='Choose a CSV or TXT file.'), 400
    try:
        text = uploaded.read().decode('utf-8-sig')
        if uploaded.filename.lower().endswith('.csv'):
            values = [row[0].strip() for row in csv.reader(io.StringIO(text)) if row and row[0].strip()]
        else:
            values = [line.strip() for line in text.splitlines() if line.strip()]
    except (UnicodeDecodeError, csv.Error):
        return render_template_string(PAGE, results=None, error='Use a valid UTF-8 CSV or TXT file.'), 400
    if not values or len(values) > 5000:
        return render_template_string(PAGE, results=None, error='File must contain 1 to 5,000 numbers.'), 400
    results = [check_number(value, region) for value in values]
    csvrows = [list(HEADERS)] + [[safe_cell(row[key]) for key in HEADERS] for row in results]
    response = Response(render_template_string(PAGE, results=results, csvrows=csvrows, error=None))
    response.headers['Cache-Control'] = 'no-store'
    return response

@app.get('/health')
def health():
    return {'status': 'ok'}

@app.errorhandler(413)
def too_large(error):
    return render_template_string(PAGE, results=None, error='File exceeds 2 MB.'), 413

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=int(os.environ.get('PORT', '5000')))

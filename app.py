import os
import sys
import uuid
import threading
from flask import Flask, render_template, request, send_file, jsonify

sys.path.insert(0, os.path.dirname(__file__))
from main_analysis import analyze_files

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), 'uploads')
os.makedirs(UPLOAD_DIR, exist_ok=True)

jobs = {}
jobs_lock = threading.Lock()

cic = None
try:
    from pyhamtools import LookupLib, Callinfo, locator as loc_mod
    lib = LookupLib(lookuptype="countryfile")
    cic = Callinfo(lib)
except Exception:
    pass


def run_analysis(job_id, file_list, locator, output_file, power_override):
    try:
        analyze_files(file_list, locator, output_file, power_override=power_override)
        with jobs_lock:
            jobs[job_id]['status'] = 'done'
    except Exception as e:
        with jobs_lock:
            jobs[job_id]['status'] = 'error'
            jobs[job_id]['error'] = str(e)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/locator')
def get_locator():
    call = request.args.get('callsign', '').strip().upper()
    if not call:
        return jsonify({'error': 'Укажите позывной'}), 400

    if not cic:
        return jsonify({'error': 'База данных недоступна'}), 503

    try:
        pos = cic.get_lat_long(call)
        if pos and 'latitude' in pos and 'longitude' in pos:
            loc = loc_mod.latlong_to_locator(pos["latitude"], pos["longitude"])
            if len(loc) == 4:
                loc = loc + "MM"
            return jsonify({'locator': loc[:6]})
    except Exception:
        pass

    return jsonify({'error': 'Не удалось определить локатор'}), 404


@app.route('/analyze', methods=['POST'])
def analyze():
    call = request.form.get('callsign', '').strip().upper()
    locator = request.form.get('locator', '').strip().upper()

    if not call:
        return jsonify({'error': 'Укажите позывной'}), 400
    if not locator:
        return jsonify({'error': 'Укажите локатор'}), 400

    power_override = request.form.get('power_override', '').strip()
    power_override_val = None
    if power_override:
        try:
            power_override_val = float(power_override.replace(',', '.'))
        except ValueError:
            return jsonify({'error': 'Некорректное значение мощности'}), 400

    files = request.files.getlist('adif_files')
    if not files or all(f.filename == '' for f in files):
        return jsonify({'error': 'Загрузите ADIF файл(ы)'}), 400

    job_id = uuid.uuid4().hex[:8]
    job_dir = os.path.join(UPLOAD_DIR, job_id)
    os.makedirs(job_dir, exist_ok=True)

    saved_files = []
    for f in files:
        if f.filename:
            safe_name = f.filename.replace('/', '_').replace('\\', '_')
            path = os.path.join(job_dir, safe_name)
            f.save(path)
            saved_files.append(path)

    output_file = os.path.join(job_dir, 'result.txt')

    with jobs_lock:
        jobs[job_id] = {'status': 'processing', 'output_file': output_file, 'error': None}

    thread = threading.Thread(target=run_analysis, args=(job_id, saved_files, locator, output_file, power_override_val), daemon=True)
    thread.start()

    return jsonify({'job_id': job_id})


@app.route('/status/<job_id>')
def status(job_id):
    with jobs_lock:
        job = jobs.get(job_id)

    if not job:
        return jsonify({'error': 'Задача не найдена'}), 404

    if job['status'] == 'processing':
        return jsonify({'status': 'processing'})
    elif job['status'] == 'error':
        return jsonify({'status': 'error', 'error': job['error']})
    else:
        with open(job['output_file'], 'r', encoding='utf-8') as fh:
            result_text = fh.read()
        return jsonify({'status': 'done', 'result': result_text, 'download_id': job_id})


@app.route('/download/<job_id>')
def download(job_id):
    result_file = os.path.join(UPLOAD_DIR, job_id, 'result.txt')
    if not os.path.exists(result_file):
        return 'Файл не найден', 404
    return send_file(result_file, as_attachment=True, download_name='adif_analysis_result.txt')


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)

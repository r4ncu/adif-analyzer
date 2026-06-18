import os
import sys
import tempfile
import uuid
from flask import Flask, render_template, request, send_file, jsonify

sys.path.insert(0, os.path.dirname(__file__))
from main_analysis import analyze_files

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), 'uploads')
os.makedirs(UPLOAD_DIR, exist_ok=True)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/analyze', methods=['POST'])
def analyze():
    call = request.form.get('callsign', '').strip().upper()
    locator = request.form.get('locator', '').strip().upper()

    if not call:
        return jsonify({'error': 'Укажите позывной'}), 400
    if not locator:
        return jsonify({'error': 'Укажите локатор'}), 400

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

    try:
        analyze_files(saved_files, locator, output_file)
    except Exception as e:
        return jsonify({'error': f'Ошибка анализа: {str(e)}'}), 500

    with open(output_file, 'r', encoding='utf-8') as fh:
        result_text = fh.read()

    return jsonify({
        'result': result_text,
        'download_id': job_id
    })


@app.route('/download/<job_id>')
def download(job_id):
    result_file = os.path.join(UPLOAD_DIR, job_id, 'result.txt')
    if not os.path.exists(result_file):
        return 'Файл не найден', 404
    return send_file(result_file, as_attachment=True, download_name='adif_analysis_result.txt')


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)

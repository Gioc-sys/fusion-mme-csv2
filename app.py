import os
import json
import shutil
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_file
from werkzeug.utils import secure_filename
from io import BytesIO
from mme_processor import MMEProcessor

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'temp_uploads'
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

DEFAULT_SETTINGS = {
    'csvHeadVelocityColumn': 'Tracking Head Rebound Velocity.y',
    'csvSeatbackColumn': 'Tracking Seatback Deflection.y',
    'mmeHeadVelocityChannel': '11HEAD0000BRVEXP',
    'mmeSeatbackChannel': '11SEAT000000ANXP'
}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/settings', methods=['GET'])
def get_settings():
    return jsonify(DEFAULT_SETTINGS)

@app.route('/api/add-csv', methods=['POST'])
def add_csv():
    try:
        if 'mmeFile' not in request.files or 'csvFile' not in request.files:
            return jsonify({'error': 'Fichiers requis'}), 400
        
        mme_file = request.files['mmeFile']
        csv_file = request.files['csvFile']
        
        settings_json = request.form.get('settings', '{}')
        settings = json.loads(settings_json)
        
        source_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(mme_file.filename))
        csv_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(csv_file.filename))
        
        mme_file.save(source_path)
        csv_file.save(csv_path)
        
        processor = MMEProcessor()
        result_buffer, stats = processor.add_csv_channels(source_path, csv_path, {**DEFAULT_SETTINGS, **settings})
        
        result_id = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        result_path = os.path.join(app.config['UPLOAD_FOLDER'], f'result_{result_id}.zip')
        
        with open(result_path, 'wb') as f:
            f.write(result_buffer)
        
        return jsonify({'success': True, 'stats': stats, 'resultId': result_id, 'filename': mme_file.filename})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/merge', methods=['POST'])
def merge():
    try:
        files = request.files.getlist('mmeFiles')
        if len(files) < 2:
            return jsonify({'error': 'Au moins 2 fichiers requis'}), 400
        
        paths = []
        for f in files:
            p = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(f.filename))
            f.save(p)
            paths.append(p)
        
        processor = MMEProcessor()
        result_buffer, stats = processor.merge_mme_files(paths)
        
        result_id = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        result_path = os.path.join(app.config['UPLOAD_FOLDER'], f'result_{result_id}.zip')
        
        with open(result_path, 'wb') as f:
            f.write(result_buffer)
        
        return jsonify({'success': True, 'stats': stats, 'resultId': result_id, 'filename': 'merged.zip'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/download/<result_id>/<filename>')
def download(result_id, filename):
    try:
        result_path = os.path.join(app.config['UPLOAD_FOLDER'], f'result_{result_id}.zip')
        if not os.path.exists(result_path):
            return jsonify({'error': 'Non trouvé'}), 404
        
        with open(result_path, 'rb') as f:
            data = f.read()
        
        return send_file(BytesIO(data), mimetype='application/zip', as_attachment=True, download_name=f"{filename}_traité.zip")
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/shutdown', methods=['POST'])
def shutdown():
    try:
        if os.path.exists(app.config['UPLOAD_FOLDER']):
            shutil.rmtree(app.config['UPLOAD_FOLDER'])
        os._exit(0)
    except:
        os._exit(0)

if __name__ == '__main__':
    import webbrowser
    from threading import Timer
    Timer(1, lambda: webbrowser.open('http://127.0.0.1:5001/')).start()
    app.run(debug=True, use_reloader=False, port=5001)

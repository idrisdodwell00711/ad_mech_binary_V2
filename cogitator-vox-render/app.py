# -*- coding: utf-8 -*-
"""
Cogitator-Vox MK.IV — web data-shrine (Flask).
Deployable on Render. Stateless: nothing is stored; files are streamed back.
"""

import io
from flask import Flask, request, render_template, send_file, jsonify

import codec

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 25 * 1024 * 1024   # 25 MB upload cap


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/encode', methods=['POST'])
def encode():
    # Prefer an uploaded scroll; fall back to the text box.
    text = ''
    up = request.files.get('scroll')
    if up and up.filename:
        text = up.read().decode('utf-8', errors='replace')
    else:
        text = request.form.get('text', '')

    if not text.strip():
        return jsonify(ok=False, reason='The vox cannot carry silence.'), 400

    wav = codec.encode_to_wav_bytes(text)
    return send_file(io.BytesIO(wav), mimetype='audio/wav',
                     as_attachment=True, download_name='vox_transmission.wav')


@app.route('/decode', methods=['POST'])
def decode():
    up = request.files.get('vox')
    if not up or not up.filename:
        return jsonify(ok=False, reason='No vox-transmission submitted.'), 400
    try:
        result = codec.decode_from_wav_bytes(up.read())
    except Exception as ex:
        return jsonify(ok=False, reason=f'Auspex failure: {ex}'), 400
    return jsonify(result)


@app.route('/healthz')
def healthz():
    return 'OK', 200


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

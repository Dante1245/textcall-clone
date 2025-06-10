from flask import Flask, render_template, request, session, redirect, url_for
from dotenv import load_dotenv
import os
from auth import auth_bp, init_oauth
from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import requests
import uuid

load_dotenv()
app = Flask(__name__)
init_oauth(app)
app.register_blueprint(auth_bp)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///calls.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

client = Client(os.getenv('TWILIO_ACCOUNT_SID'), os.getenv('TWILIO_AUTH_TOKEN'))

class CallLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_email = db.Column(db.String(120), nullable=False)
    to_number = db.Column(db.String(20), nullable=False)
    message = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

@app.route('/')
def index():
    return render_template('index.html', user=session.get('user'))

@app.route('/call', methods=['POST'])
def make_call():
    if 'user' not in session:
        return redirect('/login')

    to_number = request.form['to']
    message = request.form['message']

    # Validate reCAPTCHA
    recaptcha_response = request.form.get('g-recaptcha-response')
    verify = requests.post(
        'https://www.google.com/recaptcha/api/siteverify',
        data={'secret': os.getenv('RECAPTCHA_SECRET_KEY'), 'response': recaptcha_response}
    ).json()

    if not verify.get('success'):
        return "reCAPTCHA failed."

    # Generate TTS from ElevenLabs
    audio_filename = f"static/audio_{uuid.uuid4()}.mp3"
    headers = {
        "xi-api-key": os.getenv("ELEVENLABS_API_KEY"),
        "Content-Type": "application/json"
    }
    json_data = {
        "text": message,
        "voice_settings": {"stability": 0.4, "similarity_boost": 0.75}
    }
    tts_url = f"https://api.elevenlabs.io/v1/text-to-speech/{os.getenv('ELEVENLABS_VOICE_ID')}"
    response = requests.post(tts_url, headers=headers, json=json_data)
    with open(audio_filename, "wb") as f:
        f.write(response.content)

    call = client.calls.create(
        to=to_number,
        from_=os.getenv('TWILIO_PHONE_NUMBER'),
        url=url_for('twiml', audio_url=request.host_url + audio_filename, _external=True)
    )

    db.session.add(CallLog(user_email=session['user']['email'], to_number=to_number, message=message))
    db.session.commit()

    return f"Calling {to_number}..."

@app.route('/twiml')
def twiml():
    audio_url = request.args.get("audio_url")
    resp = VoiceResponse()
    resp.play(audio_url)
    return str(resp)

@app.route('/history')
def history():
    if 'user' not in session:
        return redirect('/login')

    logs = CallLog.query.filter_by(user_email=session['user']['email']).order_by(CallLog.timestamp.desc()).all()
    return render_template('history.html', logs=logs, user=session['user'])

if __name__ == '__main__':
    app.run(debug=True)

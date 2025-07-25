from flask import Flask, jsonify, send_file, request, Response, stream_with_context
from flask_cors import CORS
import os
import json
import subprocess

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})

# Absolute paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE_DIR, "data", "merged.json")
EXCEL_FILE = os.path.join(BASE_DIR, "final_dorahacks_data.xlsx")

# Path to the scraper script (assumes it's one level up in the 'scraper' folder)
SCRAPER_PATH = os.path.abspath(os.path.join(BASE_DIR, "..", "backend/scraper", "main.py"))

@app.route("/api/scrape", methods=["GET"])
def stream_scraper_logs():
    def generate():
        process = subprocess.Popen(
            ['python', SCRAPER_PATH],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=1,
            universal_newlines=True
        )
        for line in iter(process.stdout.readline, ''):
            yield f"data: {line.strip()}\n\n"
        process.stdout.close()
        process.wait()
        # 🔥 Tell frontend scraping is done!
        yield "event: done\ndata: complete\n\n"

    return Response(stream_with_context(generate()), mimetype="text/event-stream")


@app.route("/api/projects", methods=["GET"])
def get_projects():
    print("📂 Checking merged.json at:", DATA_PATH)
    if not os.path.exists(DATA_PATH):
        print("❌ File not found.")
        return jsonify({"error": "No data found"}), 404
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    return jsonify(data)

@app.route("/api/download", methods=["GET"])
def download_excel():
    if os.path.exists(EXCEL_FILE):
        return send_file(EXCEL_FILE, as_attachment=True)
    return jsonify({"error": "Excel file not found"}), 404

if __name__ == "__main__":
    app.run(debug=True, port=5001, use_reloader=False)

from flask import Flask, render_template, request, redirect, send_file
from osuMatchHub import get_osu_token, get_match_data, parse_match_data, insert_scores, ensure_database_exists, init_db
import csv
import io
import re
import os
from dotenv import load_dotenv
load_dotenv()  # loads .env variables locally


app = Flask(__name__)

# Flask will listen on Render's assigned PORT
PORT = int(os.getenv("PORT", 5000))
@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        match_id = request.form.get("match_id")
        if match_id:
            # Initialize DB only when needed
            ensure_database_exists()
            init_db()

            token = get_osu_token()
            if not token:
                return "Failed to get osu! token", 500

            data = get_match_data(match_id, token)
            if not data:
                return f"Match {match_id} not found", 404

            player_scores = parse_match_data(data)
            insert_scores(match_id, player_scores)

            message = f"✅ Match {match_id} inserted successfully!"

            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(["Player", "Beatmap ID", "Score"])  # header

            for player, beatmaps in player_scores.items():
                for beatmap_id, score in beatmaps.items():
                    writer.writerow([player, beatmap_id, score])

            csv_text = output.getvalue()
            output.close()

    return render_template("index.html")

def extract_match_id(input_text):
    """
    Extract numeric match IDs from pasted text or URLs.
    Example URL: https://osu.ppy.sh/community/matches/117428039
    """
    matches = re.findall(r'(\d+)', input_text)
    return [int(m) for m in matches]

@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")

@app.route("/process", methods=["POST"])
def process():
    text_input = request.form.get("match_input")
    if not text_input:
        return "⚠️ Please enter at least one match ID or URL.", 400

    match_ids = extract_match_id(text_input)
    if not match_ids:
        return "⚠️ No valid match IDs found.", 400

    token = get_osu_token()
    if not token:
        return "❌ Failed to get osu! token.", 500

    all_player_scores = {}
    for match_id in match_ids:
        data = get_match_data(match_id, token)
        if not data:
            continue
        player_scores = parse_match_data(data)
        insert_scores(match_id, player_scores)
        all_player_scores[match_id] = player_scores

    if not all_player_scores:
        return "⚠️ No valid match data fetched.", 404

    # Prepare CSV for download
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Match ID", "Player", "Beatmap ID", "Score"])
    for match_id, scores in all_player_scores.items():
        for player, beatmaps in scores.items():
            for beatmap_id, score in beatmaps.items():
                writer.writerow([match_id, player, beatmap_id, score])
    output.seek(0)

    # Render preview table + download button
    return render_template("preview.html", all_player_scores=all_player_scores, csv_data=output.getvalue())

@app.route("/download_csv", methods=["POST"])
def download_csv():
    csv_data = request.form.get("csv_data")
    if not csv_data:
        return "⚠️ No CSV data available.", 400

    return send_file(
        io.BytesIO(csv_data.encode()),
        mimetype="text/csv",
        as_attachment=True,
        download_name="osu_matches.csv"
    )

if __name__ == "__main__":
    # Ensure Flask listens on all interfaces for Render
    app.run(host="0.0.0.0", port=PORT)
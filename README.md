## osu! Match Hub

A simple tool to fetch osu! match data and store scores in a database. You can either use the hosted website or run it locally.

## 1️⃣ Using the Website (Recommended)

Open the website: [Your Web App URL]

Paste your match ID or match URL into the input field.

Click the Fetch & Store button.

Once the data is processed, you can:

Copy CSV and paste it into Google Sheets

Download Google Sheet / CSV directly

For Google Sheets, follow this guide:

Open Google Sheets → File → Import → Paste the copied CSV data

✅ No coding required. Perfect for players who just want the results.

## 2️⃣ Running Locally (Optional)

If you want to run the code yourself, follow these steps:

### Step 1 — Clone the repository
git clone https://github.com/yourusername/osuMatchHub.git
cd osuMatchHub

### Step 2 — Set up Python environment

Make sure you have Python 3.10+ installed

Create a virtual environment:

python -m venv .venv


Activate it:

Windows: .venv\Scripts\activate

macOS/Linux: source .venv/bin/activate

Install required packages:

pip install -r requirements.txt

### Step 3 — Configure osu! API credentials

Copy the template:

cp config_template.json config.json


Open config.json and fill in your osu! Client ID and Client Secret (get them from osu! developer portal
)

### Step 4 — Set up local environment variables

Copy the template:

cp config_template.env .env


Open .env and fill in your keys:

OSU_CLIENT_ID=your_client_id
OSU_CLIENT_SECRET=your_client_secret

#Optional: local database config
DB_NAME=osu_data
DB_USER=postgres
DB_PASSWORD=     # your local Postgres password
DB_HOST=localhost
DB_PORT=5432

### Step 5 — Run the script
python osuMatchHub.py


Enter the match ID when prompted

The script will fetch scores and store them in your local database

### Step 6 — Accessing results

You can now export data to CSV or copy it into Google Sheets

Follow the same instructions as the website guide for importing into Sheets

### Notes

.env and config.json contain sensitive information — do not share them publicly

For first-time users, the local database will be created automatically by the script

The web interface is much easier if you don’t want to deal with Python

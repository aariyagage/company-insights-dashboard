from flask import Flask, request, jsonify
from flask_cors import CORS
import google.generativeai as genai
import requests
from pytrends.request import TrendReq
import yfinance as yf
import matplotlib
matplotlib.use('Agg')  # Must come BEFORE importing pyplot
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import io
import base64

# Initialize Flask App
app = Flask(__name__)
CORS(app)

# Configure Gemini API Key
genai.configure(api_key="AIzaSyC_iMBCD5PDqeTZvv2Qm1qc9oFwcTwHEKw")
NEWS_API_KEY = "707c0ead1b304b5ca2fe4cdb0b251cdb"

# Debug: Check available models
available_models = genai.list_models()
print("Available Models:", [model.name for model in available_models])

MODEL_NAME = "models/gemini-2.0-flash"


@app.route('/api/news', methods=['POST'])
def get_news():
    data = request.get_json()
    company = data.get("company", "")
    if not company:
        return jsonify({"error": "Company name is required"}), 400

    url = f"https://newsapi.org/v2/everything?q={company}&apiKey={NEWS_API_KEY}&language=en&pageSize=5"

    try:
        response = requests.get(url)
        news_data = response.json()

        if news_data.get("status") != "ok":
            return jsonify({"error": "Failed to fetch news"}), 500

        headlines = [article["title"] for article in news_data["articles"][:5]]
        return jsonify({"headlines": headlines})

    except Exception as e:
        return jsonify({"error": f"Error fetching news: {str(e)}"}), 500


@app.route('/api/sentiment', methods=['POST'])
def analyze_sentiment():
    data = request.get_json()
    text = data.get("text", "")
    print(f"Analyzing sentiment for: {text}")

    try:
        model = genai.GenerativeModel(MODEL_NAME)
        response = model.generate_content(f"Is this news positive, neutral, or negative? Respond with just one word. News: '{text}'")
        print("Gemini API Response:", response)
        sentiment = response.text.strip()
        return jsonify({"sentiment": sentiment})
    except Exception as e:
        print("Error calling Gemini API:", str(e))
        return jsonify({"error": "Failed to process request"}), 500


@app.route('/api/compare', methods=['POST'])
def competitor_comparison():
    data = request.get_json()
    keywords = data.get("keywords", ["Netflix", "Disney+", "Hulu"])
    tickers = data.get("tickers", ["NFLX", "DIS", "CMCSA"])

    try:
        # Google Trends
        pytrends = TrendReq()
        pytrends.build_payload(kw_list=keywords, timeframe='now 7-d')
        trends = pytrends.interest_over_time()

        # Stock Data
        end = datetime.today()
        start = end - timedelta(days=30)
        stocks = yf.download(tickers, start=start, end=end)['Close']

        # Save Google Trends graph
        trends[keywords].plot(title="Google Trends: Interest Over Time", figsize=(10, 4))
        plt.tight_layout()
        plt.savefig("trends.png")
        plt.close()

        # Save Stock Price graph
        stocks.plot(title="Stock Prices Over Last 30 Days", figsize=(10, 4))
        plt.tight_layout()
        plt.savefig("stocks.png")
        plt.close()

        # Executive Summary via Gemini
        model = genai.GenerativeModel(MODEL_NAME)
        company_names = ", ".join(keywords)
        prompt = f"""
        Generate an executive summary comparing public interest and stock performance of {company_names} over the last 7–30 days.

        Use the following context:
        - Google Trends data reflects public interest over the last 7 days.
        - Stock price data shows performance over the last 30 days.

        Structure it like a professional market insights summary.
        """
        response = model.generate_content(prompt)
        summary = response.text.strip()

        return jsonify({
            "message": "Graphs saved as 'trends.png' and 'stocks.png' in backend folder.",
            "executive_summary": summary
        })

    except Exception as e:
        print("Error:", e)
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True)

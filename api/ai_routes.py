from flask import request, jsonify
import pandas as pd
from api import ai_bp
from modules.ai_engine import ask_groq
from modules.prompt_builder import build_prompt

CURRENT_FILE = "cleaned_data/cleaned_sample.csv"  # dynamic later


@ai_bp.route('/ask', methods=['POST'])
def ask_ai():
    data = request.json
    query = data.get("query")

    try:
        df = pd.read_csv(CURRENT_FILE)
    except:
        return jsonify({"error": "No dataset found"}), 400

    prompt = build_prompt(query, df.columns.tolist(), df.head().to_string())

    response = ask_groq(prompt)

    return jsonify({
        "query": query,
        "response": response
    })
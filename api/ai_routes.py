from flask import request, jsonify, session
import pandas as pd
from api import ai_bp
from modules.ai_engine import ask_groq
from modules.prompt_builder import build_prompt


@ai_bp.route('/ask', methods=['POST'])
def ask_ai():
    data = request.json
    query = data.get("query")

    current_file = session.get('cleaned_raw_dataset', 'cleaned_data/cleaned_sample.csv')

    try:
        df = pd.read_csv(current_file)
    except:
        return jsonify({"error": "No dataset found"}), 400

    prompt = build_prompt(query, df.columns.tolist(), df.head().to_string())

    response = ask_groq(prompt)

    return jsonify({
        "query": query,
        "response": response
    })
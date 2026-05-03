def build_prompt(user_query, columns, data_profile, rule_based_result=None):
    context = f"""
DATASET PROFILE:
Columns: {', '.join(columns)}

{data_profile}"""
    
    if rule_based_result:
        context += f"\n\nDIRECT CALCULATION RESULT (Highly Accurate): {rule_based_result}"
    
    return f"""
You are a professional data analyst. Answer this question in a natural, conversational way like you're explaining to a colleague.

{context}

Question: {user_query}

Provide a clear, direct answer incorporating the actual numbers from the FULL dataset. Write naturally without bullet points or artificial formatting.
"""
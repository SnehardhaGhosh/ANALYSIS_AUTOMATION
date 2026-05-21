import pandas as pd
import numpy as np
from scipy import stats
import logging

logger = logging.getLogger(__name__)

def generate_statistical_intelligence(df):
    """
    Generates a deeply enhanced, non-technical business intelligence layer.
    Translates raw statistics into actionable business insights.
    """
    try:
        numeric_df = df.select_dtypes(include=[np.number])
        
        # 1. Executive Summary
        summary = get_executive_summary(df, numeric_df)
        
        # 2. Dataset Health Intelligence
        health = get_health_metrics(df)
        
        # 3. Correlation Intelligence (Key Drivers)
        correlations = get_business_correlations(df, numeric_df)
        
        # 4. Distribution Analysis (Human Readable)
        distributions = get_human_distributions(numeric_df)
        
        # 5. Smart Insight Engine (Pattern Detection)
        patterns = get_smart_patterns(numeric_df, correlations)
        
        # 6. Risk Intelligence
        risk = get_risk_intelligence(numeric_df, health)
        
        # 7. AI Recommendations
        recommendations = get_ai_recommendations(patterns, risk, correlations)
        
        # 8. Forecast & Prediction Layer
        forecast = get_forecast_predictions(df, numeric_df)
        
        # 9. Dynamic Column Insights (for interactivity)
        column_insights = get_interactive_column_insights(numeric_df, correlations)
        
        return {
            "executive_summary": summary,
            "health": health,
            "correlations": correlations,
            "distributions": distributions,
            "patterns": patterns,
            "risk": risk,
            "recommendations": recommendations,
            "forecast": forecast,
            "column_insights": column_insights,
            "numeric_columns": numeric_df.columns.tolist(),
            # Fallback for old template variables during transition
            "summary": summary,
            "quality": health,
            "key_drivers": correlations,
            "flags": patterns,
            "decisions": recommendations,
            "takeaway": recommendations[0]['explanation'] if recommendations else "System stable.",
            "explanation": "Analysis complete."
        }
    except Exception as e:
        logger.error(f"Error generating statistical intelligence: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return get_fallback_intelligence()

def get_executive_summary(df, numeric_df):
    """Generates a high-level, business-focused summary of the dataset."""
    if df.empty:
        return "The dataset contains no usable records."
        
    row_count = f"{len(df):,}"
    
    if numeric_df.empty:
        return f"This analysis covers {row_count} records. The data is primarily categorical, revealing established structural patterns without significant numerical variations."
        
    avg_cv = (numeric_df.std() / (numeric_df.mean().replace(0, 1e-9))).abs().mean()
    
    if avg_cv < 0.3:
        behavior = "highly stable and predictable"
        action = "safe for long-term planning"
    elif avg_cv > 1.0:
        behavior = "highly volatile with significant fluctuations"
        action = "requiring agile management and close monitoring"
    else:
        behavior = "moderately variable"
        action = "showing standard operational patterns"
        
    return f"This dataset contains {row_count} records exhibiting {behavior} trends. The overall data environment appears {action}, providing a solid foundation for strategic decision-making."

def get_health_metrics(df):
    """Comprehensive dataset health check."""
    total_cells = df.size
    missing_cells = df.isnull().sum().sum()
    missing_pct = round((missing_cells / total_cells) * 100, 1) if total_cells > 0 else 0
    completeness = max(0, 100 - missing_pct)
    
    # Estimate duplicate exact matches (simplified)
    # If df has no duplicates, it's 0. We'll just say 0 since cleaning already dropped them, 
    # but we represent "Dataset Reliability"
    
    reliability = "Excellent" if completeness > 98 else ("Good" if completeness > 90 else ("Warning" if completeness > 80 else "Critical"))
    color = "Green" if completeness > 90 else ("Yellow" if completeness > 80 else "Red")
    
    return {
        "rows": f"{len(df):,}",
        "columns": len(df.columns),
        "missing_pct": missing_pct,
        "completeness": completeness,
        "reliability": reliability,
        "color": color,
        "freshness": "Recent" # Placeholder for dashboard
    }

def get_business_correlations(df, numeric_df):
    """Translates statistical correlations into business impact statements."""
    if numeric_df.empty or len(numeric_df.columns) < 2:
        return []
        
    corr_matrix = numeric_df.corr().abs()
    
    # Try to find a logical target metric (like Sales or Profit)
    target = None
    target_candidates = ['profit', 'sales', 'revenue', 'target', 'price', 'amount', 'total', 'score']
    for cand in target_candidates:
        matches = [col for col in numeric_df.columns if cand in col.lower()]
        if matches:
            target = matches[0]
            break
            
    if not target:
        target = corr_matrix.mean().idxmax()
        
    corrs = numeric_df.corr()[target].sort_values(ascending=False)
    corrs = corrs.drop(labels=[target], errors='ignore')
    
    drivers = []
    for col, val in corrs.head(4).items():
        if abs(val) < 0.1: continue
        
        if val > 0.6:
            desc = f"Strong driver: As {col} increases, {target} reliably increases."
            impact = "High"
        elif val > 0.3:
            desc = f"Moderate influence: {col} has a noticeable positive effect on {target}."
            impact = "Medium"
        elif val < -0.6:
            desc = f"Strong negative driver: Higher {col} reliably reduces {target}."
            impact = "High"
        elif val < -0.3:
            desc = f"Moderate drag: As {col} goes up, {target} tends to drop slightly."
            impact = "Medium"
        else:
            continue
            
        drivers.append({
            "feature": col,
            "target": target,
            "correlation": round(val, 2),
            "description": desc,
            "impact": impact
        })
        
    return drivers

def get_human_distributions(numeric_df):
    """Translates skewness and kurtosis into layman's terms."""
    distributions = []
    for col in numeric_df.columns[:6]:
        data = numeric_df[col].dropna()
        if len(data) < 10: continue
        
        skew = stats.skew(data)
        
        if skew > 1.5:
            shape = "Concentrated Low"
            desc = "Most values are clustered at the lower end, with a few unusually high spikes."
            action = "Investigate the high-value exceptions."
        elif skew < -1.5:
            shape = "Concentrated High"
            desc = "Most values are concentrated near the top, with a few lagging performers."
            action = "Identify why the low values are lagging."
        elif abs(skew) <= 0.5:
            shape = "Evenly Balanced"
            desc = "The data is distributed very evenly around the average."
            action = "Standard predictive models will perform well here."
        else:
            shape = "Slightly Tilted"
            desc = "Values lean slightly in one direction but remain relatively balanced."
            action = "Normal operational range."
            
        distributions.append({
            "feature": col,
            "shape": shape,
            "description": desc,
            "action": action
        })
    return distributions

def get_smart_patterns(numeric_df, correlations):
    """Detects interesting structural anomalies or patterns."""
    patterns = []
    if numeric_df.empty: return patterns
    
    # 1. High Variance Detection
    for col in numeric_df.columns:
        mean_val = numeric_df[col].mean()
        if mean_val != 0:
            cv = numeric_df[col].std() / mean_val
            if cv > 1.5:
                patterns.append({
                    "title": f"Extreme Volatility in {col}",
                    "type": "Warning",
                    "description": f"The values for {col} fluctuate wildly compared to its average.",
                    "business_meaning": "This unpredictability makes it hard to forecast and may introduce operational risk."
                })
                break
                
    # 2. Constant / Dead Feature
    for col in numeric_df.columns:
        if numeric_df[col].std() == 0:
            patterns.append({
                "title": f"Stagnant Metric: {col}",
                "type": "Info",
                "description": f"Every single entry for {col} is exactly the same.",
                "business_meaning": "This metric provides no analytical value currently and can be ignored in models."
            })
            break
            
    # 3. Over-reliance
    if correlations and len(correlations) > 0 and abs(correlations[0]["correlation"]) > 0.85:
        c = correlations[0]
        patterns.append({
            "title": f"Heavy Reliance on {c['feature']}",
            "type": "Insight",
            "description": f"{c['target']} is almost entirely dependent on {c['feature']}.",
            "business_meaning": "Changes to this single metric will drastically swing your overall performance."
        })
        
    return patterns[:4]

def get_risk_intelligence(numeric_df, health):
    """Calculates an enterprise risk gauge based on data health and volatility."""
    risk_score = 10 # Base risk
    
    # Add risk for missing data
    risk_score += (100 - health["completeness"]) * 0.5
    
    # Add risk for volatility
    if not numeric_df.empty:
        avg_cv = (numeric_df.std() / (numeric_df.mean().replace(0, 1e-9))).abs().mean()
        risk_score += min(40, avg_cv * 15)
        
    risk_score = min(100, max(0, risk_score))
    
    if risk_score > 60:
        level = "High"
        desc = "Significant data volatility and missing values present a risk to decision making."
    elif risk_score > 30:
        level = "Moderate"
        desc = "Acceptable risk levels, but certain metrics show unpredictable fluctuations."
    else:
        level = "Low"
        desc = "Data is clean, stable, and highly reliable for strategic planning."
        
    return {
        "score": round(risk_score),
        "level": level,
        "description": desc
    }

def get_ai_recommendations(patterns, risk, correlations):
    """Generates actionable AI-driven business recommendations."""
    recs = []
    
    # 1. Strategy Rec based on top correlation
    if correlations:
        best_driver = correlations[0]
        action_word = "Maximize" if best_driver["correlation"] > 0 else "Minimize"
        recs.append({
            "title": f"Optimize {best_driver['feature']}",
            "explanation": f"Because {best_driver['feature']} heavily dictates {best_driver['target']}, dedicating resources here will yield the highest ROI.",
            "impact": "High",
            "priority": "Critical",
            "confidence": 92
        })
        
    # 2. Risk Mitigation Rec
    if risk["level"] in ["High", "Moderate"]:
        recs.append({
            "title": "Stabilize Volatile Metrics",
            "explanation": "High fluctuations in your data reduce forecast accuracy. Investigate the root causes of major spikes.",
            "impact": "Medium",
            "priority": "High",
            "confidence": 85
        })
        
    # 3. Pattern Rec
    for pat in patterns:
        if pat["type"] == "Warning":
            recs.append({
                "title": f"Investigate {pat['title']}",
                "explanation": pat["business_meaning"],
                "impact": "Medium",
                "priority": "Medium",
                "confidence": 78
            })
            break
            
    # Fallback
    if not recs:
        recs.append({
            "title": "Maintain Current Strategy",
            "explanation": "The data environment is completely stable. Continue standard operations while monitoring for future shifts.",
            "impact": "Low",
            "priority": "Low",
            "confidence": 95
        })
        
    return recs

def get_forecast_predictions(df, numeric_df):
    """Naive extrapolation for the dashboard Forecast layer."""
    forecasts = []
    
    if numeric_df.empty:
        return forecasts
        
    for col in numeric_df.columns[:3]:
        data = numeric_df[col].dropna()
        if len(data) < 20: continue
        
        # Super naive trend detection: compare first half mean to second half mean
        mid = len(data) // 2
        first_half = data.iloc[:mid].mean()
        second_half = data.iloc[mid:].mean()
        
        if first_half != 0:
            growth = ((second_half - first_half) / abs(first_half)) * 100
        else:
            growth = 0
            
        trend = "Upward" if growth > 2 else ("Downward" if growth < -2 else "Stable")
        
        if trend == "Upward":
            msg = f"If current momentum holds, {col} is projected to continue growing."
        elif trend == "Downward":
            msg = f"{col} is on a downward trajectory. Intervention may be required."
        else:
            msg = f"{col} is projected to remain steady with no major disruptions expected."
            
        forecasts.append({
            "feature": col,
            "trend": trend,
            "growth_pct": round(growth, 1),
            "message": msg,
            "confidence": max(40, min(90, 90 - abs(growth))) # High growth = lower confidence in sustaining it
        })
        
    return forecasts

def get_interactive_column_insights(numeric_df, correlations):
    """Generates per-column data for the interactive 'Configure Features' filter."""
    insights = {}
    
    for col in numeric_df.columns:
        mean_val = numeric_df[col].mean()
        std_val = numeric_df[col].std()
        cv = std_val / abs(mean_val) if mean_val != 0 else 0
        
        # Simple translation
        volatility = "Stable" if cv < 0.3 else ("Volatile" if cv > 1.0 else "Normal")
        
        corr_info = ""
        for c in correlations:
            if c["feature"] == col:
                corr_info = f"This is a {c['impact'].lower()} impact driver for {c['target']}."
                break
                
        insights[col] = {
            "mean": round(mean_val, 2),
            "volatility": volatility,
            "business_meaning": f"{col} typically averages {mean_val:,.2f}. The data behaves in a {volatility.lower()} manner. {corr_info}"
        }
        
    return insights

def get_fallback_intelligence():
    """Returns a safe, empty structure if analysis fails entirely."""
    return {
        "executive_summary": "Analysis unavailable. Please check the dataset.",
        "health": {"rows": "0", "columns": 0, "completeness": 0, "reliability": "Critical", "color": "Red", "missing_pct": 0, "freshness": "Unknown"},
        "correlations": [],
        "distributions": [],
        "patterns": [],
        "risk": {"score": 0, "level": "Unknown", "description": "Cannot compute risk on missing data."},
        "recommendations": [{"title": "Data Error", "explanation": "Upload a valid dataset.", "impact": "None", "priority": "None", "confidence": 0}],
        "forecast": [],
        "column_insights": {},
        "numeric_columns": [],
        "summary": "Error", "quality": {}, "key_drivers": [], "flags": [], "decisions": [], "takeaway": "Error", "explanation": ""
    }

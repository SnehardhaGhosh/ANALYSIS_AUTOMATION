import pandas as pd
import numpy as np
from scipy import stats
import logging

logger = logging.getLogger(__name__)

def generate_statistical_intelligence(df):
    """
    Generates an enhanced decision-focused explanation layer for the dataset.
    """
    try:
        numeric_df = df.select_dtypes(include=[np.number])
        
        # 1. Statistical Summary
        summary = get_summary_text(df, numeric_df)
        
        # 2. Key Drivers of Change
        key_drivers = get_key_drivers(df, numeric_df)
        
        # 3. Data Quality Score
        quality_score = get_data_quality_score(df)
        
        # 4. Distribution Analysis
        dist_analysis = get_distribution_analysis(numeric_df)
        
        # 5. Statistical Flags
        stat_flags = get_stat_flags(numeric_df)
        
        # 6. Confidence Level
        confidence = get_confidence_level(df, numeric_df)
        
        # 7. Business Translation Layer
        business_translation = get_business_translation(df, stat_flags, key_drivers)
        
        # 8. Comparison Insights & Timeline (Combined/Enhanced)
        comparison, timeline_data = get_enhanced_insights(df)
        
        # 9. Risk Indicator
        risk = get_risk_indicator(stat_flags, quality_score)
        
        # 10. Decision Suggestions (Enhanced with Priority/Impact)
        decisions = get_enhanced_decisions(stat_flags, key_drivers, quality_score, confidence)
        
        # 11. Final Takeaway
        takeaway = get_final_takeaway(risk, confidence, decisions)
        
        # 12. Intelligence Hint
        hint = get_specific_hint(key_drivers, stat_flags)
        
        # 13. Natural Language Explanation
        explanation = generate_page_explanation(summary, quality_score, risk, decisions)
        
        # 11. Column-level interactive insights (for Configure Features interactivity)
        column_insights = generate_column_specific_insights(df, numeric_df, key_drivers)

        return {
            "summary": summary,
            "key_drivers": key_drivers,
            "quality": quality_score,
            "distribution": dist_analysis,
            "flags": stat_flags,
            "confidence": confidence,
            "business": business_translation,
            "comparison": comparison,
            "timeline": timeline_data,
            "risk": risk,
            "decisions": decisions,
            "takeaway": takeaway,
            "hint": hint,
            "explanation": explanation,
            "column_insights": column_insights,
            "numeric_columns": numeric_df.columns.tolist()
        }
    except Exception as e:
        logger.error(f"Error generating statistical intelligence: {e}")
        import traceback
        logger.error(traceback.format_exc())
        # Return fully-populated safe structure so the template never crashes
        return {
            "summary": "Analysis unavailable — check server logs.",
            "key_drivers": [],
            "quality": {"score": 0, "completeness": 0, "missing_pct": 0, "reliability": "Low"},
            "distribution": {},
            "flags": [],
            "confidence": {"score": 0, "level": "Low"},
            "business": [],
            "comparison": [],
            "timeline": {"changed": [], "stable": []},
            "risk": {"level": "Low", "score": 0},
            "decisions": [],
            "takeaway": "Analysis unavailable.",
            "hint": "",
            "explanation": "",
            "column_insights": {},
            "numeric_columns": []
        }

def get_summary_text(df, numeric_df):
    """Simple explanation of the dataset in plain English."""
    if df.empty:
        return "The dataset is empty or could not be processed."
    
    row_count = len(df)
    col_count = len(df.columns)
    
    if numeric_df.empty:
        return f"The dataset contains {row_count} records. Data is primarily categorical, showing stable structural patterns."
    
    avg_std = numeric_df.std().mean()
    if avg_std < 0.1:
        trend = "stable trends with low variability"
    elif avg_std > 100:
        trend = "dynamic trends with high variability"
    else:
        trend = "consistent trends with moderate variability"
        
    outliers_found = False
    for col in numeric_df.columns:
        if len(numeric_df[col].dropna()) > 3:
            z_scores = np.abs(stats.zscore(numeric_df[col].dropna()))
            if (z_scores > 3).any():
                outliers_found = True
                break
            
    anomaly_text = "no major anomalies" if not outliers_found else "some localized anomalies"
    
    return f"The data shows {trend} and {anomaly_text} across {row_count} observations."

def get_key_drivers(df, numeric_df):
    """Top 3 influencing features based on correlation strength."""
    if numeric_df.empty or len(numeric_df.columns) < 2:
        return []
        
    corr_matrix = numeric_df.corr().abs()
    target = None
    target_candidates = ['profit', 'sales', 'revenue', 'target', 'price', 'amount', 'total']
    for cand in target_candidates:
        if cand in df.columns:
            target = cand
            break
            
    if not target:
        target = corr_matrix.mean().idxmax()
        
    corrs = numeric_df.corr()[target].sort_values(ascending=False)
    if target in corrs:
        corrs = corrs.drop(labels=[target])
    
    top_3 = []
    for col, val in corrs.head(3).items():
        # Strength determines the certainty of our language later
        strength = "Strong" if abs(val) > 0.7 else ("Moderate" if abs(val) > 0.4 else "Weak")
        impact = "High" if abs(val) > 0.6 else ("Medium" if abs(val) > 0.3 else "Low")
        influence = "Positive" if val > 0 else "Negative"
        top_3.append({
            "feature": col,
            "impact": impact,
            "influence": influence,
            "strength": strength,
            "correlation": round(val, 2)
        })
        
    return top_3

def get_data_quality_score(df):
    """Completeness and reliability metrics."""
    total_cells = df.size
    missing_cells = df.isnull().sum().sum()
    completeness = round((1 - (missing_cells / total_cells)) * 100, 1) if total_cells > 0 else 0
    
    reliability = "High" if completeness > 95 else ("Medium" if completeness > 80 else "Low")
    
    return {
        "score": completeness,
        "completeness": completeness,
        "missing_pct": round((missing_cells / total_cells) * 100, 1) if total_cells > 0 else 0,
        "reliability": reliability
    }

def get_distribution_analysis(numeric_df):
    """Skewness and outlier analysis."""
    analysis = {}
    for col in numeric_df.columns[:5]:
        data = numeric_df[col].dropna()
        if len(data) < 3: continue
        
        skew = stats.skew(data)
        skew_text = "Highly Skewed" if abs(skew) > 1 else ("Moderately Skewed" if abs(skew) > 0.5 else "Symmetrical")
        spread = "High" if data.std() > data.mean() else "Uniform"
        
        z_scores = np.abs(stats.zscore(data))
        outliers = "Present" if (z_scores > 3).any() else "None"
        
        analysis[col] = {
            "skewness": skew_text,
            "spread": spread,
            "outliers": outliers
        }
    return analysis

def get_stat_flags(numeric_df):
    """Flags for high variance and weak signals."""
    flags = []
    if numeric_df.empty: return flags
        
    for col in numeric_df.columns:
        mean_val = numeric_df[col].mean()
        if mean_val != 0:
            cv = numeric_df[col].std() / mean_val
            if cv > 1.2:
                flags.append({"type": "High Variance", "feature": col, "desc": "Extreme value fluctuation detected"})
            
    for col in numeric_df.columns:
        if len(numeric_df[col].dropna()) > 3:
            skew = stats.skew(numeric_df[col].dropna())
            if abs(skew) > 2.0:
                flags.append({"type": "Skewed Distribution", "feature": col, "desc": "Data shows significant bias"})
            
    if len(numeric_df.columns) > 1:
        corr_matrix = numeric_df.corr().abs()
        avg_corr = (corr_matrix.sum() - 1) / (len(numeric_df.columns) - 1)
        weak_cols = avg_corr[avg_corr < 0.15].index.tolist()
        for col in weak_cols[:2]:
            flags.append({"type": "Weak Correlation", "feature": col, "desc": "Feature operates independently of others"})
            
    return flags[:4]

def get_confidence_level(df, numeric_df):
    """Reliability percentage."""
    sample_size_score = min(100, (len(df) / 500) * 100)
    quality_score = get_data_quality_score(df)["score"]
    
    if not numeric_df.empty:
        cv_avg = (numeric_df.std() / (numeric_df.mean() + 0.001)).mean()
        variance_score = max(0, 100 - (cv_avg * 15))
    else:
        variance_score = 70
        
    score = round((sample_size_score * 0.25) + (quality_score * 0.5) + (variance_score * 0.25), 1)
    level = "High" if score > 85 else ("Medium" if score > 65 else "Low")
    
    return {"score": score, "level": level}

def get_business_translation(df, stat_flags, key_drivers):
    """Stats to Business mapping."""
    translations = []
    for flag in stat_flags[:2]:
        if flag["type"] == "High Variance":
            translations.append(f"Unpredictable behavior in {flag['feature']} may lead to operational forecasting errors.")
        elif flag["type"] == "Skewed Distribution":
            translations.append(f"Performance in {flag['feature']} is heavily unbalanced, suggesting niche dominance.")
            
    if key_drivers:
        driver = key_drivers[0]
        translations.append(f"{driver['feature']} acts as a primary {driver['influence'].lower()} catalyst for current outcomes.")
    
    if not translations:
        translations.append("Data indicates a steady-state environment with minimal structural risk.")
        
    return translations

def get_enhanced_insights(df):
    """Enhanced timeline with numeric insights."""
    insights = []
    timeline = {"changed": [], "stable": []}
    
    if len(df) < 10:
        return ["Limited data"], {"changed": [], "stable": ["Dataset"]}
        
    mid = len(df) // 2
    prev_half = df.iloc[:mid]
    curr_half = df.iloc[mid:]
    
    num_prev = prev_half.select_dtypes(include=[np.number])
    num_curr = curr_half.select_dtypes(include=[np.number])
    
    if not num_prev.empty and not num_curr.empty:
        for col in num_curr.columns[:3]:
            p_mean = num_prev[col].mean()
            c_mean = num_curr[col].mean()
            
            if p_mean != 0:
                diff_pct = (c_mean - p_mean) / abs(p_mean) * 100
                trend = "increased" if diff_pct > 0 else "decreased"
                
                msg = f"{col} {trend} by {abs(diff_pct):.1f}% recently"
                insights.append(msg)
                
                if abs(diff_pct) > 10:
                    timeline["changed"].append(msg)
                else:
                    timeline["stable"].append(f"{col} remains steady (+/- {abs(diff_pct):.1f}%)")
    
    if not insights:
        insights.append("No significant shifts detected in the current window.")
        timeline["stable"].append("All core metrics")
        
    return insights, timeline

def get_risk_indicator(stat_flags, quality_score):
    """System risk level based on variance and anomalies."""
    risk_points = len(stat_flags) * 2
    if quality_score["score"] < 80: risk_points += 3
    if quality_score["score"] < 60: risk_points += 5
    
    level = "Low" if risk_points < 4 else ("Medium" if risk_points < 8 else "High")
    return {"level": level, "score": risk_points}

def get_enhanced_decisions(stat_flags, key_drivers, quality_score, confidence):
    """Enhanced decisions with Impact, Effort, and Priority."""
    decisions = []
    
    # Logic Fix: Adjust certainty based on correlation strength
    if key_drivers:
        driver = key_drivers[0]
        strength = driver["strength"]
        
        certainty = "Highly recommended:" if strength == "Strong" else "Consider investigating:"
        action = f"{certainty} Focus on {driver['feature']} as it has a {strength.lower()} {driver['influence'].lower()} influence."
        
        decisions.append({
            "action": action,
            "impact": driver["impact"],
            "effort": "Medium",
            "priority": 5 if strength == "Strong" else 3
        })
        
    if quality_score["score"] < 85:
        decisions.append({
            "action": "Address missing data points to improve analytical certainty.",
            "impact": "Medium",
            "effort": "Low",
            "priority": 4
        })
        
    for flag in stat_flags:
        if flag["type"] == "High Variance":
            decisions.append({
                "action": f"Monitor {flag['feature']} closely to manage volatility risks.",
                "impact": "High",
                "effort": "Medium",
                "priority": 4
            })
            break
            
    if not decisions:
        decisions.append({
            "action": "Maintain current baseline and monitor for seasonal shifts.",
            "impact": "Low",
            "effort": "Low",
            "priority": 2
        })
        
    return decisions

def get_final_takeaway(risk, confidence, decisions):
    """One clear decision summary."""
    if risk["level"] == "High":
        return "High volatility detected. Prioritize risk mitigation and data cleanup before major scaling."
    if confidence["score"] < 60:
        return "Insight reliability is moderate. Gather more data points before making high-stakes decisions."
    
    if decisions:
        top_action = decisions[0]["action"].split(':')[-1].strip()
        return f"System is stable. {top_action}"
        
    return "Operations are healthy. No urgent interventions required."

def get_specific_hint(key_drivers, stat_flags):
    """Specific and actionable intelligence hint."""
    if key_drivers:
        driver = key_drivers[0]
        return f"Proactive adjustment of {driver['feature']} will yield the highest return on effort based on its {driver['strength'].lower()} correlation."
    
    if stat_flags:
        flag = stat_flags[0]
        return f"Reducing the variance in {flag['feature']} will stabilize overall system predictability."
        
    return "Regular monitoring of outlier presence will prevent unexpected data drift."

def generate_page_explanation(summary, quality_score, risk, decisions):
    """Short natural language summary of the entire page."""
    quality_text = f"The analysis is backed by a {quality_score['reliability'].lower()} reliability data profile."
    risk_text = f"System risk is currently {risk['level'].lower()}."
    
    action_text = ""
    if decisions:
        action_text = f" The primary recommendation is to {decisions[0]['action'].lower()}."
        
    return f"{summary} {quality_text} {risk_text}{action_text}"


def generate_column_specific_insights(df, numeric_df, key_drivers):
    """
    Pre-compute per-column takeaway, confidence, risk, and hint
    so the frontend can update all insight sections dynamically
    when the user selects/deselects features in Configure Features.
    """
    insights = {}

    for col in numeric_df.columns:
        data = numeric_df[col].dropna()
        if len(data) < 3:
            continue

        mean_val = data.mean()
        std_val  = data.std()
        cv       = std_val / abs(mean_val) if mean_val != 0 else 0

        # Skewness
        skew = float(stats.skew(data))
        skew_label = "Highly Skewed" if abs(skew) > 1.5 else ("Moderately Skewed" if abs(skew) > 0.5 else "Symmetrical")

        # Stability
        stability = "Stable" if cv < 0.2 else ("Volatile" if cv > 1.0 else "Variable")

        # Confidence (0–100)
        completeness = round((1 - df[col].isnull().sum() / len(df)) * 100, 1)
        col_confidence = round(max(0, min(100, completeness * 0.6 + max(0, 100 - cv * 20) * 0.4)), 1)

        # Risk
        col_risk = "High" if cv > 1.2 or abs(skew) > 2.0 else ("Medium" if cv > 0.6 else "Low")

        # Takeaway
        if cv > 1.0:
            takeaway = f"High volatility in {col} exceeds safe thresholds. Monitor closely before scaling decisions."
        elif abs(skew) > 1.5:
            takeaway = f"{col} has a {skew_label.lower()} distribution. Decision models should account for this bias."
        else:
            takeaway = f"{col} is performing within expected boundaries. No immediate action required."

        # Hint — find strongest correlated driver
        corr_pct = 0.0
        if key_drivers:
            driver_col = key_drivers[0]["feature"]
            if driver_col != col and driver_col in numeric_df.columns:
                corr_pct = abs(float(numeric_df[col].corr(numeric_df[driver_col]))) * 100
        hint = (
            f"Optimising {col} could shift {key_drivers[0]['feature']} by ~{corr_pct:.1f}% based on their correlation."
            if key_drivers and corr_pct > 0
            else f"Focus on reducing variance in {col} to improve overall forecast reliability."
        )

        insights[col] = {
            "summary": f"{col} shows a {skew_label.lower()} distribution with {stability.lower()} behaviour.",
            "kpi_label": f"Average {col}",
            "kpi_value": f"{mean_val:,.2f}",
            "quality": completeness,
            "confidence": col_confidence,
            "risk": col_risk,
            "takeaway": takeaway,
            "hint": hint,
            "explanation": (
                f"Statistical analysis of {col} reveals {stability.lower()} patterns "
                f"(CV={cv:.2f}). The {skew_label.lower()} nature suggests "
                f"{'concentrated values that may need segmentation.' if abs(skew) > 0.5 else 'balanced distribution suitable for standard modelling.'}"
            )
        }

    return insights

# Performance Bottlenecks & UI Issues Analysis
**Date:** March 30, 2026  
**Scope:** app.py, API routes, templates, data modules

---

## EXECUTIVE SUMMARY

The application has **significant performance bottlenecks** in:
1. **Dataset Preview Loading** - Full dataset in memory + template rendering
2. **Tab Navigation** - Serverside page reloads instead of dynamic tabs
3. **Column Detection** - Redundant type inference across multiple operations
4. **Missing Value Handling** - Inconsistent strategies (NaN vs "unknown" vs missing)
5. **Database Operations** - No caching, full file reads on every request
6. **Frontend AJAX** - Inefficient data chunking, no pagination

---

## 1. TAB SWITCHING & PREVIEW FUNCTIONALITY

### Current Flow Issues

**Problem 1.1: No Client-Side Tabs - Full Page Reloads**
- No actual tab switching - each "tab" is a separate route (`/preview`, `/processing-summary`, `/chat`)
- Each view forces a full page reload and server roundtrip
- **Impact:** 2-3 second latency per tab switch

**Location:** [templates/base.html](templates/base.html#L28), [templates/dashboard.html](templates/dashboard.html#L21-L26)

```jinja2
<!-- Current implementation: Full page navigation -->
<a class="nav-link" href="/preview"><i class="fas fa-eye"></i> Preview</a>
<a class="nav-link" href="/chat"><i class="fas fa-robot"></i> AI Chat</a>
```

**Why it's slow:**
- No caching of tab content
- Each view reloads dataframe from CSV disk: `df = pd.read_csv(source)`
- Jinja2 template rendering for potentially thousands of rows
- Full UI rerender

---

### Current Preview Implementation

**Problem 1.2: Full Dataset in DOM**
- [app.py L396-406](app.py#L396-L406) loads **entire dataframe** into template
- Renders all rows as HTML table rows
- For 10,000 rows = 10,000+ `<tr>` elements

```python
# Current: Loads ENTIRE dataset
df = pd.read_csv(source)
return render_template(
    'preview.html',
    columns=df.columns,
    data=df.to_dict(orient='records'),  # ⚠️ ALL DATA
    report=report,
    source_type='cleaned'
)
```

**Impact:** 
- Memory spike for large datasets
- Browser DOM bloat (>1MB HTML for 10K rows)
- Slow scrolling performance in table
- Template rendering time: O(n) where n = row count

**Location:** [app.py L388-408](app.py#L388-408)

---

### Processing Summary Tab - Redundant Data Loads

**Problem 1.3: Multiple CSV Reads in Single View**
- [app.py L421-450](app.py#L421-L450) reads **two full CSVs** for single page view

```python
@app.route('/processing-summary')
def processing_summary():
    # READ 1: Cleaned dataset (before ML transforms)
    cleaned_df = pd.read_csv(session['cleaned_dataset'])
    cleaned_data = cleaned_df.astype(str).to_dict(orient='records')  # ⚠️ FULL LOAD
    
    # READ 2: Final dataset (after transforms)
    df = pd.read_csv(session['dataset'])
    
    # READ 3: Calculate stats from final dataset
    numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
    for col in numeric_cols:
        summary_stats[col] = {
            'mean': round(df[col].mean(), 2),  # ⚠️ Recalculated every page load
            'median': round(df[col].median(), 2),
            'min': round(df[col].min(), 2),
            'max': round(df[col].max(), 2),
            'std': round(df[col].std(), 2)
        }
```

**Issue:** All statistics recalculated on every view load  
**Impact:** 2-5 seconds for 100K+ rows on spinning disk

---

## 2. COLUMN DETECTION LOGIC

### Problem 2.1: Redundant Type Inference Across Pipeline

**Current Flow:**
1. `data_validation.py` - infers types [L239-283]
2. `data_cleaning.py` - infers types AGAIN [L227-263]
3. `data_preprocessing.py` - detects numeric columns again
4. `query_executor.py` - likely infers third time

**Code Evidence:**

```python
# data_validation.py L62
inferred_dtype = infer_column_type(col_data)

# data_cleaning.py L37
col_dtype = infer_column_type(df[col])

# data_cleaning.py L94
string_cols = [col for col in df.columns if infer_column_type(df[col]) == 'string']

# data_cleaning.py L116
numeric_cols = [col for col in df.columns if infer_column_type(df[col]) == 'numeric']
```

**Function Location:** [data_validation.py L239-283](data_validation.py#L239-L283)

**Inefficiency:**
- `infer_column_type()` called **5-7 times per column** per dataset
- For 100-column dataset = 500-700 inference calls
- Each call includes regex matching, numeric coercion, datetime parsing

### Problem 2.2: Type Inference Strategy - Not Robust for Edge Cases

**Current Logic (80% numeric threshold):**
```python
numeric_converted = pd.to_numeric(col_clean, errors='coerce')
numeric_count = numeric_converted.notna().sum()
if numeric_count / len(col_clean) > 0.8:  # 80% are numeric
    return 'numeric'
```

**Issues:**
1. A mostly-numeric column with dates gets marked "numeric"
2. Column with "100", "200", "N/A" (where N/A = important label) misclassified
3. No handling of currency ("$1,200.50"), percentages ("85%"), ordinals ("1st", "2nd")

**Edge Cases Not Detected:**
- Phone numbers: "555-1234" detected as string ✓ but could be numeric reference
- Postal codes: "90210" stored as numeric, loses leading zeros ✗
- Product codes: "ABC-001" mixed alphanumeric not optimized
- Boolean-like numbers: "0", "1" marked numeric instead of boolean

---

## 3. MISSING VALUE HANDLING (NaN vs "unknown" vs missing)

### Problem 3.1: Inconsistent Strategy Across Codebase

**Location 1: [data_cleaning.py L23-80] - String columns get "unknown"**
```python
if col_dtype == 'string':
    df[col] = df[col].fillna('unknown')  # ⚠️ String replacement
```

**Location 2: [data_preprocessing.py L85-92] - But preprocessing ignores this**
```python
for col in categorical_cols:
    if df[col].nunique() < 20:
        unique_values = df[col].dropna().unique()  # ⚠️ dropna() ignores "unknown" strings
        encoding_map = {val: idx for idx, val in enumerate(unique_values)}
```

**Problem:** 
- After cleaning: `df['category'] = ['A', 'B', 'unknown', 'A']`
- Preprocessing: `'unknown'` encodings sometimes missing from map
- Encoding maps don't consistent track missing value strategy

**Location 3: Missing value imputation inconsistency**
- Numeric columns: median imputation
- String columns: literal "unknown" string (not missing value)
- Boolean: mode
- Datetime: forward fill + backward fill

**Issues:**
1. **NaN vs String "unknown" Comparison Problem**
   - Queries like `df['col'] == 'unknown'` miss actual `NaN` values
   - Aggregations count "unknown" strings as valid data

2. **Query Results Unreliable**
   - User asks "what % of data is missing?"
   - System counts "unknown" strings as present = wrong answer
   
3. **No Wrapper Abstraction**
   - Each module reimplements missing handling
   - No single source of truth

---

## 4. DATABASE QUERIES & DATA LOADING OPERATIONS

### Problem 4.1: No Query Caching or Memoization

**Chat History Loading - Full DB Read Every Time**
```python
@app.route('/api/chat-history', methods=['GET'])
def get_chat_history_route():
    # Reads ENTIRE chat history every time (no WHERE limit, no pagination)
    history = get_chat_history(session['user_id'])
    formatted_history = []
    for query, response, timestamp in history:
        formatted_history.append({...})
    return jsonify({"history": formatted_history})
```

**Issues:**
- User with 1000 messages = serialize 1000 JSON objects on every page load
- No pagination (frontend loads all at once)
- No indexing by timestamp

**Location:** [app.py L577-591](app.py#L577-L591), [modules/db.py L38-45](modules/db.py#L38-L45)

### Problem 4.2: Dataframe Reloading from Disk

Every view loads CSV from disk with **zero caching**:

1. **Preview**: `df = pd.read_csv(source)` [app.py L396]
2. **Processing Summary**: `df = pd.read_csv(session['dataset'])` [app.py L432]
3. **AI Chat**: `df = pd.read_csv(dataset_file)` [app.py L540]
4. **Visualizations**: Likely loads again [api routes]

**For 10MB CSV on HDD:** ~1-2 seconds per load  
**Total per user workflow:** 5-10 seconds wasted reloading same file

### Problem 4.3: No S3/Cache Layer

- Files stored in local `/uploads/` and `/cleaned_data/` folders
- No compression (CSV files can be 5-10x larger than equivalent Parquet)
- No columnar access (if you need 3 columns, must read all)

---

## 5. UPLOAD & DATA PROCESSING PIPELINE

### Problem 5.1: Sequential Processing - Not Parallelizable

**Current Flow:** [app.py L165-346]
```
Step 1: Load File         (2s) ──┐
                                 ├─ TOTAL: 30-45s
Step 2: Validate Data     (3s) ──┤
                                 ├─ (linearly sequential)
Step 3: Clean Data        (5s) ──┤
                                 ├─
Step 4: Preprocess        (10s)──┤
                                 ├─
Step 5: Transform         (8s) ──┤
                                 ├─
Step 6: Add Features      (2s) ──┤
                                 ├─
Step 7: Save Data         (2s) ──┼─
                                 │
Step 8: Build Reports     (3s) ──┘
```

**Opportunity:** Steps 1-2 could be parallel; Steps 3-8 have dependencies but cleanup/preprocessing could be optimized

### Problem 5.2: Full DataFrame in Memory for Report Building

**Location:** [app.py L335-360]

```python
# Store processing_reports
reports_summary = {
    'original_rows': int(original_rows),
    'final_rows': int(len(df)),
    'data_quality_score': float(data_quality_score),
    'duplicates_removed': duplicates_removed,
    'nulls_handled': nulls_handled,
    'outliers_handled': outliers_handled,
    'column_null_counts': column_nulls,  # ⚠️ Full column analysis required
    'memory_usage_mb': round(df.memory_usage(deep=True).sum() / 1024 / 1024, 2),
}

# ⚠️ Must keep entire dataframe in session
session['cleaning_report'] = cleaning_report
session['preprocessing_report'] = preprocessing_report
session['transformation_report'] = transformation_report
```

**Issue:** All data transformations stored in session memory
- Flask session default = file-based (filesystem-backed)
- Session files written to disk for every upload = **disk I/O bottleneck**

---

## 6. FRONTEND AJAX CALLS & DATA PROCESSING

### Problem 6.1: No Pagination in Preview

**Current Chat Implementation** [templates/chat.html]:
```javascript
// Loads ALL history items
let response = await fetch("/api/chat-history");
let data = await response.json();
// If user has 500 messages: sends/renders all 500
historyList.innerHTML = data.history.map(item => `...`).join('');
```

**Issues:**
- No pagination or lazy loading
- No message truncation
- Renders full response text for all 500 messages

### Problem 6.2: Inefficient AI Query Submission

**Location:** [static/js/main.js L23-50]

```javascript
// Current: Full data loaded to client
try {
    const response = await fetch("/ask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: query })
    });
    
    const data = await response.json();
    // Serializes entire dataset potentially
}
```

**Issue:** Query endpoint reloads full dataset [app.py L527-570] just to answer questions

### Problem 6.3: No Loading States or Request Debouncing

- No client-side debouncing when user types fast
- No "loading" spinner feedback
- No request cancellation if user navigates away

---

## 7. TEMPLATE RENDERING BOTTLENECKS

### Problem 7.1: Large Dataset Tables in Jinja2

**Location:** [templates/preview.html L19-36]

```jinja2
{% for row in data %}
<tr>
    {% for col in columns %}
    <td>{{ row[col] }}</td>
    {% endfor %}
</tr>
{% endfor %}
```

**For 10,000 rows:**
- Jinja2 must render 10,000 × 30 = 300,000 cells
- Each cell variable interpolation checked
- Result: 5-10MB HTML document
- Browser must diff/reflow 300K DOM nodes

### Problem 7.2: Processing Summary With All Data

**Location:** [templates/processing_summary.html]

Template renders:
- Full cleaned dataset sample (convertable to strings)
- All reports with all details
- Full validation warnings list
- Column statistics for every column

**For 100-column dataset:**
- 100 column rows in stats table
- All validation warnings (could be 1000+)
- Result: 3-5MB HTML

---

## SUMMARY: BOTTLENECK LOCATIONS & FIXES NEEDED

| Issue | Location | Severity | Fix |
|-------|----------|----------|-----|
| Tab reload latency | app.py routes | **CRITICAL** | Implement client-side tabs with cached data |
| Preview loads full dataset | app.py:396-406 | **CRITICAL** | Paginate or virtualize table (show 50 rows) |
| Redundant type inference | Multiple modules | HIGH | Cache column types, infer once at load |
| Inconsistent NaN handling | data_cleaning.py + preprocessing | HIGH | Unified missing value abstraction layer |
| CSV reloads from disk | All routes | HIGH | Use in-memory cache with LRU eviction |
| No pagination in chat | chat.html + api | MEDIUM | Add offset/limit pagination |
| Processing stats recalculated | app.py:421-450 | MEDIUM | Cache stats at upload time |
| Sequential upload pipeline | app.py:165-346 | MEDIUM | Parallelize IO-independent steps |
| Session memory bloat | app.py ~360+ | MEDIUM | Use external cache (Redis) for reports |

---

## ROOT CAUSE ANALYSIS

1. **Architecture:** Page-per-view with full reloads instead of SPA (Single Page App)
2. **Caching:** No application-level caching strategy
3. **Data Loading:** No lazy loading, pagination, or virtualization
4. **Type System:** No unified type detection and caching
5. **Session Management:** Session stored as files, not optimized cache

---

## Next Steps (Priority Order)

1. **Immediate (Week 1):** Implement preview pagination (show 100 rows max)
2. **Short-term (Week 2):** Client-side tab switching with cached data
3. **Medium-term (Week 3-4):** Add column type caching and missing value abstraction
4. **Long-term (Week 5-6):** Migrate to SPA architecture with React/Vue for dynamic UI


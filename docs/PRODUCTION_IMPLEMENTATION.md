# Production-Grade Data Analysis System - Documentation

## Overview
This is a production-grade AI-powered data analysis and automation system that handles all file types, data patterns, and edge cases safely with comprehensive error handling.

## Key Features

### 1. **Universal File Format Support**
- **CSV Files**: Multiple delimiter detection (comma, semicolon, tab, auto-detect)
- **Excel Files**: .xlsx, .xls with openpyxl engine, automatic sheet detection
- **JSON Files**: Standard JSON, JSONL (line-delimited), nested structures
- **Encoding Handling**: UTF-8, Latin-1, with automatic fallback

### 2. **Robust Data Type Handling**
- **Automatic Type Detection**: Detects numeric, string, datetime, boolean, mixed
- **Safe Type Coercion**: Uses `pd.to_numeric(errors='coerce')` to safely convert types
- **Mixed Type Handling**: Intelligently handles columns with mixed data types
- **Header Detection**: Automatically detects and removes duplicate header rows
- **No Data Loss on Type Errors**: Failed conversions replaced with NaN, not removed

### 3. **Data Pipeline Steps**

#### Step 1: Load
- Auto-detects file format
- Removes duplicate header rows
- Converts columns to proper types
- Handles encoding issues

#### Step 2: Validate
- Checks data quality
- Detects missing values
- Analyzes pattern issues
- Generates quality score

#### Step 3: Clean
- Handles missing values by type:
  - **Numeric**: Uses median imputation
  - **String**: Replaces with 'unknown'
  - **Datetime**: Forward/backward fill
  - **Boolean**: Uses mode
- Removes empty columns
- Standardizes column names
- Caps outliers (preserves rows)
- Detects inconsistencies

#### Step 4: Preprocess
- Encodes categorical variables
- Handles skewed distributions
- Normalizes numeric columns (0-1 scaling)
- Safe type conversion

#### Step 5: Transform
- Creates aggregate features
- Generates business metrics (profit margin)
- Extracts time-based features
- Bins numeric columns
- Creates interaction features

#### Step 6: Visualize
- Generates statistics
- Creates numeric insights
- Summarizes categorical data
- Calculates correlations

## Error Handling Strategy

### Graceful Degradation
- If a step fails (validation, preprocessing), pipeline continues with available data
- Logs all errors and warnings
- Never stops processing due to type conversion failures

### Type Coercion
All comparison operations use safe numeric conversion:
```python
numeric_col = pd.to_numeric(df[col], errors='coerce')
# Failed conversions become NaN instead of causing errors
```

### Operation Safety
- Quantile operations only on converted numeric data
- Median calculation on non-null values only
- IQR outlier detection with zero-variance check
- Division by zero protection with numpy error handling

## Usage Examples

### Using the Pipeline Orchestrator
```python
from modules.pipeline import DataPipeline

# Create pipeline
pipeline = DataPipeline('path/to/file.xlsx')

# Execute full pipeline
status = pipeline.execute()

# Or execute specific steps
status = pipeline.execute(steps=['load', 'clean', 'transform', 'visualize'])

# Access results
print(pipeline.get_data_summary())
print(pipeline.reports)

# Save processed data
pipeline.save('output.csv', format='csv')
```

### API Usage
```python
# Upload and process file
POST /api/data/upload
- Returns: file info, quality score, processing reports, data preview
```

## Supported Data Types

### Input Types
- ✓ **Numeric**: int, float, decimal
- ✓ **String**: text, names, categories
- ✓ **Datetime**: dates, timestamps
- ✓ **Boolean**: true/false, 1/0, yes/no
- ✓ **Mixed**: Columns with multiple types
- ✓ **Special**: Arrays, dictionaries, regex patterns
- ✓ **Missing**: NULL, None, NaN, empty strings

### File Formats
- ✓ CSV (any delimiter)
- ✓ Excel (XLSX, XLS)
- ✓ JSON
- ✓ JSONL (line-delimited)

## Configuration

### Environment Variables
```
UPLOAD_FOLDER=uploads/
CLEANED_FOLDER=cleaned_data/
LOGS_FOLDER=logs/
```

### Quality Thresholds
- Numeric detection: >80% values convertible
- Datetime detection: >80% values convertible
- Empty column removal: 0 valid values
- Outlier detection: IQR method (1.5 × IQR)

## Performance Optimizations

1. **Type Inference Once**: Types detected once during load, reused throughout
2. **Vectorized Operations**: Uses pandas vectorized operations, not loops
3. **Memory Efficient**: Processes data in-place where possible
4. **Smart Caching**: Stores reports in dataframe attributes
5. **Parallel Processing**: API routes handle concurrent uploads

## Logging

All operations are logged to `logs/app.log`:
- ✓ File loading with format info
- ✓ Data shape changes
- ✓ Validation results
- ✓ Cleaning operations
- ✓ Warnings and errors
- ✓ Processing times

## Error Messages

### Load Errors
- "Failed to load file format": File corrupted or unsupported format

### Type Errors
- "Error analyzing column": Mixed types, auto-handled with coercion

### Data Errors
- "Could not calculate median": Non-numeric column, uses fallback
- "Outlier detection failed": Skipped, continues processing

## Best Practices

1. **Monitor Logs**: Check `logs/app.log` for warnings
2. **Use Pipeline Reports**: Review validation and cleaning reports
3. **Verify Output**: Check data preview in API response
4. **Handle Warnings**: Warnings indicate data issues that were auto-handled
5. **Backup Original**: API keeps original file in `uploads/` folder

## Troubleshooting

### Issue: Still getting type errors
**Solution**: All type errors should now be handled. If found, check:
1. Are you using the new `load_file()` function?
2. Are column operations using `pd.to_numeric(errors='coerce')`?

### Issue: Data being removed
**Solution**: The system never removes rows due to type errors. 
- Rows removed only if all values are empty (step 6 of cleaning)
- Use `get_cleaning_report()` to see what was removed

### Issue: Large file processing slow
**Solution**: Improvements made:
1. Vectorized operations (no loops)
2. Type inference only done once
3. Use CSV for large files instead of Excel

## Production Deployment

### Requirements
```
pandas>=1.3.0
openpyxl>=3.0.0
Flask>=2.0.0
scikit-learn>=0.24.0
```

### Recommendations
1. Enable logging to file
2. Set up error monitoring
3. Use database for storing processing reports
4. Implement file size limits
5. Use background queue for large files
6. Cache validation results

## Version History

- **v2.0** (Current): Production-grade with all type handling
  - Universal file format support
  - Safe type coercion throughout
  - Graceful error handling
  - Comprehensive logging
  - Data pipeline orchestrator

- **v1.0**: Initial version
  - CSV-only support
  - Limited type handling
  - Type comparison errors on mixed data

## Support

For issues or enhancements:
1. Check logs/app.log for error details
2. Review data validation report
3. Verify file format is supported
4. Check column data types in preview

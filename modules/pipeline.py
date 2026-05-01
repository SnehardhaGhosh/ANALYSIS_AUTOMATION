"""
Production-grade data pipeline orchestrator
Handles all file formats and data types safely with comprehensive error reporting
"""

import pandas as pd
import logging
from pathlib import Path

from .file_handler import load_file
from .data_validation import validate_data
from .data_cleaning import clean_data, get_cleaning_report
from .data_preprocessing import preprocess_data, get_preprocessing_report
from .data_transformation import transform_data, get_transformation_report
from .visualizations import generate_visualizations, format_visualizations_for_json
from .utils import fill_missing_values_safe, remove_empty_columns

logger = logging.getLogger(__name__)


class DataPipeline:
    """
    Production-grade data processing pipeline with error handling
    """
    
    def __init__(self, filepath):
        self.filepath = filepath
        self.df = None
        self.reports = {}
        self.errors = []
        self.warnings = []
    
    def load(self):
        """Load file with auto-format detection"""
        try:
            logger.info(f"Loading file: {self.filepath}")
            self.df = load_file(self.filepath)
            logger.info(f"✓ File loaded: {self.df.shape[0]} rows × {self.df.shape[1]} columns")
            return True
        except Exception as e:
            error_msg = f"File load failed: {str(e)}"
            logger.error(error_msg)
            self.errors.append(error_msg)
            return False
    
    def validate(self):
        """Validate data quality"""
        if self.df is None:
            self.warnings.append("Data validation skipped - no data loaded")
            return False
        
        try:
            logger.info("Validating data...")
            validation_result = validate_data(self.df)
            self.reports['validation'] = validation_result
            quality_score = validation_result.get('quality_score', 0)
            logger.info(f"✓ Data validation complete. Quality score: {quality_score}%")
            return True
        except Exception as e:
            warning_msg = f"Data validation error (continuing): {str(e)}"
            logger.warning(warning_msg)
            self.warnings.append(warning_msg)
            return False
    
    def clean(self):
        """Clean data"""
        if self.df is None:
            self.warnings.append("Data cleaning skipped - no data loaded")
            return False
        
        try:
            logger.info("Cleaning data...")
            self.df = clean_data(self.df)
            cleaning_report = get_cleaning_report(self.df)
            if cleaning_report:
                self.reports['cleaning'] = cleaning_report
            logger.info(f"✓ Data cleaned: {self.df.shape[0]} rows × {self.df.shape[1]} columns")
            return True
        except Exception as e:
            error_msg = f"Data cleaning failed: {str(e)}"
            logger.error(error_msg)
            self.errors.append(error_msg)
            # Continue with uncleaned data
            return False
    
    def preprocess(self):
        """Preprocess data"""
        if self.df is None:
            self.warnings.append("Preprocessing skipped - no data loaded")
            return False
        
        try:
            logger.info("Preprocessing data...")
            self.df = preprocess_data(self.df)
            preprocessing_report = get_preprocessing_report(self.df)
            if preprocessing_report:
                self.reports['preprocessing'] = preprocessing_report
            logger.info(f"✓ Preprocessing complete: {self.df.shape[1]} columns")
            return True
        except Exception as e:
            warning_msg = f"Preprocessing error (continuing): {str(e)}"
            logger.warning(warning_msg)
            self.warnings.append(warning_msg)
            return False
    
    def transform(self):
        """Transform data"""
        if self.df is None:
            self.warnings.append("Transformation skipped - no data loaded")
            return False
        
        try:
            logger.info("Transforming data...")
            self.df = transform_data(self.df)
            transformation_report = get_transformation_report(self.df)
            if transformation_report:
                self.reports['transformation'] = transformation_report
            logger.info(f"✓ Transformation complete: {self.df.shape[1]} columns (with features)")
            return True
        except Exception as e:
            warning_msg = f"Transformation error (continuing): {str(e)}"
            logger.warning(warning_msg)
            self.warnings.append(warning_msg)
            return False
    
    def visualize(self):
        """Generate visualizations"""
        if self.df is None:
            self.warnings.append("Visualization skipped - no data loaded")
            return False
        
        try:
            logger.info("Generating visualizations...")
            vis = generate_visualizations(self.df)
            self.reports['visualizations'] = format_visualizations_for_json(vis)
            logger.info("✓ Visualizations generated")
            return True
        except Exception as e:
            warning_msg = f"Visualization error (continuing): {str(e)}"
            logger.warning(warning_msg)
            self.warnings.append(warning_msg)
            return False
    
    def execute(self, steps=None):
        """
        Execute complete pipeline with specified steps
        steps: list of steps to execute ['load', 'validate', 'clean', 'preprocess', 'transform', 'visualize']
        If None, executes all steps
        """
        if steps is None:
            steps = ['load', 'validate', 'clean', 'preprocess', 'transform', 'visualize']
        
        logger.info(f"Starting pipeline with steps: {steps}")
        
        step_methods = {
            'load': self.load,
            'validate': self.validate,
            'clean': self.clean,
            'preprocess': self.preprocess,
            'transform': self.transform,
            'visualize': self.visualize
        }
        
        for step in steps:
            if step not in step_methods:
                logger.warning(f"Unknown step: {step}")
                continue
            
            try:
                method = step_methods[step]
                success = method()
                if not success and step == 'load':
                    # If load fails, stop pipeline
                    logger.error("Pipeline aborted - load failed")
                    break
            except Exception as e:
                error_msg = f"Pipeline error at step '{step}': {str(e)}"
                logger.error(error_msg)
                self.errors.append(error_msg)
        
        return self.get_status()
    
    def get_status(self):
        """Get pipeline execution status"""
        return {
            'success': len(self.errors) == 0,
            'data': self.get_data_summary(),
            'reports': self.reports,
            'errors': self.errors,
            'warnings': self.warnings
        }
    
    def get_data_summary(self):
        """Get summary of current dataframe"""
        if self.df is None:
            return None
        
        return {
            'rows': len(self.df),
            'columns': len(self.df.columns),
            'column_names': self.df.columns.tolist(),
            'dtypes': self.df.dtypes.astype(str).to_dict(),
            'memory_usage_mb': round(self.df.memory_usage(deep=True).sum() / 1024**2, 2),
            'preview': self.df.head(10).to_dict(orient='records')
        }
    
    def save(self, output_path, format='csv'):
        """Save processed data to file"""
        if self.df is None:
            return False
        
        try:
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            
            if format == 'csv':
                self.df.to_csv(output_path, index=False)
            elif format == 'excel' or format == 'xlsx':
                self.df.to_excel(output_path, index=False)
            elif format == 'json':
                self.df.to_json(output_path)
            else:
                logger.error(f"Unsupported save format: {format}")
                return False
            
            logger.info(f"✓ Data saved to {output_path}")
            return True
        except Exception as e:
            error_msg = f"Failed to save data: {str(e)}"
            logger.error(error_msg)
            self.errors.append(error_msg)
            return False


def process_file(filepath, output_folder=None, steps=None):
    """
    Convenience function to process a file end-to-end
    """
    pipeline = DataPipeline(filepath)
    status = pipeline.execute(steps)
    
    if output_folder and pipeline.df is not None:
        output_path = Path(output_folder) / f"processed_{Path(filepath).name}"
        pipeline.save(str(output_path), format='csv')
    
    return status

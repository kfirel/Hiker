"""
Performance monitoring utilities for tracking response times
"""
import time
import logging
from functools import wraps
from typing import Optional

logger = logging.getLogger(__name__)

class PerformanceMonitor:
    """Track performance metrics for different operations"""
    
    def __init__(self):
        self.metrics = {}
    
    def start_timer(self, operation_name: str) -> float:
        """Start timing an operation"""
        start_time = time.time()
        self.metrics[operation_name] = {'start': start_time}
        return start_time
    
    def end_timer(self, operation_name: str, log: bool = True) -> Optional[float]:
        """End timing an operation and return duration"""
        if operation_name not in self.metrics:
            return None
        
        end_time = time.time()
        start_time = self.metrics[operation_name].get('start')
        if start_time:
            duration = end_time - start_time
            self.metrics[operation_name]['end'] = end_time
            self.metrics[operation_name]['duration'] = duration
            
            if log:
                logger.info(f"⏱️  PERF: {operation_name} took {duration:.3f}s")
            
            return duration
        return None
    
    def log_metric(self, operation_name: str, duration: float, details: dict = None):
        """Log a performance metric"""
        details_str = f" | {details}" if details else ""
        logger.info(f"⏱️  PERF: {operation_name} took {duration:.3f}s{details_str}")
    
    def get_metrics(self) -> dict:
        """Get all collected metrics"""
        return self.metrics.copy()

# Global performance monitor instance
perf_monitor = PerformanceMonitor()

def time_operation(operation_name: str):
    """Decorator to time a function execution"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = perf_monitor.start_timer(operation_name)
            try:
                result = func(*args, **kwargs)
                perf_monitor.end_timer(operation_name)
                return result
            except Exception as e:
                perf_monitor.end_timer(operation_name)
                raise e
        return wrapper
    return decorator

def log_timing(operation_name: str, duration: float, details: dict = None):
    """Helper function to log timing information"""
    perf_monitor.log_metric(operation_name, duration, details)


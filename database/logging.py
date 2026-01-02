"""
Logging Functions for Firestore
Store and retrieve system logs and errors
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from google.cloud import firestore
from utils.timezone_utils import israel_now_isoformat

logger = logging.getLogger(__name__)


async def log_error(
    db: firestore.Client,
    severity: str,
    message: str,
    stack_trace: Optional[str] = None,
    user_phone: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None
) -> bool:
    """
    Log an error to Firestore
    
    Args:
        db: Firestore client
        severity: 'error', 'warning', or 'info'
        message: Error message
        stack_trace: Optional stack trace
        user_phone: Optional user phone number
        context: Optional additional context (dict)
    
    Returns:
        True if successful, False otherwise
    """
    try:
        error_data = {
            "timestamp": israel_now_isoformat(),
            "severity": severity,
            "message": message,
            "stack_trace": stack_trace,
            "user_phone": user_phone,
            "context": context or {}
        }
        
        db.collection("error_logs").add(error_data)
        return True
    
    except Exception as e:
        logger.error(f"❌ Failed to log error to Firestore: {e}")
        return False


async def log_activity(
    db: firestore.Client,
    activity_type: str,
    description: str,
    user_phone: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> bool:
    """
    Log a system activity to Firestore
    
    Args:
        db: Firestore client
        activity_type: Type of activity (e.g., 'match_created', 'user_registered', 'message_sent')
        description: Human-readable description
        user_phone: Optional user phone number
        metadata: Optional metadata (dict)
    
    Returns:
        True if successful, False otherwise
    """
    try:
        activity_data = {
            "timestamp": israel_now_isoformat(),
            "activity_type": activity_type,
            "description": description,
            "user_phone": user_phone,
            "metadata": metadata or {}
        }
        
        db.collection("system_logs").add(activity_data)
        return True
    
    except Exception as e:
        logger.error(f"❌ Failed to log activity to Firestore: {e}")
        return False


async def get_error_logs(
    db: firestore.Client,
    severity: Optional[str] = None,
    limit: int = 100,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Retrieve error logs from Firestore
    
    Args:
        db: Firestore client
        severity: Filter by severity ('error', 'warning', 'info')
        limit: Maximum number of logs to return
        start_date: ISO format date string (optional)
        end_date: ISO format date string (optional)
    
    Returns:
        List of error log dictionaries
    """
    try:
        query = db.collection("error_logs").order_by("timestamp", direction=firestore.Query.DESCENDING)
        
        # Apply severity filter
        if severity:
            query = query.where("severity", "==", severity)
        
        # Apply date filters
        if start_date:
            query = query.where("timestamp", ">=", start_date)
        if end_date:
            query = query.where("timestamp", "<=", end_date)
        
        # Limit results
        query = query.limit(limit)
        
        docs = query.stream()
        
        logs = []
        for doc in docs:
            log_data = doc.to_dict()
            log_data["id"] = doc.id
            logs.append(log_data)
        
        return logs
    
    except Exception as e:
        logger.error(f"❌ Error retrieving error logs: {e}")
        return []


async def get_activity_logs(
    db: firestore.Client,
    activity_type: Optional[str] = None,
    limit: int = 100,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Retrieve activity logs from Firestore
    
    Args:
        db: Firestore client
        activity_type: Filter by activity type (optional)
        limit: Maximum number of logs to return
        start_date: ISO format date string (optional)
        end_date: ISO format date string (optional)
    
    Returns:
        List of activity log dictionaries
    """
    try:
        query = db.collection("system_logs").order_by("timestamp", direction=firestore.Query.DESCENDING)
        
        # Apply activity type filter
        if activity_type:
            query = query.where("activity_type", "==", activity_type)
        
        # Apply date filters
        if start_date:
            query = query.where("timestamp", ">=", start_date)
        if end_date:
            query = query.where("timestamp", "<=", end_date)
        
        # Limit results
        query = query.limit(limit)
        
        docs = query.stream()
        
        logs = []
        for doc in docs:
            log_data = doc.to_dict()
            log_data["id"] = doc.id
            logs.append(log_data)
        
        return logs
    
    except Exception as e:
        logger.error(f"❌ Error retrieving activity logs: {e}")
        return []


async def clean_old_logs(db: firestore.Client, days: int = 90) -> int:
    """
    Delete logs older than specified days
    
    Args:
        db: Firestore client
        days: Number of days to keep logs
    
    Returns:
        Number of logs deleted
    """
    try:
        cutoff_date = (datetime.utcnow() - timedelta(days=days)).isoformat()
        
        deleted_count = 0
        
        # Clean error logs
        error_docs = db.collection("error_logs").where("timestamp", "<", cutoff_date).stream()
        for doc in error_docs:
            doc.reference.delete()
            deleted_count += 1
        
        # Clean activity logs
        activity_docs = db.collection("system_logs").where("timestamp", "<", cutoff_date).stream()
        for doc in activity_docs:
            doc.reference.delete()
            deleted_count += 1
        
        logger.info(f"✅ Cleaned {deleted_count} old logs (older than {days} days)")
        return deleted_count
    
    except Exception as e:
        logger.error(f"❌ Error cleaning old logs: {e}")
        return 0


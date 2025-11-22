"""
Create index.html in test_runs/latest directory
This file is called after test runs to create a navigation page
"""

from pathlib import Path
from datetime import datetime


def create_latest_index(test_runs_base: Path):
    """Create index.html in latest directory"""
    latest_dir = test_runs_base / "latest"
    
    if not latest_dir.exists():
        latest_dir.mkdir(exist_ok=True)
    
    # Check for reports in latest directory (copied files)
    conversation_report = latest_dir / "test_report.html"
    integration_report = latest_dir / "integration_test_report.html"
    
    # Check if links exist (fallback)
    conversation_link = latest_dir / "conversation_flows"
    integration_link = latest_dir / "integration"
    
    conversation_path = None
    integration_path = None
    
    # Check for copied report files first
    if conversation_report.exists():
        conversation_path = "test_report.html"
    elif conversation_link.exists() or conversation_link.is_symlink():
        try:
            target = conversation_link.resolve()
            report = target / "test_report.html"
            if report.exists():
                conversation_path = f"conversation_flows/test_report.html"
        except:
            pass
    
    if integration_report.exists():
        integration_path = "integration_test_report.html"
    elif integration_link.exists() or integration_link.is_symlink():
        try:
            target = integration_link.resolve()
            report = target / "integration_test_report.html"
            if report.exists():
                integration_path = f"integration/integration_test_report.html"
        except:
            pass
    
    html = f"""<!DOCTYPE html>
<html lang="he" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Hiker Bot - Latest Test Reports</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 40px 20px;
            direction: rtl;
            min-height: 100vh;
        }}
        
        .container {{
            max-width: 800px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            padding: 40px;
        }}
        
        .header {{
            text-align: center;
            margin-bottom: 40px;
            padding-bottom: 20px;
            border-bottom: 3px solid #667eea;
        }}
        
        .header h1 {{
            color: #333;
            font-size: 2.5em;
            margin-bottom: 10px;
        }}
        
        .header .subtitle {{
            color: #666;
            font-size: 1.1em;
        }}
        
        .reports-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-top: 30px;
        }}
        
        .report-card {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 10px;
            padding: 25px;
            color: white;
            text-decoration: none;
            display: block;
            transition: transform 0.3s, box-shadow 0.3s;
            box-shadow: 0 5px 15px rgba(0,0,0,0.2);
        }}
        
        .report-card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 10px 25px rgba(0,0,0,0.3);
        }}
        
        .report-card.unavailable {{
            background: linear-gradient(135deg, #999 0%, #666 100%);
            opacity: 0.6;
            cursor: not-allowed;
        }}
        
        .report-card.unavailable:hover {{
            transform: none;
        }}
        
        .report-card h2 {{
            font-size: 1.5em;
            margin-bottom: 10px;
        }}
        
        .report-card p {{
            font-size: 1em;
            opacity: 0.9;
            line-height: 1.6;
        }}
        
        .report-card .icon {{
            font-size: 3em;
            margin-bottom: 15px;
        }}
        
        .timestamp {{
            text-align: center;
            color: #666;
            margin-top: 30px;
            font-size: 0.9em;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚗 Hiker Bot</h1>
            <div class="subtitle">Latest Test Reports</div>
        </div>
        
        <div class="reports-grid">
            <a href="{conversation_path or '#'}" class="report-card {'unavailable' if not conversation_path else ''}" {'onclick="return false;"' if not conversation_path else ''}>
                <div class="icon">💬</div>
                <h2>Conversation Flows</h2>
                <p>דוח טסטים של זרימת השיחה - בדיקת כל ה-flows והאינטראקציות עם הבוט</p>
            </a>
            
            <a href="{integration_path or '#'}" class="report-card {'unavailable' if not integration_path else ''}" {'onclick="return false;"' if not integration_path else ''}>
                <div class="icon">🔗</div>
                <h2>Integration Tests</h2>
                <p>דוח טסטים משולבים - בדיקת שמירת מידע, matching, והתראות עם MongoDB</p>
            </a>
        </div>
        
        <div class="timestamp">
            Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        </div>
    </div>
</body>
</html>"""
    
    index_file = latest_dir / "index.html"
    with open(index_file, 'w', encoding='utf-8') as f:
        f.write(html)
    
    return index_file


"""
Integration Test Report Generator
Creates HTML reports showing data persistence, matching, and notifications
with chronological multi-user conversation tables
"""

from typing import List, Dict, Any
from datetime import datetime
import os


class IntegrationReportGenerator:
    """Generate HTML reports for integration test results"""
    
    def __init__(self, output_file: str = "integration_test_report.html"):
        self.output_file = output_file
        self.scenarios = []
        self.user_colors = {}  # Cache colors for user IDs
    
    def _get_user_color(self, user_id: str) -> tuple:
        """Generate a consistent color for a user ID"""
        if not user_id:
            return ("rgb(227, 242, 253)", "rgb(33, 150, 243)")
        
        if user_id in self.user_colors:
            return self.user_colors[user_id]
        
        import hashlib
        hash_obj = hashlib.md5(user_id.encode())
        hash_int = int(hash_obj.hexdigest(), 16)
        
        hue = hash_int % 360
        saturation = 0.25 + ((hash_int // 360) % 30) / 100
        lightness_bg = 0.88 + ((hash_int // 10800) % 8) / 100
        lightness_border = 0.50 + ((hash_int // 360) % 20) / 100
        
        import colorsys
        rgb_bg = colorsys.hls_to_rgb(hue / 360, lightness_bg, saturation)
        rgb_border = colorsys.hls_to_rgb(hue / 360, lightness_border, min(saturation + 0.2, 1.0))
        
        background_color = f"rgb({int(rgb_bg[0]*255)}, {int(rgb_bg[1]*255)}, {int(rgb_bg[2]*255)})"
        border_color = f"rgb({int(rgb_border[0]*255)}, {int(rgb_border[1]*255)}, {int(rgb_border[2]*255)})"
        
        self.user_colors[user_id] = (background_color, border_color)
        return (background_color, border_color)
    
    def add_scenario(self, scenario_result: Dict[str, Any]):
        """Add a scenario result to the report"""
        self.scenarios.append(scenario_result)
    
    def generate_html(self) -> str:
        """Generate HTML report content"""
        html = f"""<!DOCTYPE html>
<html lang="he" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Hiker Bot - Integration Test Report</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            direction: rtl;
        }}
        
        .container {{
            max-width: 1800px;
            margin: 0 auto;
            background: white;
            border-radius: 8px;
            box-shadow: 0 5px 20px rgba(0,0,0,0.1);
            padding: 20px;
        }}
        
        .header {{
            text-align: center;
            padding: 15px 0;
            border-bottom: 2px solid #667eea;
            margin-bottom: 20px;
        }}
        
        .header h1 {{
            color: #333;
            font-size: 2em;
            margin-bottom: 5px;
        }}
        
        .header .subtitle {{
            color: #666;
            font-size: 1em;
        }}
        
        .summary {{
            display: flex;
            justify-content: space-around;
            margin-bottom: 25px;
            padding: 15px;
            background: #f8f9fa;
            border-radius: 6px;
        }}
        
        .summary-item {{
            text-align: center;
        }}
        
        .summary-item .number {{
            font-size: 2.5em;
            font-weight: bold;
            color: #667eea;
        }}
        
        .summary-item .label {{
            color: #666;
            margin-top: 5px;
            font-size: 1em;
        }}
        
        .scenario-section {{
            margin-bottom: 40px;
            border: 1px solid #e0e0e0;
            border-radius: 6px;
            overflow: hidden;
        }}
        
        .scenario-header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 12px 15px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        
        .scenario-header.success {{
            background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
        }}
        
        .scenario-header.failed {{
            background: linear-gradient(135deg, #ee0979 0%, #ff6a00 100%);
        }}
        
        .scenario-title {{
            font-size: 1.2em;
            font-weight: bold;
        }}
        
        .scenario-status {{
            padding: 5px 12px;
            border-radius: 15px;
            background: rgba(255,255,255,0.3);
            font-size: 0.9em;
        }}
        
        .scenario-description {{
            padding: 10px 15px;
            background: #f8f9fa;
            color: #666;
            border-bottom: 1px solid #e0e0e0;
            font-size: 0.95em;
        }}
        
        .data-section {{
            margin: 15px;
            padding: 15px;
            background: #f8f9fa;
            border-radius: 6px;
        }}
        
        .data-section h3 {{
            color: #333;
            margin-bottom: 10px;
            font-size: 1.1em;
        }}
        
        .data-table {{
            width: 100%;
            border-collapse: collapse;
            background: white;
            border-radius: 4px;
            overflow: hidden;
        }}
        
        .data-table th {{
            background: #667eea;
            color: white;
            padding: 8px 12px;
            text-align: right;
            font-weight: bold;
            border: 1px solid rgba(255,255,255,0.2);
        }}
        
        .data-table td {{
            padding: 8px 12px;
            border: 1px solid #e0e0e0;
            text-align: right;
        }}
        
        .data-table tr:nth-child(even) {{
            background: #f8f9fa;
        }}
        
        .chronological-table-wrapper {{
            margin: 15px;
            overflow-x: auto;
            overflow-y: visible;
        }}
        
        .chronological-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 0.85em;
            min-width: 800px;
        }}
        
        .chronological-table th {{
            background: #667eea;
            color: white;
            padding: 8px 10px;
            text-align: center;
            font-weight: bold;
            border: 1px solid rgba(255,255,255,0.2);
            min-width: 200px;
            position: sticky;
            top: 0;
            z-index: 10;
        }}
        
        .chronological-table th:first-child {{
            position: sticky;
            left: 0;
            z-index: 20;
            min-width: 150px;
        }}
        
        .chronological-table td {{
            padding: 8px 10px;
            border: 1px solid #e0e0e0;
            vertical-align: top;
            background: white;
            min-width: 200px;
            max-width: 300px;
        }}
        
        .chronological-table td:first-child {{
            position: sticky;
            left: 0;
            z-index: 10;
            background: inherit;
        }}
        
        .user-message {{
            padding: 6px 8px;
            border-left: 4px solid;
            border-radius: 4px;
            margin-bottom: 5px;
            font-size: 0.9em;
            line-height: 1.4;
            word-wrap: break-word;
            max-height: 200px;
            overflow-y: auto;
        }}
        
        .bot-message {{
            background: #f1f8e9;
            border-left: 4px solid #8bc34a;
            padding: 6px 8px;
            border-radius: 4px;
            margin-bottom: 5px;
            font-size: 0.9em;
            line-height: 1.4;
            word-wrap: break-word;
            max-height: 200px;
            overflow-y: auto;
        }}
        
        .notification-message {{
            background: #fff3e0;
            border-left: 4px solid #ff9800;
            padding: 6px 8px;
            border-radius: 4px;
            margin-bottom: 5px;
            font-size: 0.85em;
            line-height: 1.3;
        }}
        
        .button {{
            display: inline-block;
            padding: 3px 8px;
            margin: 2px;
            background: #667eea;
            color: white;
            border-radius: 3px;
            font-size: 0.75em;
            line-height: 1.2;
        }}
        
        .timestamp {{
            font-size: 0.7em;
            color: #999;
            margin-top: 3px;
        }}
        
        .error-message {{
            padding: 10px 15px;
            background: #ffebee;
            color: #c62828;
            border-left: 3px solid #c62828;
            margin: 15px;
            border-radius: 3px;
        }}
        
        .user-badge {{
            display: inline-block;
            padding: 3px 8px;
            border-radius: 12px;
            font-size: 0.8em;
            font-weight: bold;
            color: white;
            margin-bottom: 5px;
        }}
        
        .log-files-section {{
            margin: 15px;
            padding: 15px;
            background: #e3f2fd;
            border-radius: 6px;
            border-left: 4px solid #2196f3;
        }}
        
        .log-files-section h4 {{
            color: #1976d2;
            margin-bottom: 10px;
            font-size: 1em;
        }}
        
        .log-file-link {{
            display: inline-block;
            padding: 5px 12px;
            margin: 3px;
            background: #2196f3;
            color: white;
            text-decoration: none;
            border-radius: 4px;
            font-size: 0.85em;
            transition: background 0.3s;
        }}
        
        .log-file-link:hover {{
            background: #1976d2;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚗 Hiker Bot - Integration Test Report</h1>
            <div class="subtitle">Data Persistence, Matching & Notifications Test Results</div>
            <div class="subtitle">Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>
        </div>
        
        {self._generate_summary()}
        
        {self._generate_scenarios()}
    </div>
</body>
</html>"""
        return html
    
    def _generate_summary(self) -> str:
        """Generate summary section"""
        total = len(self.scenarios)
        passed = sum(1 for s in self.scenarios if not s.get('error'))
        failed = total - passed
        
        return f"""
        <div class="summary">
            <div class="summary-item">
                <div class="number">{total}</div>
                <div class="label">Total Scenarios</div>
            </div>
            <div class="summary-item">
                <div class="number" style="color: #38ef7d;">{passed}</div>
                <div class="label">Passed</div>
            </div>
            <div class="summary-item">
                <div class="number" style="color: #ee0979;">{failed}</div>
                <div class="label">Failed</div>
            </div>
        </div>
        """
    
    def _generate_scenarios(self) -> str:
        """Generate all scenario sections"""
        scenarios_html = []
        
        for idx, scenario in enumerate(self.scenarios, 1):
            has_error = bool(scenario.get('error'))
            status_class = "success" if not has_error else "failed"
            status_text = "✅ PASSED" if not has_error else "❌ FAILED"
            
            # Build chronological conversation table
            chronological_table_html = self._build_chronological_table(scenario)
            
            # Build error message if failed
            error_html = ""
            if has_error:
                error_html = f'<div class="error-message"><strong>Error:</strong> {scenario["error"]}</div>'
            
            scenario_html = f"""
            <div class="scenario-section">
                <div class="scenario-header {status_class}">
                    <div class="scenario-title">Scenario {idx}: {scenario.get('scenario_name', 'Unnamed')}</div>
                    <div class="scenario-status">{status_text}</div>
                </div>
                <div class="scenario-description">{scenario.get('scenario_description', 'No description')}</div>
                {error_html}
                {chronological_table_html}
            </div>
            """
            scenarios_html.append(scenario_html)
        
        return "\n".join(scenarios_html)
    
    def _build_data_tables(self, scenario: Dict[str, Any]) -> str:
        """Build data tables showing database state"""
        db_snapshot = scenario.get('db_snapshot', {})
        users = db_snapshot.get('users', [])
        routines = db_snapshot.get('routines', [])
        ride_requests = db_snapshot.get('ride_requests', [])
        matches = db_snapshot.get('matches', [])
        
        html = '<div class="data-section">'
        html += '<h3>📊 Database State</h3>'
        
        # Users table
        if users:
            html += '<h4 style="margin-top: 15px; margin-bottom: 5px;">Users</h4>'
            html += '<table class="data-table">'
            html += '<thead><tr><th>Phone</th><th>Name</th><th>Type</th><th>State</th></tr></thead>'
            html += '<tbody>'
            for user in users:
                html += f'<tr>'
                html += f'<td>{self._escape_html(str(user.get("phone", "")))}</td>'
                html += f'<td>{self._escape_html(str(user.get("name", "")))}</td>'
                html += f'<td>{self._escape_html(str(user.get("type", "")))}</td>'
                html += f'<td>{self._escape_html(str(user.get("state", "")))}</td>'
                html += f'</tr>'
            html += '</tbody></table>'
        
        # Routines table
        if routines:
            html += '<h4 style="margin-top: 15px; margin-bottom: 5px;">Routines</h4>'
            html += '<table class="data-table">'
            html += '<thead><tr><th>Phone</th><th>Destination</th><th>Days</th><th>Departure</th></tr></thead>'
            html += '<tbody>'
            for routine in routines:
                html += f'<tr>'
                html += f'<td>{self._escape_html(str(routine.get("phone", "")))}</td>'
                html += f'<td>{self._escape_html(str(routine.get("destination", "")))}</td>'
                html += f'<td>{self._escape_html(str(routine.get("days", "")))}</td>'
                html += f'<td>{self._escape_html(str(routine.get("departure_time", "")))}</td>'
                html += f'</tr>'
            html += '</tbody></table>'
        
        # Ride Requests table
        if ride_requests:
            html += '<h4 style="margin-top: 15px; margin-bottom: 5px;">Ride Requests</h4>'
            html += '<table class="data-table">'
            html += '<thead><tr><th>Request ID</th><th>Phone</th><th>Destination</th><th>Status</th></tr></thead>'
            html += '<tbody>'
            for req in ride_requests:
                html += f'<tr>'
                html += f'<td>{self._escape_html(str(req.get("request_id", "")))}</td>'
                html += f'<td>{self._escape_html(str(req.get("phone", "")))}</td>'
                html += f'<td>{self._escape_html(str(req.get("destination", "")))}</td>'
                html += f'<td>{self._escape_html(str(req.get("status", "")))}</td>'
                html += f'</tr>'
            html += '</tbody></table>'
        
        # Matches table
        if matches:
            html += '<h4 style="margin-top: 15px; margin-bottom: 5px;">Matches</h4>'
            html += '<table class="data-table">'
            html += '<thead><tr><th>Match ID</th><th>Status</th><th>Driver Response</th></tr></thead>'
            html += '<tbody>'
            for match in matches:
                html += f'<tr>'
                html += f'<td>{self._escape_html(str(match.get("match_id", "")))}</td>'
                html += f'<td>{self._escape_html(str(match.get("status", "")))}</td>'
                html += f'<td>{self._escape_html(str(match.get("driver_response", "")))}</td>'
                html += f'</tr>'
            html += '</tbody></table>'
        
        html += '</div>'
        return html
    
    def _build_chronological_table(self, scenario: Dict[str, Any]) -> str:
        """Build chronological table with horizontal layout - users as rows, steps as columns"""
        interactions = scenario.get('interactions', [])
        
        if not interactions:
            return '<div style="padding: 20px; text-align: center; color: #999;">No interactions</div>'
        
        # Get all unique user phones
        user_phones = list(set(interaction.get('user_phone') for interaction in interactions))
        user_phones.sort()  # Sort for consistent ordering
        
        # Group interactions by user
        user_interactions = {}
        for phone in user_phones:
            user_interactions[phone] = []
        
        for idx, interaction in enumerate(interactions, 1):
            phone = interaction.get('user_phone')
            if phone in user_interactions:
                user_interactions[phone].append((idx, interaction))
        
        # Build header - one column per step
        html = '<div class="chronological-table-wrapper">'
        html += '<h3 style="margin: 15px;">💬 Chronological Conversations (Horizontal Layout)</h3>'
        html += '<table class="chronological-table">'
        html += '<thead><tr>'
        html += '<th style="position: sticky; left: 0; z-index: 20; background: #667eea;">User</th>'
        for idx in range(1, len(interactions) + 1):
            html += f'<th>Step {idx}</th>'
        html += '</tr></thead>'
        html += '<tbody>'
        
        # Build rows - one per user
        for phone in user_phones:
            user_id = next((i.get('user_id') for i in interactions if i.get('user_phone') == phone), phone)
            colors = self._get_user_color(user_id)
            
            html += '<tr>'
            
            # User name column (sticky)
            html += f'<td style="position: sticky; left: 0; z-index: 10; background: {colors[1]}; color: white; font-weight: bold; min-width: 150px;">'
            html += f'<div class="user-badge" style="background: {colors[1]};">{self._escape_html(phone)}</div>'
            html += '</td>'
            
            # Get interactions for this user
            user_steps = {step_idx: interaction for step_idx, interaction in user_interactions[phone]}
            
            # Build columns - one per step
            for step_idx in range(1, len(interactions) + 1):
                if step_idx in user_steps:
                    # This user has an interaction at this step
                    interaction = user_steps[step_idx]
                    
                    cell_html = '<div>'
                    
                    # Timestamp
                    timestamp = interaction.get('timestamp')
                    if timestamp:
                        if isinstance(timestamp, datetime):
                            time_str = timestamp.strftime('%H:%M:%S')
                        else:
                            time_str = str(timestamp)
                        cell_html += f'<div class="timestamp">{time_str}</div>'
                    
                    # User message
                    user_msg = interaction.get('user_message', '')
                    if user_msg:
                        cell_html += f'<div class="user-message" style="background: {colors[0]}; border-left-color: {colors[1]};">'
                        cell_html += f'<strong>👤 User:</strong><br>{self._escape_html(user_msg)}'
                        cell_html += '</div>'
                    
                    # Bot response
                    bot_response = interaction.get('bot_response', '')
                    if bot_response:
                        cell_html += '<div class="bot-message">'
                        cell_html += f'<strong>🤖 Bot:</strong><br>{self._escape_html(bot_response)}'
                        
                        # Buttons
                        buttons = interaction.get('buttons', [])
                        if buttons:
                            cell_html += '<div style="margin-top: 5px;">'
                            for btn in buttons:
                                if isinstance(btn, dict):
                                    btn_title = btn.get('title', btn.get('id', ''))
                                    if 'reply' in btn and isinstance(btn['reply'], dict):
                                        btn_title = btn['reply'].get('title', btn['reply'].get('id', ''))
                                else:
                                    btn_title = str(btn)
                                cell_html += f'<span class="button">{self._escape_html(btn_title)}</span>'
                            cell_html += '</div>'
                        cell_html += '</div>'
                    
                    
                    # Error if any
                    error = interaction.get('error')
                    if error:
                        cell_html += f'<div style="background: #ffebee; color: #c62828; padding: 5px; border-radius: 3px; margin-top: 5px;">'
                        cell_html += f'<strong>❌ Error:</strong> {self._escape_html(str(error))}'
                        cell_html += '</div>'
                    
                    cell_html += '</div>'
                    html += f'<td>{cell_html}</td>'
                else:
                    # Empty cell - this user didn't interact at this step
                    html += '<td style="background: #f5f5f5;"></td>'
            
            html += '</tr>'
        
        html += '</tbody></table>'
        html += '</div>'
        
        return html
    
    def _build_log_files_section(self, scenario: Dict[str, Any]) -> str:
        """Build log files section with links to log files"""
        log_files = scenario.get('log_files', [])
        
        if not log_files:
            return ""
        
        html = '<div class="log-files-section">'
        html += '<h4>📝 Log Files - Full Conversation Logs</h4>'
        html += '<p style="font-size: 0.9em; color: #666; margin-bottom: 10px;">לצפייה בלוגים המלאים של כל משתמש:</p>'
        html += '<div style="display: flex; flex-wrap: wrap; gap: 5px;">'
        
        for log_file in log_files:
            phone = log_file.get('phone', '')
            filename = log_file.get('filename', '')
            # Create relative path from report location
            log_path = f"logs/{filename}"
            html += f'<a href="{log_path}" class="log-file-link" target="_blank">📄 {phone}</a>'
        
        html += '</div>'
        html += '</div>'
        
        return html
    
    def _escape_html(self, text: str) -> str:
        """Escape HTML special characters"""
        if not text:
            return ""
        return (str(text).replace('&', '&amp;')
                   .replace('<', '&lt;')
                   .replace('>', '&gt;')
                   .replace('"', '&quot;')
                   .replace("'", '&#39;')
                   .replace('\n', '<br>'))
    
    def save_report(self, output_dir: str = "test_reports"):
        """Save the HTML report to file"""
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        output_path = os.path.join(output_dir, self.output_file)
        
        html_content = self.generate_html()
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"\n📊 Integration test report saved to: {output_path}")
        return output_path


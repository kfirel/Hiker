"""
HTML Report Generator for Test Results
Creates a beautiful HTML report showing all conversation flows in horizontal table format
"""

from typing import List, Dict, Any
from datetime import datetime
import os

class HTMLReportGenerator:
    """Generate HTML reports for test results"""
    
    def __init__(self, output_file: str = "test_report.html"):
        self.output_file = output_file
        self.report_data = []
        self.user_colors = {}  # Cache colors for user IDs
    
    def _get_user_color(self, user_id: str) -> tuple:
        """Generate a consistent color for a user ID
        
        Returns:
            Tuple of (background_color, border_color) as RGB strings
        """
        if not user_id:
            return ("rgb(227, 242, 253)", "rgb(33, 150, 243)")  # Default blue
        
        # Use cached color if available
        if user_id in self.user_colors:
            return self.user_colors[user_id]
        
        # Generate color based on user ID hash
        import hashlib
        hash_obj = hashlib.md5(user_id.encode())
        hash_int = int(hash_obj.hexdigest(), 16)
        
        # Generate a pleasant color with good contrast
        # Use HSL: vary hue, keep saturation moderate, lightness high for background
        hue = hash_int % 360
        saturation = 0.25 + ((hash_int // 360) % 30) / 100  # 25-55% saturation
        lightness_bg = 0.88 + ((hash_int // 10800) % 8) / 100  # 88-96% lightness (light background)
        lightness_border = 0.50 + ((hash_int // 360) % 20) / 100  # 50-70% lightness (darker border)
        
        # Convert HSL to RGB
        import colorsys
        rgb_bg = colorsys.hls_to_rgb(hue / 360, lightness_bg, saturation)
        rgb_border = colorsys.hls_to_rgb(hue / 360, lightness_border, min(saturation + 0.2, 1.0))
        
        background_color = f"rgb({int(rgb_bg[0]*255)}, {int(rgb_bg[1]*255)}, {int(rgb_bg[2]*255)})"
        border_color = f"rgb({int(rgb_border[0]*255)}, {int(rgb_border[1]*255)}, {int(rgb_border[2]*255)})"
        
        # Cache both colors
        self.user_colors[user_id] = (background_color, border_color)
        return (background_color, border_color)
    
    def add_conversation(self, flow_name: str, flow_description: str, 
                        messages: List[Dict[str, Any]], success: bool, 
                        error_message: str = None, user_id: str = None):
        """
        Add a conversation flow to the report
        
        Args:
            flow_name: Name of the flow
            flow_description: Description of the flow
            messages: List of message exchanges
            success: Whether the flow completed successfully
            error_message: Error message if flow failed
            user_id: User ID (phone number) for this flow
        """
        self.report_data.append({
            'flow_name': flow_name,
            'flow_description': flow_description,
            'messages': messages,
            'success': success,
            'error_message': error_message,
            'user_id': user_id
        })
    
    def generate_html(self) -> str:
        """Generate HTML report content"""
        html = f"""<!DOCTYPE html>
<html lang="he" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Hiker Bot - Test Report</title>
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
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 8px;
            box-shadow: 0 5px 20px rgba(0,0,0,0.1);
            padding: 15px;
        }}
        
        .header {{
            text-align: center;
            padding: 12px 0;
            border-bottom: 2px solid #667eea;
            margin-bottom: 15px;
        }}
        
        .header h1 {{
            color: #333;
            font-size: 1.8em;
            margin-bottom: 5px;
        }}
        
        .header .subtitle {{
            color: #666;
            font-size: 0.95em;
        }}
        
        .summary {{
            display: flex;
            justify-content: space-around;
            margin-bottom: 20px;
            padding: 12px;
            background: #f8f9fa;
            border-radius: 6px;
        }}
        
        .summary-item {{
            text-align: center;
        }}
        
        .summary-item .number {{
            font-size: 2em;
            font-weight: bold;
            color: #667eea;
        }}
        
        .summary-item .label {{
            color: #666;
            margin-top: 3px;
            font-size: 0.9em;
        }}
        
        .flow-section {{
            margin-bottom: 25px;
            border: 1px solid #e0e0e0;
            border-radius: 6px;
            overflow: hidden;
        }}
        
        .flow-header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 8px 12px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        
        .flow-header.success {{
            background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
        }}
        
        .flow-header.failed {{
            background: linear-gradient(135deg, #ee0979 0%, #ff6a00 100%);
        }}
        
        .flow-title {{
            font-size: 1.1em;
            font-weight: bold;
        }}
        
        .flow-status {{
            padding: 3px 10px;
            border-radius: 15px;
            background: rgba(255,255,255,0.3);
            font-size: 0.85em;
        }}
        
        .flow-description {{
            padding: 8px 12px;
            background: #f8f9fa;
            color: #666;
            border-bottom: 1px solid #e0e0e0;
            font-size: 0.9em;
        }}
        
        .conversation-table {{
            width: 100%;
            border-collapse: collapse;
            overflow-x: auto;
            display: block;
            font-size: 0.85em;
        }}
        
        .conversation-table thead {{
            background: #667eea;
            color: white;
        }}
        
        .conversation-table th {{
            padding: 6px 8px;
            text-align: center;
            font-weight: bold;
            min-width: 120px;
            max-width: 180px;
            border: 1px solid rgba(255,255,255,0.2);
            font-size: 0.9em;
        }}
        
        .conversation-table td {{
            padding: 6px 8px;
            border: 1px solid #e0e0e0;
            vertical-align: top;
            background: white;
            max-width: 180px;
            word-wrap: break-word;
            overflow-wrap: break-word;
        }}
        
        .user-message {{
            padding: 4px 6px;
            border-left: 3px solid;
            border-radius: 3px;
            margin-bottom: 3px;
            font-size: 0.9em;
            line-height: 1.3;
            word-wrap: break-word;
            overflow-wrap: break-word;
            max-height: 150px;
            overflow-y: auto;
        }}
        
        .user-id-badge {{
            display: inline-block;
            padding: 2px 6px;
            border-radius: 10px;
            font-size: 0.75em;
            font-weight: bold;
            margin-right: 5px;
            color: white;
            text-shadow: 0 1px 2px rgba(0,0,0,0.2);
        }}
        
        .bot-message {{
            background: #f1f8e9;
            border-left: 3px solid #8bc34a;
            padding: 4px 6px;
            border-radius: 3px;
            margin-bottom: 3px;
            font-size: 0.9em;
            line-height: 1.3;
            word-wrap: break-word;
            overflow-wrap: break-word;
            max-height: 200px;
            overflow-y: auto;
        }}
        
        .bot-message .message-text {{
            margin-bottom: 3px;
        }}
        
        .buttons {{
            margin-top: 5px;
            padding-top: 5px;
            border-top: 1px solid #ddd;
        }}
        
        .button {{
            display: inline-block;
            padding: 2px 6px;
            margin: 2px;
            background: #667eea;
            color: white;
            border-radius: 3px;
            font-size: 0.75em;
            line-height: 1.2;
        }}
        
        .error-message {{
            padding: 8px 12px;
            background: #ffebee;
            color: #c62828;
            border-left: 3px solid #c62828;
            margin: 8px 12px;
            border-radius: 3px;
            font-size: 0.85em;
        }}
        
        .timestamp {{
            font-size: 0.75em;
            color: #999;
            margin-top: 3px;
        }}
        
        .conversation-table-wrapper {{
            overflow-x: auto;
            margin: 8px 0;
        }}
        
        @media print {{
            body {{
                background: white;
            }}
            .container {{
                box-shadow: none;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚗 Hiker Bot - Test Report</h1>
            <div class="subtitle">Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>
        </div>
        
        {self._generate_summary()}
        
        {self._generate_flows()}
    </div>
</body>
</html>"""
        return html
    
    def _generate_summary(self) -> str:
        """Generate summary section"""
        total = len(self.report_data)
        passed = sum(1 for flow in self.report_data if flow['success'])
        failed = total - passed
        
        return f"""
        <div class="summary">
            <div class="summary-item">
                <div class="number">{total}</div>
                <div class="label">Total Flows</div>
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
    
    def _generate_flows(self) -> str:
        """Generate all flow sections"""
        flows_html = []
        
        for idx, flow in enumerate(self.report_data, 1):
            status_class = "success" if flow['success'] else "failed"
            status_text = "✅ PASSED" if flow['success'] else "❌ FAILED"
            
            # Build conversation table with user ID for coloring
            table_html = self._build_conversation_table(flow['messages'], flow.get('user_id'))
            
            # Build error message if failed
            error_html = ""
            if not flow['success'] and flow.get('error_message'):
                error_html = f'<div class="error-message"><strong>Error:</strong> {flow["error_message"]}</div>'
            
            # Add user ID with color badge if available
            user_id_html = ""
            user_id = flow.get('user_id')
            if user_id:
                # Get user color for badge
                colors = self._get_user_color(user_id)
                badge_bg_color = colors[1]  # Use darker border color for badge
                user_id_html = f'<div style="font-size: 0.85em; margin-top: 3px; opacity: 0.9;">👤 User ID: <span class="user-id-badge" style="background: {badge_bg_color};">{user_id}</span></div>'
            
            flow_html = f"""
            <div class="flow-section">
                <div class="flow-header {status_class}">
                    <div>
                        <div class="flow-title">Flow {idx}: {flow['flow_name']}</div>
                        {user_id_html}
                    </div>
                    <div class="flow-status">{status_text}</div>
                </div>
                <div class="flow-description">{flow['flow_description']}</div>
                {error_html}
                {table_html}
            </div>
            """
            flows_html.append(flow_html)
        
        return "\n".join(flows_html)
    
    def _build_conversation_table(self, messages: List[Dict[str, Any]], user_id: str = None) -> str:
        """Build horizontal conversation table"""
        if not messages or not messages[0].get('exchanges'):
            return '<div style="padding: 20px; text-align: center; color: #999;">No messages</div>'
        
        # Get all exchanges from the first (and only) message entry
        exchanges = messages[0].get('exchanges', [])
        
        if not exchanges:
            return '<div style="padding: 20px; text-align: center; color: #999;">No exchanges</div>'
        
        # Get user color if user_id provided
        user_bg_color = "#e3f2fd"
        user_border_color = "#2196f3"
        if user_id:
            colors = self._get_user_color(user_id)
            user_bg_color = colors[0]
            user_border_color = colors[1]
        
        # Build table header - one column per exchange
        header_cells = []
        for i in range(len(exchanges)):
            header_cells.append(f"<th>Step {i+1}</th>")
        
        # Build user messages row
        user_row = ["<td><strong>User Messages</strong></td>"]
        bot_row = ["<td><strong>Bot Responses</strong></td>"]
        
        for exchange in exchanges:
            # User message cell with user-specific color
            user_msg = exchange.get('user_message', '')
            user_cell = f'<div class="user-message" style="background: {user_bg_color}; border-left-color: {user_border_color};">{self._escape_html(user_msg)}</div>'
            user_row.append(f"<td>{user_cell}</td>")
            
            # Bot response cell
            bot_msg = exchange.get('bot_message', '')
            buttons = exchange.get('buttons', [])
            
            bot_cell = '<div class="bot-message">'
            if bot_msg:
                bot_cell += f'<div class="message-text">{self._escape_html(bot_msg)}</div>'
            
            if buttons:
                bot_cell += '<div class="buttons">'
                for btn in buttons:
                    # Handle different button formats
                    if isinstance(btn, dict):
                        btn_title = btn.get('title', btn.get('id', ''))
                        if 'reply' in btn and isinstance(btn['reply'], dict):
                            btn_title = btn['reply'].get('title', btn['reply'].get('id', ''))
                    else:
                        btn_title = str(btn)
                    bot_cell += f'<span class="button">{self._escape_html(btn_title)}</span>'
                bot_cell += '</div>'
            
            bot_cell += '</div>'
            bot_row.append(f"<td>{bot_cell}</td>")
        
        table_html = f"""
        <div class="conversation-table-wrapper">
        <table class="conversation-table">
            <thead>
                <tr>
                    <th>Type</th>
                    {''.join(header_cells)}
                </tr>
            </thead>
            <tbody>
                <tr>
                    {''.join(user_row)}
                </tr>
                <tr>
                    {''.join(bot_row)}
                </tr>
            </tbody>
        </table>
        </div>
        """
        
        return table_html
    
    def _escape_html(self, text: str) -> str:
        """Escape HTML special characters"""
        if not text:
            return ""
        return (text.replace('&', '&amp;')
                   .replace('<', '&lt;')
                   .replace('>', '&gt;')
                   .replace('"', '&quot;')
                   .replace("'", '&#39;')
                   .replace('\n', '<br>'))
    
    def save_report(self, output_dir: str = "test_reports"):
        """Save the HTML report to file"""
        # Create output directory if it doesn't exist
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        output_path = os.path.join(output_dir, self.output_file)
        
        html_content = self.generate_html()
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"\n📊 Test report saved to: {output_path}")
        return output_path


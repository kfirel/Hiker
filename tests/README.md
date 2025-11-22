# 🧪 Hiker Bot Testing Platform

This directory contains a comprehensive testing platform for the Hiker WhatsApp Bot. The platform allows you to test all conversation flows without using the actual WhatsApp API.

## 📋 Overview

The testing platform includes:

- **YAML Input File** (`test_inputs.yml`) - Contains N conversation flow scenarios
- **Mock WhatsApp Client** - Simulates WhatsApp API calls without actually sending messages
- **Pytest Test Suite** - Runs all flows and generates reports
- **HTML Report Generator** - Creates beautiful HTML reports with horizontal conversation tables

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

This will install pytest and pyyaml along with other dependencies.

### 2. Run All Tests

```bash
# Run all conversation flows
pytest tests/test_conversation_flows.py -v

# Run with more verbose output
pytest tests/test_conversation_flows.py -v -s

# Run a specific flow by index
pytest tests/test_conversation_flows.py::test_individual_flow[0] -v
```

### 3. View Test Report

After running tests, an HTML report will be generated in `test_reports/test_report.html`. Open this file in your browser to view:

- Summary statistics (total flows, passed, failed)
- Each conversation flow displayed in a horizontal table format
- User messages and bot responses side by side
- Button interactions
- Error messages for failed flows

## 📝 Test Input Format

The `test_inputs.yml` file contains conversation flows in the following format:

```yaml
flows:
  - name: "Flow Name"
    description: "Description of what this flow tests"
    messages:
      - "User message 1"
      - "User message 2"
      - "User message 3"
      # ... more messages
```

Each flow represents a complete conversation from start to finish. The test runner will:

1. Clear user data for a fresh start
2. Send each message in sequence
3. Capture bot responses and buttons
4. Record any errors
5. Generate a report

## 🎯 Example Flows

The test suite includes 10 pre-configured flows covering:

1. **New Hitchhiker - Immediate Ride Request** - Complete registration and ride request
2. **New Driver - With Routine** - Driver registration with driving routine
3. **Both User Type** - User who is both hitchhiker and driver
4. **Registered Hitchhiker** - Returning user requesting a ride
5. **Registered Driver** - Driver offering a ride
6. **Validation Test** - Testing input validation with invalid settlement
7. **Restart Command** - Testing restart functionality
8. **Multiple Routines** - Driver with multiple routine destinations
9. **Default Destination** - Hitchhiker using default destination
10. **Special Commands** - Testing help, menu, and restart commands

## 📊 Report Format

The HTML report displays each conversation in a horizontal table:

| Type | Step 1 | Step 2 | Step 3 | ... |
|------|--------|--------|--------|-----|
| **User Messages** | Message 1 | Message 2 | Message 3 | ... |
| **Bot Responses** | Response 1<br>Buttons | Response 2<br>Buttons | Response 3<br>Buttons | ... |

Each cell shows:
- **User messages** in blue boxes
- **Bot responses** in green boxes
- **Buttons** as clickable button elements
- **Error messages** highlighted in red if a flow fails

## 🔧 Customization

### Adding New Test Flows

Edit `test_inputs.yml` and add a new flow:

```yaml
flows:
  - name: "My New Flow"
    description: "Testing a new scenario"
    messages:
      - "First message"
      - "Second message"
      # ... more messages
```

### Modifying Report Style

Edit `tests/report_generator.py` to customize:
- Colors and styling
- Table layout
- Additional information displayed

### Running Specific Tests

```bash
# Run only the first flow
pytest tests/test_conversation_flows.py::test_individual_flow[0] -v

# Run flows 0-4
pytest tests/test_conversation_flows.py::test_individual_flow[0-4] -v

# Run with HTML coverage report
pytest tests/test_conversation_flows.py --html=report.html --self-contained-html
```

## 🐛 Debugging

If a test fails:

1. Check the HTML report for detailed error messages
2. Run the specific flow individually:
   ```bash
   pytest tests/test_conversation_flows.py::test_individual_flow[0] -v -s
   ```
3. Check the conversation history in the report
4. Verify the flow definition in `test_inputs.yml`

## 📁 File Structure

```
tests/
├── __init__.py
├── README.md                    # This file
├── conftest.py                  # Pytest fixtures and configuration
├── test_inputs.yml              # YAML file with test scenarios
├── mock_whatsapp_client.py      # Mock WhatsApp API client
├── report_generator.py          # HTML report generator
├── test_conversation_flows.py   # Main test file
└── test_reports/                # Generated reports (created automatically)
    └── test_report.html
```

## ✅ Features

- ✅ No WhatsApp API required - all tests run internally
- ✅ Mock WhatsApp client for safe testing
- ✅ YAML-based test input for easy maintenance
- ✅ Beautiful HTML reports with horizontal tables
- ✅ Comprehensive flow coverage
- ✅ Error tracking and reporting
- ✅ Isolated test execution (each flow gets fresh state)

## 🎨 Report Features

- **Summary Dashboard** - Quick overview of test results
- **Flow-by-Flow Breakdown** - Detailed view of each conversation
- **Horizontal Tables** - Easy-to-read conversation flow
- **Button Visualization** - See all interactive buttons
- **Error Highlighting** - Failed flows clearly marked
- **Responsive Design** - Works on desktop and mobile

## 📝 Notes

- Each test flow uses a unique phone number to avoid state conflicts
- User data is cleared at the start of each flow
- The mock WhatsApp client stores all messages for inspection
- Reports are saved in `test_reports/` directory

## 🤝 Contributing

When adding new test flows:

1. Add the flow to `test_inputs.yml`
2. Give it a descriptive name and description
3. Include all user messages in sequence
4. Run tests to verify it works
5. Check the HTML report to ensure proper formatting

---

**Happy Testing! 🚀**




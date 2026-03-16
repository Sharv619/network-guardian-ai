# Network Guardian AI - MCP Integration Guide

## Overview

This guide explains how to set up and use the Network Guardian AI MCP (Model Context Protocol) server to integrate the threat detection system with AI assistants like Claude Desktop.

## What is MCP?

Model Context Protocol (MCP) is an open protocol that enables AI assistants to securely interact with external systems and data sources. It provides a standardized way for AI models to:
- Access tools and functions
- Query resources
- Perform actions on behalf of users

## Prerequisites

1. **Python 3.12+** installed
2. **Network Guardian AI** backend configured
3. **MCP Client** (e.g., Claude Desktop, MCP Inspector)

## Installation

### 1. Install Dependencies

```bash
# Navigate to the project directory
cd /home/lade/Hackathons/network-guardian-ai

# Install MCP dependencies
pip install mcp fastmcp

# Or install all dependencies including MCP
pip install -r backend/requirements.txt
```

### 2. Configure Environment Variables

Ensure your `.env` file is properly configured:

```bash
# Required for AI analysis
GEMINI_API_KEY=your_google_ai_studio_key

# Optional but recommended
GOOGLE_SHEET_ID=your_spreadsheet_id
GOOGLE_SHEETS_CREDENTIALS='{ "type": "service_account", ... }'

# AdGuard Home integration (optional)
ADGUARD_URL=http://localhost:8080
ADGUARD_USER=admin
ADGUARD_PASS=your_password

# Polling interval (seconds)
POLL_INTERVAL=30
```

## Available Tools

The MCP server exposes the following tools:

### Analysis Tools

#### `analyze_domain`
Analyze a domain for security threats using the full Network Guardian pipeline.

**Parameters:**
- `domain` (string): The domain name to analyze
- `full_analysis` (boolean): Include Gemini AI analysis (default: false)

**Example:**
```python
await analyze_domain("suspicious-domain.com", full_analysis=True)
```

**Returns:**
```json
{
  "domain": "suspicious-domain.com",
  "risk_score": 75,
  "category": "Tracker",
  "entropy": 4.2,
  "is_suspicious": true,
  "analysis_method": "gemini_ai",
  "gemini_analysis": {...}
}
```

#### `get_entropy_analysis`
Get Shannon entropy analysis for a domain.

**Parameters:**
- `domain` (string): The domain to analyze

**Example:**
```python
await get_entropy_analysis("x7k9m2p4.com")
```

#### `find_similar_threats`
Find similar threats using vector similarity search.

**Parameters:**
- `domain` (string): The domain to find similar threats for
- `limit` (integer): Maximum results (default: 5)

**Example:**
```python
await find_similar_threats("malware-domain.com", limit=10)
```

#### `get_threat_cluster`
Get threat cluster information for a domain.

**Parameters:**
- `domain` (string): The domain to analyze

**Example:**
```python
await get_threat_cluster("suspicious-domain.com")
```

### Retrieval Tools

#### `get_recent_threats`
Retrieve recently detected threats from the database.

**Parameters:**
- `limit` (integer): Maximum number of threats (default: 20, max: 100)

**Example:**
```python
await get_recent_threats(limit=50)
```

#### `get_threat_stats`
Get comprehensive threat statistics and system metrics.

**Example:**
```python
await get_threat_stats()
```

#### `get_knowledge_base_stats`
Get knowledge base and pattern learning statistics.

**Example:**
```python
await get_knowledge_base_stats()
```

### System Tools

#### `get_system_status`
Check system health, configuration, and component status.

**Example:**
```python
await get_system_status()
```

#### `get_config`
Retrieve system configuration (sensitive data redacted).

**Example:**
```python
await get_config()
```

#### `sync_to_google_sheets`
Manually trigger Google Sheets synchronization.

**Parameters:**
- `domain` (string, optional): Specific domain to sync

**Example:**
```python
await sync_to_google_sheets("example.com")
await sync_to_google_sheets()  # Sync all recent
```

### Interaction Tools

#### `chat_with_system`
Chat with the Network Guardian AI system.

**Parameters:**
- `message` (string): Your question or message
- `context` (string, optional): Additional context

**Example:**
```python
await chat_with_system("What are the top threats detected today?")
```

## Resources

The MCP server also exposes resources that can be subscribed to:

- `threats://recent` - Real-time stream of recent threats
- `stats://current` - Current threat statistics
- `status://system` - System health status

## Configuration

### Claude Desktop Setup

Add the following to your Claude Desktop configuration:

**macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows:** `%APPDATA%\Claude\claude_desktop_config.json`
**Linux:** `~/.config/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "network-guardian-ai": {
      "command": "python",
      "args": ["/home/lade/Hackathons/network-guardian-ai/mcp_server.py"],
      "cwd": "/home/lade/Hackathons/network-guardian-ai",
      "env": {
        "PYTHONPATH": "/home/lade/Hackathons/network-guardian-ai"
      }
    }
  }
}
```

### Alternative: Using Virtual Environment

If you're using a virtual environment:

```json
{
  "mcpServers": {
    "network-guardian-ai": {
      "command": "/home/lade/Hackathons/network-guardian-ai/venv/bin/python",
      "args": ["/home/lade/Hackathons/network-guardian-ai/mcp_server.py"],
      "cwd": "/home/lade/Hackathons/network-guardian-ai"
    }
  }
}
```

### Using MCP Inspector

For development and testing:

```bash
# Install MCP Inspector
npx @modelcontextprotocol/inspector

# Run the server with inspector
python mcp_server.py
```

Then open the Inspector UI to test tools interactively.

## Running the Server

### Standalone Mode

```bash
# Activate virtual environment (if using one)
source venv/bin/activate

# Run the MCP server
python mcp_server.py
```

### Expected Output

```
============================================================
Network Guardian AI - MCP Server
============================================================

Available Tools:
  • analyze_domain - Analyze a domain for threats
  • get_recent_threats - Retrieve recent detected threats
  • get_threat_stats - Get threat statistics and trends
  • get_system_status - Check system health and status
  • get_config - Retrieve system configuration
  • find_similar_threats - Find similar threats using vector search
  • get_threat_cluster - Get threat cluster information
  • get_entropy_analysis - Get Shannon entropy analysis
  • sync_to_google_sheets - Manually trigger Google Sheets sync
  • get_knowledge_base_stats - Get knowledge base statistics
  • chat_with_system - Chat with the AI system

Resources:
  • threats://recent - Recent threats stream
  • stats://current - Current statistics
  • status://system - System status

Configuration Status:
  • AdGuard: ✓
  • Gemini AI: ✓
  • Google Sheets: ✓
  • Notion: ✗

Server running. Press Ctrl+C to stop.
============================================================
```

## Usage Examples

### Example 1: Analyze a Suspicious Domain

**User:** "Analyze this domain: suspicious-tracker.example.com"

**Assistant:** Uses `analyze_domain` tool
```python
result = await analyze_domain("suspicious-tracker.example.com", full_analysis=True)
```

**Response:**
```
I've analyzed suspicious-tracker.example.com:

- Risk Score: 75/100 (High)
- Category: Tracker
- Entropy: 3.8 (Normal)
- Anomaly Score: -0.15 (Anomalous)

The domain shows characteristics of a tracking service with anomalous patterns.
Gemini AI analysis suggests it's likely a privacy-invasive tracker.
```

### Example 2: Get Recent Threats

**User:** "Show me the recent threats detected"

**Assistant:** Uses `get_recent_threats` tool
```python
threats = await get_recent_threats(limit=10)
```

### Example 3: System Health Check

**User:** "Is the system healthy?"

**Assistant:** Uses `get_system_status` tool
```python
status = await get_system_status()
```

### Example 4: Find Related Threats

**User:** "Find domains similar to malware-campaign.com"

**Assistant:** Uses `find_similar_threats` tool
```python
similar = await find_similar_threats("malware-campaign.com", limit=5)
```

## Troubleshooting

### Server Won't Start

**Issue:** Module not found errors

**Solution:**
```bash
# Ensure you're in the project directory
cd /home/lade/Hackathons/network-guardian-ai

# Install dependencies
pip install -r backend/requirements.txt

# Verify Python path
python -c "import sys; print(sys.path)"
```

### Tools Not Available in Claude Desktop

**Issue:** Tools don't appear in Claude Desktop

**Solution:**
1. Check the configuration file path is correct
2. Verify the Python path in config matches your installation
3. Restart Claude Desktop completely
4. Check Claude Desktop logs for errors

### Configuration Errors

**Issue:** "Missing environment variables" warnings

**Solution:**
1. Copy `.env.example` to `.env`
2. Fill in required values (at minimum `GEMINI_API_KEY`)
3. Restart the MCP server

### Connection Issues

**Issue:** MCP client can't connect to server

**Solution:**
1. Ensure the server is running (`python mcp_server.py`)
2. Check that the path in MCP config is absolute
3. Verify file permissions
4. Try running with full Python path

## Security Considerations

- **API Keys:** Never share your `.env` file or commit it to version control
- **Access Control:** MCP server runs locally with your user permissions
- **Data Privacy:** Threat data is stored in your local database and Google Sheets
- **Network Access:** Server only binds to localhost by default

## Performance Tips

1. **Use Caching:** The system caches analysis results for 5 minutes
2. **Batch Operations:** Use `get_recent_threats` instead of multiple individual lookups
3. **Limit Vector Searches:** Keep `limit` parameter reasonable (<20)
4. **Full Analysis:** Only use `full_analysis=True` when Gemini AI insight is needed

## Advanced Usage

### Custom Tool Extensions

You can extend the MCP server with custom tools:

```python
@mcp.tool()
async def my_custom_tool(param: str) -> Dict[str, Any]:
    """Custom tool documentation"""
    # Your implementation
    return {"result": "value"}
```

### Resource Subscriptions

Subscribe to real-time updates:

```python
# In your MCP client
subscribe("threats://recent")
```

### Prompts (Future)

Define reusable prompts for common tasks:

```python
@mcp.prompt()
def threat_analysis_prompt(domain: str) -> str:
    return f"Analyze the security threat: {domain}"
```

## Support

For issues or questions:
1. Check the [README.md](README.md) for general project info
2. Review the [PRD.md](PRD.md) for system architecture
3. Check the [SAMPLE_DATA.md](SAMPLE_DATA.md) for example data formats

## Updates

To update the MCP server:
```bash
# Pull latest changes (if using git)
git pull

# Reinstall dependencies
pip install -r backend/requirements.txt --upgrade

# Restart the server
```

---

**Last Updated:** 2026-02-26
**Version:** 1.0.0

# MCP Client Configuration Examples

This directory contains configuration examples for various MCP clients.

## Claude Desktop

### Linux
Location: `~/.config/Claude/claude_desktop_config.json`

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

### macOS
Location: `~/Library/Application Support/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "network-guardian-ai": {
      "command": "python3",
      "args": ["/Users/username/projects/network-guardian-ai/mcp_server.py"],
      "cwd": "/Users/username/projects/network-guardian-ai"
    }
  }
}
```

### Windows
Location: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "network-guardian-ai": {
      "command": "python",
      "args": ["C:\\projects\\network-guardian-ai\\mcp_server.py"],
      "cwd": "C:\\projects\\network-guardian-ai"
    }
  }
}
```

## Alternative: Using Absolute Python Path

For more reliable execution, use the absolute path to your Python interpreter:

### Linux (with virtualenv)
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

### Find Python Path
```bash
# Get absolute path to Python
which python
# or for virtualenv
source venv/bin/activate
which python
```

## Using Environment Variables

If you need to set specific environment variables:

```json
{
  "mcpServers": {
    "network-guardian-ai": {
      "command": "python",
      "args": ["mcp_server.py"],
      "cwd": "/home/lade/Hackathons/network-guardian-ai",
      "env": {
        "PYTHONPATH": "/home/lade/Hackathons/network-guardian-ai",
        "GEMINI_API_KEY": "your_key_here",
        "PATH": "/home/lade/Hackathons/network-guardian-ai/venv/bin:/usr/bin:/bin"
      }
    }
  }
}
```

**Note:** It's better to use a `.env` file than to put API keys in the config.

## Troubleshooting

### Server Not Starting

Check the Claude Desktop logs:
- **Linux:** `~/.config/Claude/logs/`
- **macOS:** `~/Library/Logs/Claude/`
- **Windows:** `%APPDATA%\Claude\logs\`

Common issues:
1. **Python not found:** Use absolute path to Python
2. **Module not found:** Ensure dependencies are installed
3. **Path issues:** Use absolute paths, not relative

### Permission Denied

Make sure the script is executable:
```bash
chmod +x mcp_server.py
```

### Virtual Environment Issues

If using a virtual environment, ensure it's activated when installing:
```bash
source venv/bin/activate
pip install -r backend/requirements.txt
```

Then use the venv Python path in the config.

## Testing the Connection

After configuring, restart Claude Desktop and try:
- "Check the system status using Network Guardian"
- "Analyze the domain example.com"
- "Show me recent threats"

If the tools are available, Claude will use them automatically.

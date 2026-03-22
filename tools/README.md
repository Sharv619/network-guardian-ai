# AI Agent Testing & Evaluation Tools

This directory contains configurations for integrating external npx CLI tools into Network Guardian AI for comprehensive testing, evaluation, and security auditing.

## Available Tools

### 1. PromptFoo (LLM Evals & Red Teaming)

**Purpose:** Evaluate and red-team LLM applications

**Install/Run:**
```bash
npm run test:promptfoo        # Run evaluations
npm run test:promptfoo:watch  # Watch mode
npm run test:promptfoo:redteam # Red team mode
```

**Config:** `promptfooconfig.yaml`

**Features:**
- Test prompts, agents, and RAGs
- Red teaming / pentesting / vulnerability scanning
- Compare GPT, Claude, Gemini, Llama performance
- CI/CD integration

---

### 2. HackMyAgent (Security Toolkit)

**Purpose:** 163 security checks for AI agents

**Install/Run:**
```bash
npm run test:hackmyagent       # Quick security scan
npm run test:hackmyagent:full   # Full security dashboard
npx hackmyagent secure          # Direct CLI
npx opena2a-cli review         # Full review
```

**Config:** `tools/hackmyagent.yaml`

**Security Checks:**
- Credentials exposure detection
- Config integrity verification
- Shadow AI detection
- MCP server security
- API key exposure
- Tool permissions audit
- Context isolation

---

### 3. Agent Duelist (Model Benchmarking)

**Purpose:** Benchmark LLM providers on agent tasks

**Install/Run:**
```bash
npm run test:duelist:init       # Initialize config
npm run test:duelist            # Run benchmarks
npx duelist init                # Direct CLI
npx duelist run --config tools/duelist-config.yaml
```

**Config:** `tools/duelist-config.yaml`

**Features:**
- Compare multiple LLM providers
- Structured results (correctness, latency, tokens, cost)
- Console output with color ranking
- Per-task winner tracking

---

### 4. Vercel Agent Eval (Agent Testing)

**Purpose:** Test AI coding agents on your framework

**Install/Run:**
```bash
npm run test:agent-eval:init    # Initialize project
npm run test:agent-eval         # Run evaluations
npx @vercel/agent-eval init my-agent-evals
npx @vercel/agent-eval run
```

**Config:** `tools/agent-eval.yaml`

**Features:**
- Measure pass rates across models
- Compare techniques (MCP servers, documentation)
- CI/CD integration
- Framework-specific testing

---

### 5. Gemini CLI (Google AI Agent)

**Purpose:** Google's AI agent with Gemini in terminal

**Install/Run:**
```bash
npm run test:gemini
npx @google/gemini-cli
```

**Features:**
- Direct Gemini access in terminal
- MCP client support
- 98K GitHub stars

---

## Quick Start

### Run All Tests
```bash
npm run test:all
```

### Individual Test Commands
```bash
# LLM Evaluation
npm run test:promptfoo

# Security Audit
npm run test:hackmyagent

# Model Benchmarking
npm run test:duelist

# Agent Testing
npm run test:agent-eval
```

---

## Tool Comparison

| Tool | Purpose | Best For | Stars |
|------|---------|----------|-------|
| PromptFoo | LLM Evals | Testing prompts & RAGs | 17K |
| HackMyAgent | Security | Agent vulnerability scanning | 23 |
| Agent Duelist | Benchmarking | Comparing LLM providers | 4 |
| Agent Eval | Agent Testing | Framework testing | 126 |
| Gemini CLI | AI Agent | Gemini-powered CLI | 98K |

---

## Integration with Network Guardian AI

These tools integrate with the Network Guardian AI backend:

- **Backend API:** `http://localhost:8000/analyze`
- **Health Check:** `http://localhost:8000/health`
- **WebSocket:** `ws://localhost:8000/ws`

### Testing the API
```bash
# Start backend first
cd backend && python -m uvicorn main:app --reload

# Run PromptFoo tests
npm run test:promptfoo
```

---

## Environment Variables

Some tools require API keys:

```bash
# OpenAI (for some benchmarks)
OPENAI_API_KEY=sk-...

# Anthropic (for Claude evaluation)
ANTHROPIC_API_KEY=sk-ant-...

# Google Gemini
GEMINI_API_KEY=...
```

---

## CI/CD Integration

Add to your CI pipeline:

```yaml
# .github/workflows/ai-tools.yml
- name: Run AI Tests
  run: |
    npm install
    npm run test:promptfoo
    npm run test:hackmyagent
```

---

## Results

Test results are saved to:
- `promptfoo-results.json` - PromptFoo output
- `tools/hackmyagent-results.json` - Security scan results
- `tools/duelist-results.json` - Benchmark results
- `tools/agent-eval-results.json` - Agent test results

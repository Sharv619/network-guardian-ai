# Network Guardian AI - Next Phase Plan

## Current Status ✅

| Component | Status |
|-----------|--------|
| Backend | ✅ Working (imports OK) |
| MCP Server | ✅ Starts (waits for connections) |
| Frontend | ✅ Built |
| PromptFoo | ✅ Installed (needs API key) |
| Impeccable | ✅ Design guidelines added |
| ruff | ✅ Linting works |

## Issues Found & Fixed

### Fixed:
1. ✅ MCP config Windows path - Updated to Windows paths
2. ✅ MCP server import error - Fixed `calculate_digit_ratio` → `is_dga`, `extract_domain_features`
3. ✅ Missing dependencies - Installed gspread, mcp, fastmcp

### Remaining Issues:
1. ⚠️ **sentence-transformers** - Not installed (Windows Long Path issue)
2. ⚠️ **torch** - Not installed (Windows Long Path issue)  
3. ⚠️ **PromptFoo** - Needs OPENAI_API_KEY environment variable
4. ⚠️ **Ruff warnings** - 3 B904 exceptions (should use `raise ... from err`)

---

## Next Phase Roadmap

### Phase 1: Polish the Frontend (Week 1)
Using Impeccable design principles:

- [ ] **Audit current UI** - Run `/audit` command on Dashboard
- [ ] **Fix typography** - Replace generic fonts with distinctive choices
- [ ] **Improve color scheme** - Add OKLCH colors, fix gray-on-colored issues
- [ ] **Polish interactions** - Better loading states, animations
- [ ] **Responsive design** - Mobile-first improvements

### Phase 2: Enhance Testing (Week 2)
Using PromptFoo:

- [ ] **Set up eval environment** - Add OPENAI_API_KEY or GEMINI_API_KEY
- [ ] **Create test cases** - Add more domain test cases
- [ ] **Run evaluations** - Test Gemini analyzer quality
- [ ] **CI/CD integration** - Add to GitHub Actions

### Phase 3: Infrastructure (Week 3)
Optional improvements:

- [ ] **Fix torch installation** - Enable Windows Long Path support
- [ ] **Add OpenViking** - For better vector memory (optional)
- [ ] **Docker setup** - Containerize for easier deployment

---

## Quick Wins - Actions Needed

1. **Set API Key for PromptFoo:**
   ```bash
   export OPENAI_API_KEY=your_key_here
   # or
   promptfoo eval
   ```

2. **Run backend:**
   ```bash
   cd backend
   python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
   ```

3. **Run frontend:**
   ```bash
   cd frontend
   npm run dev
   ```

4. **Use Impeccable:**
   - Reference DESIGN.md when working with AI coding agents
   - Use `/audit`, `/polish`, `/normalize` commands

---

## Files Modified/Created

| File | Action |
|------|--------|
| `claude_desktop_config.json` | Fixed Windows paths |
| `mcp_client_configs/claude_desktop_windows.json` | Created |
| `DESIGN.md` | Created - Impeccable guidelines |
| `promptfooconfig.yaml` | Created - Test config |
| `mcp_server.py` | Fixed imports |
| `backend/requirements.txt` | Commented out sentence-transformers |

---

## Recommended Priority

1. **Now**: Set up API key, test PromptFoo
2. **This week**: Polish frontend with Impeccable
3. **Next week**: Add more test cases, run evaluations
4. **Optional**: Fix torch/transformers if needed

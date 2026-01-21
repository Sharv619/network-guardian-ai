
# Changelog

All notable changes to this project will be documented in this file.

## [1.2.0] - Frontend Mock API Layer

### Added

- **Mock API Service:** Created a new mock API service layer (`api/mockApi.ts`) to simulate backend responses for both threat analysis and chat.
  - This allows for complete frontend development and testing without a live backend.
  - The mock API simulates network latency using `setTimeout` for a more realistic feel.
- **Project Documentation:** Updated this `CHANGELOG.md`.

### Changed

- **`ThreatAnalysisPanel.tsx`:** Refactored to fetch data from the new mock API service instead of directly calling the Gemini service.
- **`useChat.ts`:** Refactored the chat hook to use the mock chat streaming service.
- **`index.html`:** Cleaned up unused importmap entries.

### Removed

- **Backend Skeleton:** Removed all Python/FastAPI backend files to refocus on a pure frontend architecture as requested.

## [1.1.0] - Initial Refactor

### Added

- **Frontend `useChat` Hook:** Created a new custom React hook (`hooks/useChat.ts`) to abstract away all chat state and logic from the UI component.
- **Markdown Rendering:** Integrated `react-markdown` and `remark-gfm` to render Markdown in the AI's chat responses.

### Changed

- **`ChatPanel.tsx`:** Refactored the component to be a "dumb" presentational component that consumes the `useChat` hook. This significantly simplifies its code and improves readability.

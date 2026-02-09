# Changelog

All notable changes to this project will be documented in this file.

## [1.3.0] - Phase 2: Anomaly Detection & Testing

### Added

- **Isolation Forest ML Model:** Integrated a new anomaly detection engine using `scikit-learn`'s `IsolationForest` to identify unusual network behavior in real-time. This provides a behavior-based detection layer.
- **Host-Gateway Networking:** Established a robust networking bridge between the Docker environment and the host machine, ensuring the poller can always reach the AdGuard instance.
- **Automated Testing Suite:** Initialized a comprehensive testing suite for the backend using `pytest`.
    - Added unit tests for ML heuristics (`test_heuristics.py`).
    - Added integration tests for API endpoints (`test_router.py`).

### Changed

- **UI Polish:** The dashboard now visually highlights anomalous traffic with a pulsing gold border and displays the anomaly score for quick identification.

<!--
**Learning Tip: Hybrid Defense**

By combining AdGuard (Signature-based), Isolation Forest (Behavior-based), and Gemini (Semantic-based), we have built a Defense-in-Depth architecture that catches threats at multiple layers.
-->

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
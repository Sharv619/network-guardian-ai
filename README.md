
# Network Guardian AI

A "Live" Threat Intelligence Dashboard that monitors network traffic from AdGuard Home, analyzes it with Google Gemini, and logs threats to Notion.

## Prerequisites

1.  **Google Gemini API Key**: [Get it here](https://aistudio.google.com/).
2.  **Notion Integration**:
    *   Create a new Integration at [Notion Developers](https://www.notion.so/my-integrations).
    *   Get the `NOTION_TOKEN`.
    *   Share your target Database with this Integration connection.
    *   Get the `DATABASE_ID` from the URL.
3.  **AdGuard Home**: Running instance with credentials.

## Deployment

1.  **Set Environment Variables**
    Create a `.env` file in the root:
    ```bash
    GEMINI_API_KEY=your_key
    NOTION_TOKEN=your_token
    NOTION_DATABASE_ID=your_db_id
    ADGUARD_URL=http://your_adguard_ip
    ADGUARD_USER=your_user
    ADGUARD_PASS=your_pass
    POLL_INTERVAL=30
    ```

2.  **Run the Stack**
    ```bash
    docker-compose up --build
    ```

3.  **Access the Dashboard**
    Open `http://localhost:3000`.

## Features

*   **Live Feed**: Real-time stream of blocked domains and their AI verdict.
*   **Manual Analysis**: Paste any domain to get an instant risk assessment.
*   **Hacker UI**: Dark mode, monospace fonts, and status badges.

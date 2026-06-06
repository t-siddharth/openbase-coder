# iOS App Tabs

The Openbase iOS app (`ios/Openbase/OpenbaseApp.swift`) has four tabs backed by this CLI server.

## 1. Call Tab

Label: `Call` (`AgentCallTabView`)

Responsibilities:

- Hosts the primary LiveKit call UI
- Requests room tokens from the local CLI server
- Connects voice turns to the shared Codex app-server thread through the LiveKit worker

Requirements:

- CLI auth token configured in Account tab
- Active network configuration selected

## 2. Threads Tab

Label: `Threads` (`CodeThreadsView`)

Responsibilities:

- Lists active Codex threads
- Creates threads from recent projects
- Archives threads
- Shows the current turn and turn history
- Handles realtime turn events over WebSocket

CLI endpoints used:

- `GET/POST /api/threads/`
- `GET/DELETE /api/threads/<thread_id>/`
- `POST /api/threads/<thread_id>/interrupt/`
- `POST /api/threads/<thread_id>/turns/`
- `GET /api/projects/recent/`
- `ws://.../ws/threads/`
- `ws://.../ws/threads/<thread_id>/`

Requirements:

- CLI auth token configured in Account tab
- Local coder URL configured and reachable

## 3. Diff Tab

Label: `Diff` (`BrowserView`)

Responsibilities:

- Opens web console diff UI in `WKWebView`
- Loads `/dashboard/diff?token=<cli_token>`
- Injects token into browser `localStorage` for console auth

Requirements:

- CLI auth token configured
- Local coder URL configured and reachable
- Console assets available (built by setup/server)

## 4. Account Tab

Label: `Account` (`HomeView`)

Responsibilities:

- Openbase account/security screens (email, password, sessions, MFA, providers)
- CLI token management (Keychain)
- Network configuration CRUD and active selection (UserDefaults)

Local persistence used by app:

- Keychain: `com.openbase.coder.cli.authtoken`
- UserDefaults: `openbase_agent_hosts`
- UserDefaults: `openbase_selected_host_id`

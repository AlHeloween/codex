# Cyber Safety Message Handling

ChatGPT backend flags high-risk cyber activity -> downgrade to safer model (gpt-5.3-codex -> gpt-5.2) -> app-server detects warning in EventMsg::Error.

Details from bespoke_event_handling.rs:

- is_safety_check_downgrade_warning(message): Checks phrase + "https://chatgpt.com/cyber" link

- If true, special handling in handle_error (record in turn_summary.last_error)

- Emits ServerNotification::Error with TurnError

```mermaid
sequenceDiagram
    participant Model
    participant ChatGPT as ChatGPT Backend
    participant AppServer as app-server
    participant User
    
    Model->>ChatGPT: Request (gpt-5.3-codex)
    ChatGPT-->>AppServer: EventMsg::Error<br/>"Your account flagged...<br/>downgraded to gpt-5.2<br/>https://chatgpt.com/cyber"
    AppServer->>Detect: is_safety_check_downgrade_warning
    Detect-->>AppServer: True
    AppServer->>Handle: handle_error<br/>turn_summary.last_error = TurnError
    AppServer->>Emit: ServerNotification::Error<br/>TurnStatus::Failed
    AppServer->>User: Warning Notification
    
    Note over AppServer: If not safety warning,<br/>normal error flow
```

# Anvil Logs API

The Lenina API now provides real-time access to Anvil's console output through RESTful endpoints.

## Endpoints

### GET /anvil/logs

Retrieve Anvil's console logs from the circular buffer (max 1000 lines).

**Query Parameters:**
- `lines` (int, default: 100): Number of recent lines to return (1-1000)
- `since` (int, optional): Return logs after this sequence number
- `format` (str, default: "markdown"): Output format - "markdown", "json", or "text"

**Example:**
```bash
# Get last 100 lines in markdown format
curl "http://localhost:8000/anvil/logs?lines=100"

# Get logs since sequence number 50
curl "http://localhost:8000/anvil/logs?since=50&lines=50"

# Get logs in JSON format
curl "http://localhost:8000/anvil/logs?format=json"
```

**Response:**
```json
{
  "lines": [
    {
      "line": "Listening on 0.0.0.0:8545",
      "timestamp": 1773001454.779116,
      "sequence": 72
    },
    {
      "line": "eth_blockNumber",
      "timestamp": 1773001478.7702653,
      "sequence": 73
    }
  ],
  "totalLines": 73,
  "truncated": true,
  "format": "json"
}
```

### GET /anvil/logs/stream

Stream Anvil logs in real-time using Server-Sent Events (SSE).

**Query Parameters:**
- `since` (int, optional): Start streaming from this sequence number
- `format` (str, default: "markdown"): Output format - "markdown" or "text"

**Example:**
```bash
# Stream new logs in markdown format
curl -N "http://localhost:8000/anvil/logs/stream"

# Stream logs since sequence 100
curl -N "http://localhost:8000/anvil/logs/stream?since=100&format=text"
```

**Response Format (SSE):**
```
data: ```
data: Listening on 0.0.0.0:8545
data: ```

: keepalive

data: eth_blockNumber
```

### JavaScript Example:
```javascript
const eventSource = new EventSource('http://localhost:8000/anvil/logs/stream');

eventSource.onmessage = (event) => {
  console.log('New Anvil log:', event.data);
};

eventSource.onerror = () => {
  console.log('Connection closed');
  eventSource.close();
};
```

## Docker Integration

When running in Docker, you can also access logs via Docker's native logging:

```bash
# View all logs
docker logs lenina

# Follow logs in real-time
docker logs -f lenina

# Last 200 lines
docker logs --tail 200 lenina

# With timestamps
docker logs -t lenina
```

**Advantages of API vs Docker logs:**

| Feature | API Endpoints | Docker Logs |
|---------|--------------|-------------|
| Programmatic access | ✅ Yes | ❌ No |
| Markdown formatting | ✅ Yes | ❌ No |
| Sequence-based pagination | ✅ Yes | ❌ No |
| Real-time streaming (SSE) | ✅ Yes | ✅ Yes (with -f) |
| Filter by sequence number | ✅ Yes | ❌ No |
| Works without Docker | ✅ Yes | ❌ No |

## Log Buffer Details

- **Maximum size**: 1000 lines (circular buffer)
- **Persistence**: In-memory only (cleared when Anvil stops)
- **Sequence numbers**: Monotonic counter for ordering and pagination
- **Timestamps**: Unix timestamp when each line was captured

## Stop with Preserve Logs

By default, stopping Anvil clears the log buffer. To preserve logs after stopping:

```bash
curl -X POST "http://localhost:8000/anvil/stop?preserve_logs=true"
```

**Note**: Preserved logs are only accessible until the Lenina server restarts or Anvil is started again.

## Use Cases

### 1. Monitor Anvil Activity
```bash
# Watch real-time activity
watch -n 1 'curl -s "http://localhost:8000/anvil/logs?lines=10"'
```

### 2. Debug Transaction Issues
```bash
# Get logs since last known good state
curl "http://localhost:8000/anvil/logs?since=1000&lines=100"
```

### 3. Integrate with Monitoring Tools
```python
import requests

def get_recent_logs(lines=50):
    response = requests.get(f"http://localhost:8000/anvil/logs?lines={lines}")
    return response.json()

logs = get_recent_logs()
for entry in logs['lines']:
    print(f"[{entry['sequence']}] {entry['line']}")
```

### 4. Real-time Dashboard
```javascript
// Connect to SSE stream
const logsStream = new EventSource('/anvil/logs/stream');

logsStream.onmessage = (event) => {
  const logEntry = parseLogEntry(event.data);
  updateDashboard(logEntry);
};
```

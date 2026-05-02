# Alice Browser Automation - API Reference

## Overview

This document provides comprehensive API documentation for all public classes, methods, and data models in the Alice Browser Automation system.

**Version:** 1.0.0  
**Requirements Coverage:** All requirements (1.1-12.6)

---

## Table of Contents

1. [Core Engine](#core-engine)
2. [Data Models](#data-models)
3. [Session Management](#session-management)
4. [DOM Processing](#dom-processing)
5. [Action Suites](#action-suites)
6. [Configuration](#configuration)
7. [Error Handling](#error-handling)
8. [Security](#security)

---

## Core Engine

### BrowserAutomationEngine

Main orchestrator for browser automation tasks.

**Location:** `alice_browser_automation.engine`

#### Constructor

```python
BrowserAutomationEngine(config: Optional[Config] = None)
```

**Parameters:**
- `config` (Optional[Config]): Configuration object. If None, loads from default locations.

**Example:**
```python
from alice_browser_automation import BrowserAutomationEngine, Config

# Use default configuration
engine = BrowserAutomationEngine()

# Use custom configuration
config = Config.load("custom_config.yaml")
engine = BrowserAutomationEngine(config)
```

#### Methods

##### initialize()

```python
async def initialize() -> bool
```

Initialize browser-use, Playwright, and Qwen model.

**Returns:** `bool` - True if initialization successful

**Raises:**
- `BrowserAutomationError`: If initialization fails
- `QwenModelUnavailableError`: If Qwen model is not available

**Requirements:** 1.1, 1.2, 1.3, 1.4

**Example:**
```python
engine = BrowserAutomationEngine()
await engine.initialize()
```

##### execute_task()

```python
async def execute_task(
    task_description: str,
    task_type: TaskType,
    parameters: Dict[str, Any],
    callback: Optional[Callable[[str], None]] = None
) -> TaskResult
```

Execute a browser automation task.

**Parameters:**
- `task_description` (str): Natural language description of the task
- `task_type` (TaskType): Type of task (WEB_BOOKING, PROBLEM_SOLVING, APP_ACCESS)
- `parameters` (Dict[str, Any]): Task-specific parameters
- `callback` (Optional[Callable]): Progress callback function

**Returns:** `TaskResult` - Task execution results

**Raises:**
- `BrowserAutomationError`: If task execution fails
- `QwenModelUnavailableError`: If Qwen model becomes unavailable

**Requirements:** 11.1, 11.2, 11.3, 11.4, 11.5, 12.1

**Example:**
```python
from alice_browser_automation.types import TaskType

def progress_callback(message: str):
    print(f"Progress: {message}")

result = await engine.execute_task(
    task_description="Book a flight to Paris on December 25th",
    task_type=TaskType.WEB_BOOKING,
    parameters={
        "booking_type": "flight",
        "destination": "Paris",
        "departure_date": "2024-12-25",
        "passengers": 1
    },
    callback=progress_callback
)

print(f"Success: {result.success}")
print(f"Summary: {result.summary}")
```

##### shutdown()

```python
async def shutdown() -> None
```

Clean up resources and close browser sessions.

**Requirements:** 8.3

**Example:**
```python
await engine.shutdown()
```

##### get_active_sessions()

```python
def get_active_sessions() -> List[BrowserSession]
```

Get list of active browser sessions.

**Returns:** `List[BrowserSession]` - List of active sessions

**Requirements:** 8.3

**Example:**
```python
sessions = engine.get_active_sessions()
for session in sessions:
    print(f"Session {session.session_id}: {session.domain}")
```

##### cancel_task()

```python
def cancel_task(task_id: str) -> bool
```

Cancel an active task.

**Parameters:**
- `task_id` (str): ID of the task to cancel

**Returns:** `bool` - True if task was found and cancelled

**Requirements:** 11.5

**Example:**
```python
# Start a task
result_future = asyncio.create_task(engine.execute_task(...))

# Cancel it
engine.cancel_task(task.task_id)
```

---

## Data Models

### TaskType

Enum defining types of browser automation tasks.

**Location:** `alice_browser_automation.types`

```python
class TaskType(Enum):
    WEB_BOOKING = "web_booking"
    PROBLEM_SOLVING = "problem_solving"
    APP_ACCESS = "app_access"
```

### ActionType

Enum defining types of browser actions.

```python
class ActionType(Enum):
    NAVIGATE = "navigate"
    CLICK = "click"
    TYPE = "type"
    WAIT = "wait"
    EXTRACT = "extract"
    SCROLL = "scroll"
    SELECT = "select"
    UPLOAD = "upload"
    DOWNLOAD = "download"
```

### BrowserTask

High-level browser automation task.

```python
@dataclass
class BrowserTask:
    task_id: str
    description: str
    task_type: TaskType
    parameters: Dict[str, Any]
    target_url: Optional[str] = None
    expected_outcome: str = ""
```

**Fields:**
- `task_id`: Unique identifier for the task
- `description`: Natural language description
- `task_type`: Type of task (TaskType enum)
- `parameters`: Task-specific parameters
- `target_url`: Optional starting URL
- `expected_outcome`: Expected result description

### TaskResult

Result of browser automation task execution.

```python
@dataclass
class TaskResult:
    task_id: str
    success: bool
    summary: str
    actions_taken: List[BrowserAction] = field(default_factory=list)
    extracted_data: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    duration_seconds: float = 0.0
    screenshots: List[str] = field(default_factory=list)
```

**Fields:**
- `task_id`: Task identifier
- `success`: Whether task completed successfully
- `summary`: Human-readable summary
- `actions_taken`: List of actions executed
- `extracted_data`: Data extracted during execution
- `error`: Error message if failed
- `duration_seconds`: Execution duration
- `screenshots`: Paths to screenshots taken

### BrowserSession

Active browser session with Playwright.

```python
@dataclass
class BrowserSession:
    session_id: str
    profile_name: str
    domain: str
    playwright_context: Any  # BrowserContext
    playwright_page: Any  # Page
    created_at: datetime
    last_activity: datetime
    is_headless: bool
    state: SessionState
```

**Fields:**
- `session_id`: Unique session identifier
- `profile_name`: Chrome profile name
- `domain`: Associated domain
- `playwright_context`: Playwright BrowserContext
- `playwright_page`: Playwright Page
- `created_at`: Creation timestamp
- `last_activity`: Last activity timestamp
- `is_headless`: Whether running headless
- `state`: Current session state

### StructuredDOM

Structured representation of DOM for LLM processing.

```python
@dataclass
class StructuredDOM:
    url: str
    title: str
    interactive_elements: List[InteractiveElement]
    text_content: str
    metadata: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)
```

**Fields:**
- `url`: Page URL
- `title`: Page title
- `interactive_elements`: List of interactive elements
- `text_content`: Extracted text content
- `metadata`: Additional metadata
- `timestamp`: Parse timestamp

### InteractiveElement

Represents an interactive DOM element.

```python
@dataclass
class InteractiveElement:
    element_id: str
    tag_name: str
    role: str  # ARIA role
    label: str
    selectors: ElementSelectors
    attributes: Dict[str, str]
    position: Tuple[int, int]  # x, y coordinates
    is_visible: bool
```

**Fields:**
- `element_id`: Unique element identifier
- `tag_name`: HTML tag name
- `role`: ARIA role
- `label`: Element label/text
- `selectors`: Multiple selector strategies
- `attributes`: HTML attributes
- `position`: Screen coordinates
- `is_visible`: Visibility status

---

## Session Management

### SessionManager

Manages browser session lifecycle and resource limits.

**Location:** `alice_browser_automation.session_manager`

#### Constructor

```python
SessionManager(
    profile_manager: ChromeProfileManager,
    max_concurrent_sessions: int = 3,
    idle_timeout_seconds: int = 300,
    browser_type: str = "chromium"
)
```

**Parameters:**
- `profile_manager`: ChromeProfileManager instance
- `max_concurrent_sessions`: Maximum concurrent sessions (default: 3)
- `idle_timeout_seconds`: Idle timeout in seconds (default: 300)
- `browser_type`: Browser type (default: "chromium")

**Requirements:** 8.1

#### Methods

##### initialize()

```python
async def initialize() -> None
```

Initialize Playwright and browser.

**Raises:** `SessionError` if initialization fails

**Example:**
```python
manager = SessionManager(profile_manager)
await manager.initialize()
```

##### create_session()

```python
async def create_session(
    profile_name: str = "default",
    headless: bool = True,
    domain: Optional[str] = None
) -> BrowserSession
```

Create a new browser session.

**Parameters:**
- `profile_name`: Chrome profile name (default: "default")
- `headless`: Run in headless mode (default: True)
- `domain`: Optional domain for session reuse

**Returns:** `BrowserSession` - New session object

**Raises:**
- `SessionLimitError`: If max sessions limit reached
- `SessionError`: If creation fails

**Requirements:** 8.1, 8.2, 8.5, 12.1

**Example:**
```python
session = await manager.create_session(
    profile_name="work",
    headless=True,
    domain="example.com"
)
```

##### get_session_for_domain()

```python
async def get_session_for_domain(domain: str) -> Optional[BrowserSession]
```

Get existing session for domain or None.

**Parameters:**
- `domain`: Domain to look up

**Returns:** `Optional[BrowserSession]` - Session if found and active

**Requirements:** 8.5, 12.1

**Example:**
```python
session = await manager.get_session_for_domain("example.com")
if session:
    # Reuse existing session
    page = session.playwright_page
else:
    # Create new session
    session = await manager.create_session(domain="example.com")
```

##### close_session()

```python
async def close_session(session_id: str) -> None
```

Close a specific browser session.

**Parameters:**
- `session_id`: ID of session to close

**Raises:** `ValueError` if session doesn't exist

**Requirements:** 8.1

##### close_idle_sessions()

```python
async def close_idle_sessions() -> int
```

Close sessions idle longer than idle_timeout.

**Returns:** `int` - Number of sessions closed

**Requirements:** 8.3, 8.4

**Example:**
```python
closed_count = await manager.close_idle_sessions()
print(f"Closed {closed_count} idle sessions")
```

##### restart_crashed_session()

```python
async def restart_crashed_session(session_id: str) -> BrowserSession
```

Restart a crashed browser session.

**Parameters:**
- `session_id`: ID of crashed session

**Returns:** `BrowserSession` - New session object

**Raises:**
- `ValueError`: If session doesn't exist or not crashed
- `SessionError`: If restart fails

**Requirements:** 8.6, 9.6

**Example:**
```python
try:
    await page.goto("https://example.com")
except Exception:
    # Session crashed
    session = await manager.restart_crashed_session(session.session_id)
```

---

## DOM Processing

### DOMParser

Extracts structured DOM data and accessibility tree.

**Location:** `alice_browser_automation.dom_parser`

#### Constructor

```python
DOMParser(cache_duration_seconds: float = 2.0)
```

**Parameters:**
- `cache_duration_seconds`: DOM cache duration (default: 2.0)

**Requirements:** 2.1, 2.2, 2.3, 2.4, 2.5, 2.6

#### Methods

##### parse_page()

```python
async def parse_page(page: PlaywrightPage) -> StructuredDOM
```

Extract DOM structure from current page.

**Parameters:**
- `page`: Playwright Page object

**Returns:** `StructuredDOM` - Structured DOM representation

**Requirements:** 2.1, 2.4, 12.2

**Example:**
```python
from alice_browser_automation import DOMParser

parser = DOMParser()
dom = await parser.parse_page(page)

print(f"Page: {dom.title}")
print(f"Interactive elements: {len(dom.interactive_elements)}")
```

##### get_accessibility_tree()

```python
async def get_accessibility_tree(page: PlaywrightPage) -> AccessibilityTree
```

Extract accessibility tree for element identification.

**Parameters:**
- `page`: Playwright Page object

**Returns:** `AccessibilityTree` - Accessibility tree structure

**Requirements:** 2.2

**Example:**
```python
tree = await parser.get_accessibility_tree(page)
print(f"Interactive nodes: {len(tree.interactive_nodes)}")
```

##### filter_interactive_elements()

```python
def filter_interactive_elements(dom: StructuredDOM) -> List[InteractiveElement]
```

Filter only interactive elements.

**Parameters:**
- `dom`: StructuredDOM object

**Returns:** `List[InteractiveElement]` - Interactive elements only

**Requirements:** 2.6

---

## Action Suites

### WebBookingsActionSuite

Handles travel bookings, food delivery, and event tickets.

**Location:** `alice_browser_automation.web_bookings`

**Requirements:** 5.1-5.8

#### Constructor

```python
WebBookingsActionSuite(
    engine: BrowserAutomationEngine,
    config: Optional[Dict[str, Any]] = None
)
```

#### Methods

##### book_flight()

```python
async def book_flight(
    origin: str,
    destination: str,
    departure_date: date,
    return_date: Optional[date] = None,
    passengers: int = 1,
    class_preference: Optional[str] = None,
    progress_callback: Optional[Callable[[str], None]] = None
) -> TaskResult
```

Book a flight.

**Parameters:**
- `origin`: Departure airport/city
- `destination`: Arrival airport/city
- `departure_date`: Departure date
- `return_date`: Optional return date
- `passengers`: Number of passengers
- `class_preference`: "economy", "business", or "first"
- `progress_callback`: Progress updates

**Returns:** `TaskResult` - Booking confirmation

**Requirements:** 5.1, 5.2, 5.3, 5.4, 5.5

**Example:**
```python
from datetime import date

result = await web_bookings.book_flight(
    origin="New York",
    destination="Paris",
    departure_date=date(2024, 12, 25),
    return_date=date(2025, 1, 5),
    passengers=2,
    class_preference="economy"
)

if result.success:
    confirmation = result.extracted_data.get("confirmation_number")
    print(f"Flight booked! Confirmation: {confirmation}")
```

##### book_hotel()

```python
async def book_hotel(
    destination: str,
    check_in_date: date,
    check_out_date: date,
    guests: int = 1,
    preferences: Optional[Dict[str, Any]] = None,
    progress_callback: Optional[Callable[[str], None]] = None
) -> TaskResult
```

Book a hotel.

**Parameters:**
- `destination`: Hotel location/city
- `check_in_date`: Check-in date
- `check_out_date`: Check-out date
- `guests`: Number of guests
- `preferences`: Optional preferences (pool, wifi, etc.)
- `progress_callback`: Progress updates

**Returns:** `TaskResult` - Booking confirmation

**Example:**
```python
result = await web_bookings.book_hotel(
    destination="Paris",
    check_in_date=date(2024, 12, 25),
    check_out_date=date(2024, 12, 30),
    guests=2,
    preferences={"pool": True, "wifi": True}
)
```

##### order_food()

```python
async def order_food(
    restaurant: str,
    items: List[str],
    delivery_address: str,
    platform: Optional[str] = None,
    special_instructions: Optional[str] = None,
    progress_callback: Optional[Callable[[str], None]] = None
) -> TaskResult
```

Order food delivery.

**Parameters:**
- `restaurant`: Restaurant name
- `items`: List of menu items
- `delivery_address`: Delivery address
- `platform`: Optional platform ("ubereats", "doordash", "grubhub")
- `special_instructions`: Optional delivery instructions
- `progress_callback`: Progress updates

**Returns:** `TaskResult` - Order confirmation

**Requirements:** 5.6

**Example:**
```python
result = await web_bookings.order_food(
    restaurant="Pizza Palace",
    items=["Large Pepperoni Pizza", "Caesar Salad", "Garlic Bread"],
    delivery_address="123 Main St, Apt 4B",
    platform="ubereats",
    special_instructions="Ring doorbell twice"
)
```

##### book_event()

```python
async def book_event(
    event_name: str,
    date: date,
    venue: Optional[str] = None,
    ticket_count: int = 1,
    seat_preference: Optional[str] = None,
    ticket_type: Optional[str] = None,
    progress_callback: Optional[Callable[[str], None]] = None
) -> TaskResult
```

Book event tickets.

**Parameters:**
- `event_name`: Name of the event
- `date`: Event date
- `venue`: Optional venue name
- `ticket_count`: Number of tickets
- `seat_preference`: Optional ("front", "middle", "back", "vip")
- `ticket_type`: Optional ("general", "vip", "premium")
- `progress_callback`: Progress updates

**Returns:** `TaskResult` - Booking confirmation

**Requirements:** 5.7

**Example:**
```python
result = await web_bookings.book_event(
    event_name="Hamilton Musical",
    date=date(2024, 12, 31),
    venue="Broadway Theatre",
    ticket_count=2,
    seat_preference="middle",
    ticket_type="premium"
)
```

### ProblemSolvingActionSuite

Handles desktop problem solving through web research.

**Location:** `alice_browser_automation.problem_solving`

**Requirements:** 6.1-6.6

#### Methods

##### solve_problem()

```python
async def solve_problem(
    problem_description: str,
    system_info: Optional[Dict[str, Any]] = None,
    max_solutions: int = 5,
    auto_execute: bool = False,
    progress_callback: Optional[Callable[[str], None]] = None
) -> TaskResult
```

Solve a desktop problem using web research.

**Parameters:**
- `problem_description`: Description of the problem
- `system_info`: Optional system information
- `max_solutions`: Maximum solutions to find
- `auto_execute`: Auto-execute top solution
- `progress_callback`: Progress updates

**Returns:** `TaskResult` - Solutions and execution results

**Requirements:** 6.1, 6.2, 6.3, 6.4, 6.5, 6.6

**Example:**
```python
result = await problem_solving.solve_problem(
    problem_description="Python import error: ModuleNotFoundError",
    system_info={"os": "Windows 10", "python_version": "3.11"},
    max_solutions=5,
    auto_execute=False
)

solutions = result.extracted_data.get("solutions", [])
for sol in solutions:
    print(f"Solution: {sol['title']}")
    print(f"Steps: {sol['steps']}")
```

### ApplicationAccessActionSuite

Handles web application access with persistent login.

**Location:** `alice_browser_automation.app_access`

**Requirements:** 7.1-7.7

#### Methods

##### access_application()

```python
async def access_application(
    app_name: str,
    action: str = "open",
    section: Optional[str] = None,
    extract_info: Optional[List[str]] = None,
    parameters: Optional[Dict[str, Any]] = None,
    progress_callback: Optional[Callable[[str], None]] = None
) -> AppAccessResult
```

Access a web application with persistent login.

**Parameters:**
- `app_name`: Application name ("gmail", "github", "linkedin")
- `action`: Action to perform ("open", "navigate", "extract")
- `section`: Optional section to navigate to
- `extract_info`: Optional information to extract
- `parameters`: Optional additional parameters
- `progress_callback`: Progress updates

**Returns:** `AppAccessResult` - Access details

**Requirements:** 7.3, 7.4, 7.5, 7.6

**Example:**
```python
# Access Gmail inbox
result = await app_access.access_application(
    app_name="gmail",
    action="navigate",
    section="inbox",
    extract_info=["unread_count", "latest_emails"]
)

if result.success:
    info = result.extracted_info
    print(f"Unread emails: {info.get('unread_count')}")
```

---

## Configuration

### Config

Main configuration container.

**Location:** `alice_browser_automation.config`

#### Class Methods

##### load()

```python
@classmethod
def load(cls, config_path: Optional[str] = None) -> Config
```

Load configuration from file and environment.

**Parameters:**
- `config_path`: Optional path to YAML config file

**Returns:** `Config` - Configuration object

**Example:**
```python
from alice_browser_automation import Config

# Load from default locations
config = Config.load()

# Load from specific file
config = Config.load("custom_config.yaml")
```

##### from_yaml()

```python
@classmethod
def from_yaml(cls, config_path: str) -> Config
```

Load configuration from YAML file.

##### from_env()

```python
@classmethod
def from_env(cls) -> Config
```

Load configuration from environment variables.

#### Configuration Sections

**BrowserConfig:**
- `headless_default`: Run headless by default (bool)
- `max_concurrent_sessions`: Max concurrent sessions (int)
- `idle_timeout_seconds`: Idle timeout (int)
- `profiles_dir`: Profiles directory path (str)
- `default_profile`: Default profile name (str)

**QwenConfig:**
- `host`: Ollama host URL (str)
- `model`: Qwen model name (str)
- `timeout_seconds`: Request timeout (int)
- `max_retries`: Max retry attempts (int)

**SecurityConfig:**
- `require_payment_confirmation`: Require payment confirmation (bool)
- `block_banking_sites`: Block banking sites (bool)
- `validate_ssl`: Validate SSL certificates (bool)
- `clear_sensitive_data`: Clear sensitive data after tasks (bool)

**Example YAML:**
```yaml
browser:
  headless_default: true
  max_concurrent_sessions: 3
  idle_timeout_seconds: 300
  profiles_dir: "~/.alice/browser_profiles"
  default_profile: "default"

qwen:
  host: "http://localhost:11434"
  model: "qwen2.5-coder:3b"
  timeout_seconds: 30
  max_retries: 3

security:
  require_payment_confirmation: true
  block_banking_sites: false
  validate_ssl: true
  clear_sensitive_data: true
```

---

## Error Handling

### Exception Hierarchy

```
BrowserAutomationError (base)
├── QwenModelUnavailableError
├── SessionError
│   ├── SessionLimitError
│   └── SessionCrashedError
├── DOMParsingError
├── ActionExecutionError
└── SecurityError
```

### BrowserAutomationError

Base exception for all browser automation errors.

```python
class BrowserAutomationError(Exception):
    """Base exception for browser automation errors"""
    pass
```

### QwenModelUnavailableError

Raised when Qwen model is not available.

```python
class QwenModelUnavailableError(BrowserAutomationError):
    def __init__(self, message: str, host: str, model: str):
        self.host = host
        self.model = model
        super().__init__(message)
```

**Example:**
```python
try:
    await engine.initialize()
except QwenModelUnavailableError as e:
    print(f"Qwen model not available at {e.host}: {e.model}")
    print("Please ensure Ollama is running and model is installed")
```

### SessionLimitError

Raised when max concurrent sessions limit is reached.

```python
class SessionLimitError(SessionError):
    def __init__(self, message: str, current_count: int, max_limit: int):
        self.current_count = current_count
        self.max_limit = max_limit
        super().__init__(message)
```

**Example:**
```python
try:
    session = await manager.create_session()
except SessionLimitError as e:
    print(f"Session limit reached: {e.current_count}/{e.max_limit}")
    # Close idle sessions and retry
    await manager.close_idle_sessions()
    session = await manager.create_session()
```

---

## Security

### SecurityManager

Manages security and privacy settings.

**Location:** `alice_browser_automation.security`

**Requirements:** 10.1-10.6

#### Methods

##### validate_url()

```python
def validate_url(url: str) -> bool
```

Validate URL for security concerns.

**Parameters:**
- `url`: URL to validate

**Returns:** `bool` - True if URL is safe

**Requirements:** 10.6

##### require_payment_confirmation()

```python
async def require_payment_confirmation(
    action_description: str,
    callback: Callable[[str], bool]
) -> bool
```

Require user confirmation for payment actions.

**Parameters:**
- `action_description`: Description of payment action
- `callback`: Callback to get user confirmation

**Returns:** `bool` - True if confirmed

**Requirements:** 10.3

##### clear_sensitive_data()

```python
def clear_sensitive_data() -> None
```

Clear sensitive data from memory.

**Requirements:** 10.4

---

## Complete Example

Here's a complete example using the API:

```python
import asyncio
from datetime import date
from alice_browser_automation import (
    BrowserAutomationEngine,
    Config,
    TaskType
)

async def main():
    # Initialize engine
    config = Config.load()
    engine = BrowserAutomationEngine(config)
    
    try:
        # Initialize components
        await engine.initialize()
        print("Engine initialized successfully")
        
        # Book a flight
        def progress(msg):
            print(f"Progress: {msg}")
        
        result = await engine.execute_task(
            task_description="Book a flight to Paris on December 25th",
            task_type=TaskType.WEB_BOOKING,
            parameters={
                "booking_type": "flight",
                "origin": "New York",
                "destination": "Paris",
                "departure_date": "2024-12-25",
                "passengers": 1,
                "class_preference": "economy"
            },
            callback=progress
        )
        
        if result.success:
            print(f"Success! {result.summary}")
            if "confirmation_number" in result.extracted_data:
                print(f"Confirmation: {result.extracted_data['confirmation_number']}")
        else:
            print(f"Failed: {result.error}")
        
    finally:
        # Clean up
        await engine.shutdown()
        print("Engine shut down")

if __name__ == "__main__":
    asyncio.run(main())
```

---

## API Versioning

**Current Version:** 1.0.0

The API follows semantic versioning (MAJOR.MINOR.PATCH):
- MAJOR: Breaking changes
- MINOR: New features (backward compatible)
- PATCH: Bug fixes (backward compatible)

---

## Support

For issues, questions, or contributions:
- GitHub Issues: [Link to repository]
- Documentation: [Link to docs]
- Email: support@alice-automation.com

---

**Last Updated:** 2024
**Requirements Coverage:** All requirements (1.1-12.6) documented

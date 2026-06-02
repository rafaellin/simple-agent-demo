# AI Agent Memory System - Complete Reference

## Table of Contents
1. [Quick Start (5 min)](#quick-start)
2. [How It Works](#how-it-works)
3. [Features](#features)
4. [Python API](#python-api)
5. [WebSocket API](#websocket-api)
6. [Storage & Architecture](#storage--architecture)
7. [Examples](#examples)
8. [Troubleshooting](#troubleshooting)
9. [Best Practices](#best-practices)

---

## Quick Start

### Installation
Memory is **built-in** - no installation needed. It activates automatically when the agent starts.

### 30-Second Overview
```python
from agent import Agent

# Initialize agent (memory auto-created)
agent = Agent(config_dir, workspace_path, api_key)

# Every message is automatically tracked
for response in agent.stream_response("Hello!"):
    print(response)

# Manually store facts
agent.add_fact_to_memory("user_lang", "Speaks French", "preference", 0.95)
agent.set_memory_preference("format", "markdown")

# Check memory
stats = agent.get_memory_stats()
print(f"Stored facts: {stats['total_facts']}")
```

### WebSocket (JavaScript)
```javascript
// Get memory stats
ws.send(JSON.stringify({ type: "memory_stats" }));

// Add a fact
ws.send(JSON.stringify({
  type: "add_fact",
  fact_id: "user_timezone",
  fact: "UTC+8",
  category: "location",
  confidence: 0.9
}));

// Set preference
ws.send(JSON.stringify({
  type: "set_preference",
  key: "language",
  value: "French"
}));
```

---

## How It Works

### Memory System Architecture

```
Agent Instance
├── ShortTermMemory (in-memory, max 50 messages)
│   ├── Messages from current conversation
│   ├── Context variables
│   └── Current topic
│
├── LongTermMemory (persistent JSON files)
│   ├── facts.json - Knowledge with confidence levels
│   ├── summaries.json - Conversation summaries
│   ├── preferences.json - User preferences
│   └── patterns.json - Behavioral patterns
│
└── MemoryManager (unified interface)
    ├── Tracks all messages automatically
    ├── Auto-summarizes at 30 messages
    └── Provides context to LLM
```

### Message Flow

```
1. User Message → Added to ShortTermMemory
2. LLM gets system prompt with:
   - Top 5 facts from LongTermMemory
   - Top 3 patterns from LongTermMemory
3. AI Response → Added to ShortTermMemory
4. Tool Results → Added to ShortTermMemory
5. At 30 messages → Auto-summarize:
   - Create summary
   - Move to LongTermMemory
   - Clear ShortTermMemory
   - Continue conversation
```

---

## Features

### ✅ Short-Term Memory
- Stores up to 50 recent messages
- Configurable capacity
- Stores context variables
- Tracks current topic
- Auto-clears on summarization

### ✅ Long-Term Memory
- **Facts**: Knowledge with confidence levels (0.0-1.0)
- **Summaries**: Conversation summaries with timestamps
- **Preferences**: User settings and preferences
- **Patterns**: Behavioral patterns with frequency tracking
- Persistent JSON file storage
- Survives agent restarts

### ✅ Auto-Summarization
- Triggers at 30 messages
- Creates summary of conversation
- Stores in long-term memory
- Clears short-term memory
- Seamless continuation

### ✅ LLM Integration
- Top 5 facts included in system prompt
- Top 3 patterns included
- Agent remembers historical context
- More personalized responses

### ✅ Zero Configuration
- Automatic initialization
- Works out of the box
- No configuration needed
- Starts immediately

---

## Python API

### MemoryManager Methods

#### Add Message (Automatic)
```python
# Messages are added automatically during streaming
# But you can also add manually:
agent.memory.add_message("user", "Hello", metadata={"type": "custom"})
agent.memory.add_message("assistant", "Hi there!", metadata={"type": "custom"})
```

#### Facts Management

```python
# Add a fact
agent.add_fact_to_memory(
    fact_id="user_timezone",
    fact="User is in UTC+8",
    category="location",
    confidence=0.95
)

# Retrieve a fact
fact = agent.retrieve_memory_fact("user_timezone")
print(fact)
# Output: {
#   "fact": "User is in UTC+8",
#   "category": "location",
#   "confidence": 0.95,
#   "timestamp": "2024-05-19T10:15:00",
#   "access_count": 3
# }
```

#### Preferences Management

```python
# Set a preference
agent.set_memory_preference("response_language", "French")
agent.set_memory_preference("output_format", "markdown")

# Get all preferences
prefs = agent.get_memory_preferences()
print(prefs)
# Output: {
#   "response_language": "French",
#   "output_format": "markdown"
# }
```

#### Statistics & Summary

```python
# Get memory stats
stats = agent.get_memory_stats()
print(stats)
# Output: {
#   "short_term_messages": 15,
#   "short_term_capacity": 50,
#   "total_facts": 5,
#   "total_patterns": 12,
#   "recent_summaries": 2,
#   "message_history_length": 20
# }

# Get comprehensive summary
summary = agent.get_memory_summary()
print(f"Facts: {summary['stored_facts']}")
print(f"Recent summaries: {summary['recent_summaries']}")
print(f"Patterns: {summary['common_patterns']}")
```

### Direct Memory Access

```python
# Access ShortTermMemory directly
agent.memory.short_term.get_all_messages()
agent.memory.short_term.get_context("key")
agent.memory.short_term.set_context("key", "value")

# Access LongTermMemory directly
agent.memory.long_term.get_all_facts()
agent.memory.long_term.get_facts_by_category("location")
agent.memory.long_term.get_common_patterns(limit=5)
agent.memory.long_term.get_summaries(limit=3)
```

---

## WebSocket API

### Message Format
```json
{
  "type": "message_type",
  "data": {}
}
```

### Get Memory Stats
**Request:**
```json
{
  "type": "memory_stats"
}
```

**Response:**
```json
{
  "type": "memory_stats",
  "data": {
    "short_term_messages": 15,
    "short_term_capacity": 50,
    "total_facts": 5,
    "total_patterns": 12,
    "recent_summaries": 2,
    "message_history_length": 20
  }
}
```

### Get Memory Summary
**Request:**
```json
{
  "type": "memory_summary"
}
```

**Response:**
```json
{
  "type": "memory_summary",
  "data": {
    "stats": { /* memory_stats */ },
    "recent_summaries": [
      {
        "summary": "Discussion about...",
        "message_count": 25,
        "timestamp": "2024-05-19T10:30:00"
      }
    ],
    "common_patterns": [
      {
        "pattern": "User asks questions",
        "frequency": 8,
        "first_seen": "2024-05-19T10:00:00"
      }
    ],
    "stored_facts": 5,
    "user_preferences": { "language": "French" }
  }
}
```

### Add a Fact
**Request:**
```json
{
  "type": "add_fact",
  "fact_id": "user_timezone",
  "fact": "User is in UTC+8",
  "category": "location",
  "confidence": 0.95
}
```

**Response:**
```json
{
  "type": "fact_added",
  "data": {
    "fact_id": "user_timezone",
    "status": "success"
  }
}
```

### Retrieve a Fact
**Request:**
```json
{
  "type": "get_fact",
  "fact_id": "user_timezone"
}
```

**Response:**
```json
{
  "type": "fact_retrieved",
  "data": {
    "fact": "User is in UTC+8",
    "category": "location",
    "confidence": 0.95,
    "timestamp": "2024-05-19T10:15:00",
    "access_count": 3
  }
}
```

### Set a Preference
**Request:**
```json
{
  "type": "set_preference",
  "key": "language",
  "value": "French"
}
```

**Response:**
```json
{
  "type": "preference_set",
  "data": {
    "key": "language",
    "status": "success"
  }
}
```

### Get All Preferences
**Request:**
```json
{
  "type": "get_preferences"
}
```

**Response:**
```json
{
  "type": "preferences",
  "data": {
    "language": "French",
    "format": "markdown",
    "verbosity": "concise"
  }
}
```

### JavaScript Helper Class
```javascript
class AgentMemory {
  constructor(wsUrl = 'ws://localhost:8765/ws') {
    this.ws = new WebSocket(wsUrl);
  }

  addFact(factId, fact, category = 'general', confidence = 1.0) {
    this.ws.send(JSON.stringify({
      type: 'add_fact',
      fact_id: factId,
      fact, category, confidence
    }));
  }

  getFact(factId) {
    this.ws.send(JSON.stringify({
      type: 'get_fact',
      fact_id: factId
    }));
  }

  setPreference(key, value) {
    this.ws.send(JSON.stringify({
      type: 'set_preference',
      key, value
    }));
  }

  getPreferences() {
    this.ws.send(JSON.stringify({ type: 'get_preferences' }));
  }

  getMemoryStats() {
    this.ws.send(JSON.stringify({ type: 'memory_stats' }));
  }

  getMemorySummary() {
    this.ws.send(JSON.stringify({ type: 'memory_summary' }));
  }
}
```

---

## Storage & Architecture

### File Structure

```
workspace/
├── agent-workspace/          (Existing sandbox)
└── memory/                   (NEW - auto-created)
    ├── facts.json
    ├── summaries.json
    ├── preferences.json
    └── patterns.json
```

### Data Format

**facts.json:**
```json
{
  "user_timezone": {
    "fact": "User is in UTC+8",
    "category": "location",
    "confidence": 0.95,
    "timestamp": "2024-05-19T10:15:00",
    "access_count": 3
  }
}
```

**summaries.json:**
```json
{
  "summary_20240519_101500": {
    "summary": "Conversation with 30 messages about Python",
    "message_count": 30,
    "timestamp": "2024-05-19T10:15:00"
  }
}
```

**preferences.json:**
```json
{
  "language": {
    "value": "French",
    "timestamp": "2024-05-19T09:00:00"
  }
}
```

**patterns.json:**
```json
{
  "user_asks_questions": {
    "pattern": "User frequently asks technical questions",
    "frequency": 12,
    "first_seen": "2024-05-19T08:00:00",
    "last_seen": "2024-05-19T10:30:00"
  }
}
```

### Code Organization

**New file:** `backend/src/agent/memory.py`
- `ShortTermMemory` class - ~100 lines
- `LongTermMemory` class - ~200 lines
- `MemoryManager` class - ~50 lines

**Modified:** `backend/src/agent/agent.py`
- Added MemoryManager initialization
- Auto-message tracking in stream_response()
- Memory context in system prompt
- 6 new memory methods
- Auto-summarization logic

**Modified:** `backend/src/agent/gateway.py`
- 6 new WebSocket endpoints
- Memory operation handlers

---

## Examples

### Example 1: Store User Preferences

```python
# During first interaction
agent.add_fact_to_memory(
    fact_id="user_preference_lang",
    fact="User prefers French responses",
    category="user_preference",
    confidence=0.95
)

agent.set_memory_preference("response_language", "French")
agent.set_memory_preference("format", "markdown")

# Agent now remembers and uses these preferences
```

### Example 2: Track User Skills

```python
# As conversation progresses
agent.add_fact_to_memory(
    fact_id="user_skill_python",
    fact="User is experienced with Python",
    category="user_skill",
    confidence=0.9
)

agent.add_fact_to_memory(
    fact_id="user_skill_javascript",
    fact="User is learning JavaScript",
    category="user_skill",
    confidence=0.7
)

# Agent will adjust explanations based on skill level
```

### Example 3: Monitor Memory Growth

```python
# Check memory during conversation
for i in range(5):
    response = agent.stream_response(f"Message {i}")
    
    stats = agent.get_memory_stats()
    print(f"Messages in memory: {stats['short_term_messages']}")
    
    # At 30 messages, auto-summarization triggers
    if stats['short_term_messages'] == 0:
        print("Auto-summarization occurred!")
        summary = agent.get_memory_summary()
        print(f"New summary created: {summary['recent_summaries'][0]['summary']}")
```

### Example 4: Retrieve Facts Later

```python
# Later in another conversation
fact = agent.retrieve_memory_fact("user_preference_lang")

if fact:
    language = fact['fact']
    print(f"Continuing in: {language}")
    # Agent has context about previous preference
```

### Example 5: WebSocket Frontend Integration

```javascript
const memory = new AgentMemory('ws://localhost:8765/ws');

// Store user information
memory.addFact(
  'user_company',
  'Works at TechCorp',
  'user_info',
  0.9
);

// Set preferences
memory.setPreference('notification_style', 'minimal');

// Get stats for UI
memory.getMemoryStats();  // Updates UI with stats

// Monitor memory during conversation
setInterval(() => {
  memory.getMemoryStats();
}, 5000);  // Check every 5 seconds
```

---

## Troubleshooting

### Memory Not Persisting?
**Check:**
1. Verify `workspace/memory/` directory exists
2. Check file permissions (must be writable)
3. Review agent logs for errors
4. Restart agent if needed

### Auto-Summarization Not Triggering?
**Fix:**
1. Needs ≥30 messages to trigger
2. Check agent logs for summarization events
3. Verify LongTermMemory can write to disk

### Facts Not Included in LLM Prompt?
**Check:**
1. Verify facts were added (check `facts.json`)
2. Facts need confidence > 0 (ideally 0.7+)
3. Only top 5 facts included - your fact might not be top 5
4. Check agent system prompt for memory context

### WebSocket Endpoints Not Responding?
**Fix:**
1. Verify gateway is running
2. Check WebSocket connection is open
3. Review error messages in browser console
4. Check agent logs for endpoint errors

### "Out of Memory" Issues?
**Note:** With 50 message limit and auto-summarization, memory is efficient. If issues occur:
1. Reduce short-term capacity in code
2. Lower auto-summarization threshold
3. Clear old summaries manually
4. Restart agent to clear memory

---

## Best Practices

### ✅ DO
- Store **specific, factual information** about users
- Use **consistent fact IDs** for easy retrieval
- Set **appropriate confidence levels** (0.7-1.0 for reliable facts)
- Use **meaningful categories** to organize facts
- **Check memory stats** periodically
- Use **lowercase underscores** for fact IDs (user_timezone, not userTimezone)
- Update facts instead of creating duplicates
- Set confidence < 1.0 for uncertain facts

### ❌ DON'T
- Store **sensitive data** (passwords, API keys, tokens)
- Use **vague fact IDs** (just use descriptive names)
- Store **duplicate facts** (same fact_id overwrites)
- Ignore **confidence levels** (affects importance)
- Store **overly broad information**
- Create facts without **categories**
- Assume all facts stay in LLM prompt (only top 5 included)

### Fact Categories
Common categories for organizing:
- `user_preference` - User preferences
- `user_info` - User information
- `user_skill` - User skills/expertise
- `location` - Location information
- `conversation` - Facts from conversations
- `general` - General knowledge

### Naming Conventions
```python
# Good fact IDs
"user_lang_preference"
"user_timezone"
"user_experience_level"

# Avoid
"fp1"  # Too vague
"UserLangPref"  # Use underscores
"the user prefers french"  # Too long
```

---

## Files Changed

**Created:**
- `backend/src/agent/memory.py` - Core memory system
- `test_memory.py` - Test suite

**Modified:**
- `backend/src/agent/agent.py` - Agent integration
- `backend/src/agent/gateway.py` - WebSocket endpoints
- `README.md` - Documentation links

---

## Testing

Run the test suite to verify everything works:
```bash
python test_memory.py
```

This tests:
- Short-term memory operations
- Long-term memory operations
- Fact storage and retrieval
- Preference management
- Pattern tracking
- Auto-summarization

---

## Summary

The memory system provides:

✅ **Automatic conversation tracking** - Every message remembered
✅ **Persistent knowledge** - Facts survive restarts
✅ **Smart summarization** - Auto-summarize at 30 messages
✅ **LLM awareness** - Facts included in every prompt
✅ **Simple API** - Easy Python and WebSocket interfaces
✅ **Zero configuration** - Works immediately
✅ **Production ready** - Tested and documented

**Ready to use!** Start with the Quick Start section above. 🚀

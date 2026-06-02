import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Any, Optional
from collections import deque

logger = logging.getLogger(__name__)


class ShortTermMemory:
    """Manages short-term memory (current conversation context)."""
    
    def __init__(self, max_messages: int = 50):
        self.max_messages = max_messages
        self.messages: deque = deque(maxlen=max_messages)
        self.context: dict = {}
        self.current_topic: Optional[str] = None
        
    def add_message(self, role: str, content: str, metadata: dict = None) -> None:
        """Add a message to short-term memory."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "role": role,
            "content": content,
            "metadata": metadata or {}
        }
        self.messages.append(entry)
        logger.debug(f"Added {role} message to short-term memory")
    
    def get_recent_messages(self, limit: int = 10) -> list:
        """Get recent messages from short-term memory."""
        return list(self.messages)[-limit:]
    
    def get_all_messages(self) -> list:
        """Get all messages in short-term memory."""
        return list(self.messages)
    
    def set_context(self, key: str, value: Any) -> None:
        """Set context variable."""
        self.context[key] = value
        logger.debug(f"Set context: {key} = {value}")
    
    def get_context(self, key: str, default: Any = None) -> Any:
        """Get context variable."""
        return self.context.get(key, default)
    
    def set_topic(self, topic: str) -> None:
        """Set the current conversation topic."""
        self.current_topic = topic
        logger.info(f"Current topic set to: {topic}")
    
    def get_topic(self) -> Optional[str]:
        """Get the current conversation topic."""
        return self.current_topic
    
    def clear(self) -> None:
        """Clear short-term memory."""
        self.messages.clear()
        self.context.clear()
        self.current_topic = None
        logger.info("Short-term memory cleared")


class LongTermMemory:
    """Manages long-term memory (persistent storage)."""
    
    def __init__(self, storage_dir: str):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        self.facts_file = self.storage_dir / "facts.json"
        self.summaries_file = self.storage_dir / "summaries.json"
        self.preferences_file = self.storage_dir / "preferences.json"
        self.patterns_file = self.storage_dir / "patterns.json"
        
        # Initialize files if they don't exist
        self._initialize_files()
    
    def _initialize_files(self) -> None:
        """Initialize empty storage files if they don't exist."""
        for file_path in [self.facts_file, self.summaries_file, 
                         self.preferences_file, self.patterns_file]:
            if not file_path.exists():
                file_path.write_text(json.dumps({}), encoding="utf-8")
                logger.debug(f"Initialized {file_path.name}")
    
    def _load_json(self, file_path: Path) -> dict:
        """Load JSON from file."""
        try:
            content = file_path.read_text(encoding="utf-8")
            return json.loads(content) if content else {}
        except Exception as e:
            logger.error(f"Error loading {file_path.name}: {e}")
            return {}
    
    def _save_json(self, file_path: Path, data: dict) -> None:
        """Save JSON to file."""
        try:
            file_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), 
                               encoding="utf-8")
            logger.debug(f"Saved {file_path.name}")
        except Exception as e:
            logger.error(f"Error saving {file_path.name}: {e}")
    
    # Facts management
    def add_fact(self, fact_id: str, fact: str, category: str = "general", 
                 confidence: float = 1.0) -> None:
        """Store a fact in long-term memory."""
        facts = self._load_json(self.facts_file)
        facts[fact_id] = {
            "fact": fact,
            "category": category,
            "confidence": confidence,
            "timestamp": datetime.now().isoformat(),
            "access_count": 0
        }
        self._save_json(self.facts_file, facts)
        logger.info(f"Added fact: {fact_id}")
    
    def get_fact(self, fact_id: str) -> Optional[dict]:
        """Retrieve a fact from long-term memory."""
        facts = self._load_json(self.facts_file)
        if fact_id in facts:
            fact_data = facts[fact_id]
            fact_data["access_count"] += 1
            self._save_json(self.facts_file, facts)
            return fact_data
        return None
    
    def get_facts_by_category(self, category: str) -> list:
        """Get all facts in a category."""
        facts = self._load_json(self.facts_file)
        return [f for f in facts.values() if f.get("category") == category]
    
    def get_all_facts(self) -> dict:
        """Get all stored facts."""
        return self._load_json(self.facts_file)
    
    # Summaries management
    def add_summary(self, summary_id: str, summary: str, 
                   message_count: int = 0) -> None:
        """Store a conversation summary."""
        summaries = self._load_json(self.summaries_file)
        summaries[summary_id] = {
            "summary": summary,
            "message_count": message_count,
            "timestamp": datetime.now().isoformat()
        }
        self._save_json(self.summaries_file, summaries)
        logger.info(f"Added summary: {summary_id}")
    
    def get_summaries(self, limit: int = 5) -> list:
        """Get recent summaries."""
        summaries = self._load_json(self.summaries_file)
        sorted_summaries = sorted(
            summaries.values(),
            key=lambda x: x["timestamp"],
            reverse=True
        )
        return sorted_summaries[:limit]
    
    # Preferences management
    def set_preference(self, key: str, value: Any) -> None:
        """Store a user preference."""
        prefs = self._load_json(self.preferences_file)
        prefs[key] = {
            "value": value,
            "timestamp": datetime.now().isoformat()
        }
        self._save_json(self.preferences_file, prefs)
        logger.debug(f"Set preference: {key}")
    
    def get_preference(self, key: str, default: Any = None) -> Any:
        """Get a user preference."""
        prefs = self._load_json(self.preferences_file)
        if key in prefs:
            return prefs[key].get("value", default)
        return default
    
    def get_all_preferences(self) -> dict:
        """Get all preferences."""
        prefs = self._load_json(self.preferences_file)
        return {k: v.get("value") for k, v in prefs.items()}
    
    # Patterns management
    def add_pattern(self, pattern_id: str, pattern: str, 
                   frequency: int = 1) -> None:
        """Store a behavioral pattern."""
        patterns = self._load_json(self.patterns_file)
        if pattern_id in patterns:
            patterns[pattern_id]["frequency"] += frequency
            patterns[pattern_id]["last_seen"] = datetime.now().isoformat()
        else:
            patterns[pattern_id] = {
                "pattern": pattern,
                "frequency": frequency,
                "first_seen": datetime.now().isoformat(),
                "last_seen": datetime.now().isoformat()
            }
        self._save_json(self.patterns_file, patterns)
        logger.debug(f"Added/updated pattern: {pattern_id}")
    
    def get_common_patterns(self, limit: int = 5) -> list:
        """Get most common patterns."""
        patterns = self._load_json(self.patterns_file)
        sorted_patterns = sorted(
            patterns.values(),
            key=lambda x: x["frequency"],
            reverse=True
        )
        return sorted_patterns[:limit]


class MemoryManager:
    """Unified memory management combining short and long-term memory."""
    
    def __init__(self, workspace_path: str, max_short_term: int = 50):
        self.short_term = ShortTermMemory(max_messages=max_short_term)
        memory_dir = Path(workspace_path) / "memory"
        self.long_term = LongTermMemory(str(memory_dir))
        
        logger.info(f"MemoryManager initialized with workspace: {workspace_path}")
    
    def add_message(self, role: str, content: str, metadata: dict = None) -> None:
        """Add message to short-term memory and track in long-term."""
        self.short_term.add_message(role, content, metadata)
        
        # Track message type pattern in long-term memory
        if role:
            self.long_term.add_pattern(f"message_type_{role}", f"User message: {content[:50]}...")
    
    def should_summarize(self, message_threshold: int = 30) -> bool:
        """Check if conversation should be summarized."""
        return len(self.short_term.messages) >= message_threshold
    
    def create_summary(self, summary_id: str, summary_text: str) -> None:
        """Create and store a conversation summary."""
        message_count = len(self.short_term.messages)
        self.long_term.add_summary(summary_id, summary_text, message_count)
        logger.info(f"Created summary with {message_count} messages")
    
    def get_context_for_llm(self, include_facts: bool = True, 
                           include_patterns: bool = True) -> str:
        """Generate context string for LLM incorporating memories."""
        context_parts = []
        
        if include_facts:
            facts = self.long_term.get_all_facts()
            if facts:
                context_parts.append("## Known Facts:")
                for fact_id, fact_data in list(facts.items())[:5]:  # Top 5 facts
                    context_parts.append(f"- {fact_data['fact']}")
        
        if include_patterns:
            patterns = self.long_term.get_common_patterns(limit=3)
            if patterns:
                context_parts.append("\n## Common Patterns:")
                for pattern in patterns:
                    context_parts.append(f"- {pattern['pattern']} (frequency: {pattern['frequency']})")
        
        return "\n".join(context_parts) if context_parts else ""
    
    def get_memory_stats(self) -> dict:
        """Get statistics about current memory usage."""
        return {
            "short_term_messages": len(self.short_term.messages),
            "short_term_capacity": self.short_term.max_messages,
            "total_facts": len(self.long_term.get_all_facts()),
            "total_patterns": len(self.long_term._load_json(self.long_term.patterns_file)),
            "recent_summaries": len(self.long_term._load_json(self.long_term.summaries_file))
        }

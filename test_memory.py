#!/usr/bin/env python3
"""Test script demonstrating memory system functionality."""

import sys
from pathlib import Path

# Add src to path
backend_dir = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_dir / "src"))
sys.path.insert(0, str(backend_dir / "src" / "agent"))

from agent.memory import MemoryManager, ShortTermMemory, LongTermMemory

def test_short_term_memory():
    """Test short-term memory functionality."""
    print("\n=== Testing Short-Term Memory ===")
    
    stm = ShortTermMemory(max_messages=10)
    
    # Add messages
    stm.add_message("user", "Hello, how are you?")
    stm.add_message("assistant", "I'm doing well, thank you for asking!")
    stm.add_message("user", "What's the weather?")
    
    print(f"Messages in memory: {len(stm.messages)}")
    print(f"Recent messages: {stm.get_recent_messages(limit=2)}")
    
    # Test context
    stm.set_context("user_timezone", "UTC+8")
    stm.set_context("response_language", "Chinese")
    print(f"Context: {stm.context}")
    
    # Test topic
    stm.set_topic("weather inquiry")
    print(f"Current topic: {stm.get_topic()}")

def test_long_term_memory():
    """Test long-term memory functionality."""
    print("\n=== Testing Long-Term Memory ===")
    
    ltm = LongTermMemory("./test_memory")
    
    # Test facts
    print("\n--- Testing Facts ---")
    ltm.add_fact("user_lang", "User prefers Chinese responses", "user_preference", 0.95)
    ltm.add_fact("user_timezone", "User is in UTC+8", "location", 0.9)
    ltm.add_fact("user_role", "User is a developer", "user_info", 0.85)
    
    fact = ltm.get_fact("user_lang")
    print(f"Retrieved fact: {fact['fact']}")
    
    category_facts = ltm.get_facts_by_category("user_preference")
    print(f"Facts in 'user_preference' category: {len(category_facts)}")
    
    # Test preferences
    print("\n--- Testing Preferences ---")
    ltm.set_preference("output_format", "markdown")
    ltm.set_preference("verbosity", "concise")
    
    pref = ltm.get_preference("output_format")
    print(f"Retrieved preference: output_format = {pref}")
    
    all_prefs = ltm.get_all_preferences()
    print(f"All preferences: {all_prefs}")
    
    # Test patterns
    print("\n--- Testing Patterns ---")
    ltm.add_pattern("message_greeting", "User greets agent", frequency=5)
    ltm.add_pattern("message_question", "User asks questions", frequency=8)
    ltm.add_pattern("tool_execution", "User requests tool execution", frequency=3)
    
    patterns = ltm.get_common_patterns(limit=2)
    print(f"Top patterns: {[p['pattern'] for p in patterns]}")
    
    # Test summaries
    print("\n--- Testing Summaries ---")
    ltm.add_summary("conv_001", "Discussion about Python programming", message_count=15)
    ltm.add_summary("conv_002", "Weather and climate inquiry", message_count=8)
    
    summaries = ltm.get_summaries(limit=2)
    print(f"Recent summaries: {len(summaries)}")
    for summary in summaries:
        print(f"  - {summary['summary']}")

def test_memory_manager():
    """Test unified memory manager."""
    print("\n=== Testing Memory Manager ===")
    
    mm = MemoryManager("./test_workspace")
    
    # Add some messages
    mm.add_message("user", "How do I learn Python?")
    mm.add_message("assistant", "Here are some great resources to learn Python...")
    mm.add_message("user", "Thanks, can you help with my code?")
    mm.add_message("assistant", "Sure, I'd be happy to help!")
    
    # Check if summarization is needed
    print(f"Should summarize: {mm.should_summarize(message_threshold=30)}")
    
    # Get memory stats
    stats = mm.get_memory_stats()
    print(f"\nMemory Stats:")
    print(f"  Short-term messages: {stats['short_term_messages']}")
    print(f"  Total facts: {stats['total_facts']}")
    print(f"  Total patterns: {stats['total_patterns']}")
    
    # Get LLM context
    context = mm.get_context_for_llm(include_facts=True, include_patterns=True)
    if context:
        print(f"\nLLM Context:\n{context}")
    else:
        print("\nNo memory context to include in LLM prompt yet.")

def main():
    """Run all tests."""
    print("Starting Memory System Tests...")
    
    try:
        test_short_term_memory()
        test_long_term_memory()
        test_memory_manager()
        
        print("\n=== All Tests Completed Successfully ===\n")
    except Exception as e:
        print(f"\nError during testing: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()

import React, { useState, useEffect, useRef } from 'react'
import './Chat.css'

interface Message {
  role: 'user' | 'assistant' | 'system' | 'error'
  content: string
  timestamp: Date
}

export function Chat() {
  const [messages, setMessages] = useState<Message[]>([])
  const [inputValue, setInputValue] = useState('')
  const [isConnected, setIsConnected] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [toolStatus, setToolStatus] = useState<string | null>(null)
  const [currentAssistantMessage, setCurrentAssistantMessage] = useState('')
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const wsRef = useRef<WebSocket | null>(null)

  // Connect to WebSocket
  useEffect(() => {
    const ws = new WebSocket('ws://127.0.0.1:8765/ws')
    
    ws.onopen = () => {
      console.log('WebSocket connected')
      setIsConnected(true)
    }
    
    ws.onmessage = (event: MessageEvent) => {
      const data = JSON.parse(event.data)
      console.log('Received:', data)
      
      if (data.type === 'text') {
        // Accumulate assistant message text
        setCurrentAssistantMessage(prev => prev + data.data)
      } else if (data.type === 'tool_start') {
        const toolData = data.data
        setToolStatus(`⚙️ Executing: ${toolData.tool}`)
        // Save current assistant message if any
        if (currentAssistantMessage) {
          setMessages(prev => [...prev, {
            role: 'assistant',
            content: currentAssistantMessage,
            timestamp: new Date()
          }])
          setCurrentAssistantMessage('')
        }
      } else if (data.type === 'tool_result') {
        setToolStatus(`✓ Tool completed`)
        // Show tool result
        setMessages(prev => [...prev, {
          role: 'system',
          content: `Tool output: ${data.data}`,
          timestamp: new Date()
        }])
        // Clear tool status after a short delay
        setTimeout(() => setToolStatus(null), 1500)
      } else if (data.type === 'end') {
        // Conversation ended - save any remaining message
        if (currentAssistantMessage) {
          setMessages(prev => [...prev, {
            role: 'assistant',
            content: currentAssistantMessage,
            timestamp: new Date()
          }])
          setCurrentAssistantMessage('')
        }
        setIsLoading(false)
      } else if (data.type === 'error') {
        // Save current assistant message if any
        if (currentAssistantMessage) {
          setMessages(prev => [...prev, {
            role: 'assistant',
            content: currentAssistantMessage,
            timestamp: new Date()
          }])
          setCurrentAssistantMessage('')
        }
        setMessages(prev => [...prev, {
          role: 'error',
          content: `Error: ${data.data}`,
          timestamp: new Date()
        }])
        setIsLoading(false)
      }
    }
    
    ws.onerror = (error: Event) => {
      console.error('WebSocket error:', error)
      setIsConnected(false)
    }
    
    ws.onclose = () => {
      console.log('WebSocket disconnected')
      setIsConnected(false)
    }
    
    wsRef.current = ws
    
    return () => {
      ws.close()
    }
  }, [])

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, toolStatus, currentAssistantMessage, isLoading])

  const sendMessage = async () => {
    if (!inputValue.trim() || !isConnected) return

    const userMessage: Message = {
      role: 'user',
      content: inputValue,
      timestamp: new Date()
    }

    setMessages(prev => [...prev, userMessage])
    setInputValue('')
    setIsLoading(true)
    setCurrentAssistantMessage('')
    setToolStatus(null)

    // Send to gateway
    wsRef.current?.send(JSON.stringify({
      type: 'chat',
      data: inputValue
    }))
  }

  const handleKeyPress = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  const resetConversation = () => {
    setMessages([])
    setToolStatus(null)
    setCurrentAssistantMessage('')
    wsRef.current?.send(JSON.stringify({
      type: 'reset',
      data: null
    }))
  }

  return (
    <div className="chat-container">
      <div className="chat-header">
        <h1>AI Agent Chat</h1>
        <div className="connection-status">
          <span className={`status-indicator ${isConnected ? 'connected' : 'disconnected'}`}></span>
          <span>{isConnected ? 'Connected' : 'Disconnected'}</span>
        </div>
      </div>

      <div className="messages-container">
        {messages.length === 0 && !currentAssistantMessage && (
          <div className="empty-state">
            <p>Start a conversation with the AI Agent</p>
            <p className="hint">You can ask it to perform file operations or queries</p>
          </div>
        )}
        
        {messages.map((msg, idx) => (
          <div key={idx} className={`message message-${msg.role}`}>
            <div className="message-role">{msg.role.toUpperCase()}</div>
            <div className="message-content">{msg.content}</div>
            <div className="message-time">
              {msg.timestamp.toLocaleTimeString()}
            </div>
          </div>
        ))}
        
        {currentAssistantMessage && (
          <div className="message message-assistant">
            <div className="message-role">ASSISTANT</div>
            <div className="message-content">{currentAssistantMessage}</div>
          </div>
        )}
        
        {toolStatus && (
          <div className="tool-status">
            <span className="spinner"></span>
            {toolStatus}
          </div>
        )}
        
        {isLoading && !currentAssistantMessage && !toolStatus && (
          <div className="message message-assistant">
            <div className="typing-indicator">
              <span></span>
              <span></span>
              <span></span>
            </div>
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>

      <div className="chat-footer">
        <div className="input-group">
          <textarea
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Type your message..."
            disabled={!isConnected}
            rows={3}
          />
          <button
            onClick={sendMessage}
            disabled={!isConnected || !inputValue.trim() || isLoading}
            className="send-button"
          >
            Send
          </button>
        </div>
        <button
          onClick={resetConversation}
          disabled={!isConnected}
          className="reset-button"
        >
          Reset Conversation
        </button>
      </div>
    </div>
  )
}

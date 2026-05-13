'use client'

import { useState, useEffect } from 'react'
import { getHistory, PromptRecord } from '@/lib/api'

interface Props {
  isOpen: boolean
  onClose: () => void
  onReuse: (question: string) => void
}

function formatRelativeTime(dateStr: string): string {
  const date = new Date(dateStr)
  const now = new Date()
  const seconds = Math.floor((now.getTime() - date.getTime()) / 1000)

  if (seconds < 60) return 'just now'
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`
  if (seconds < 604800) return `${Math.floor(seconds / 86400)}d ago`

  return date.toLocaleDateString()
}

export default function HistoryPanel({ isOpen, onClose, onReuse }: Props) {
  const [history, setHistory] = useState<PromptRecord[]>([])
  const [currentIndex, setCurrentIndex] = useState(0)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Fetch history when panel opens
  useEffect(() => {
    if (!isOpen) return

    const fetchHistory = async () => {
      setIsLoading(true)
      setError(null)
      try {
        const response = await getHistory()
        setHistory(response.history)
        setCurrentIndex(0)
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : 'Failed to load history')
      } finally {
        setIsLoading(false)
      }
    }

    void fetchHistory()
  }, [isOpen])

  if (!isOpen) return null

  const currentPrompt = history[currentIndex] || null
  const totalCount = history.length

  const handlePrev = () => {
    if (currentIndex < totalCount - 1) {
      setCurrentIndex(currentIndex + 1)
    }
  }

  const handleNext = () => {
    if (currentIndex > 0) {
      setCurrentIndex(currentIndex - 1)
    }
  }

  const handleSelectFromList = (index: number) => {
    setCurrentIndex(index)
  }

  const handleReuse = () => {
    if (currentPrompt) {
      onReuse(currentPrompt.question)
    }
  }

  const panelStyle: React.CSSProperties = {
    position: 'fixed',
    bottom: 24,
    right: 24,
    width: 360,
    maxHeight: 480,
    backgroundColor: '#fff',
    boxShadow: '0 4px 12px rgba(0, 0, 0, 0.15)',
    borderRadius: 12,
    zIndex: 1000,
    display: 'flex',
    flexDirection: 'column',
  }

  const headerStyle: React.CSSProperties = {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '12px 16px',
    borderBottom: '1px solid #e0e0e0',
    flexShrink: 0,
  }

  const contentStyle: React.CSSProperties = {
    flex: 1,
    overflow: 'hidden',
    display: 'flex',
    flexDirection: 'column',
    padding: '16px',
  }

  const currentItemStyle: React.CSSProperties = {
    marginBottom: 16,
    flexShrink: 0,
  }

  const questionStyle: React.CSSProperties = {
    fontWeight: 600,
    fontSize: 14,
    marginBottom: 8,
    color: '#333',
  }

  const answerStyle: React.CSSProperties = {
    fontSize: 13,
    lineHeight: 1.5,
    maxHeight: 120,
    overflowY: 'auto',
    marginBottom: 8,
    color: '#555',
    paddingRight: 4,
  }

  const sheetNameStyle: React.CSSProperties = {
    fontSize: 11,
    color: '#888',
    marginBottom: 8,
  }

  const feedbackStyle: React.CSSProperties = {
    fontSize: 13,
    marginBottom: 8,
  }

  const navStyle: React.CSSProperties = {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 12,
    flexShrink: 0,
  }

  const navButtonStyle: React.CSSProperties = {
    padding: '4px 10px',
    fontSize: 12,
    border: '1px solid #ccc',
    borderRadius: 4,
    backgroundColor: '#fff',
    cursor: 'pointer',
  }

  const navButtonDisabledStyle: React.CSSProperties = {
    ...navButtonStyle,
    color: '#ccc',
    cursor: 'not-allowed',
    opacity: 0.6,
  }

  const counterStyle: React.CSSProperties = {
    fontSize: 12,
    color: '#666',
  }

  const reuseButtonStyle: React.CSSProperties = {
    padding: '6px 12px',
    fontSize: 13,
    backgroundColor: '#2563eb',
    color: '#fff',
    border: 'none',
    borderRadius: 4,
    cursor: 'pointer',
    width: '100%',
    flexShrink: 0,
  }

  const historyListStyle: React.CSSProperties = {
    maxHeight: 160,
    overflowY: 'auto',
    border: '1px solid #e0e0e0',
    borderRadius: 6,
    flexShrink: 0,
  }

  const historyItemStyle = (isSelected: boolean): React.CSSProperties => ({
    padding: '8px 12px',
    fontSize: 12,
    borderBottom: '1px solid #f0f0f0',
    cursor: 'pointer',
    backgroundColor: isSelected ? '#e3f2fd' : '#fff',
    color: isSelected ? '#2563eb' : '#333',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap',
    transition: 'background-color 0.2s',
  })

  return (
    <div style={panelStyle}>
      {/* Header */}
      <div style={headerStyle}>
        <h3 style={{ margin: 0, fontSize: 14, fontWeight: 600, color: '#333' }}>
          Prompt History
        </h3>
        <button
          onClick={onClose}
          style={{
            background: 'none',
            border: 'none',
            fontSize: 18,
            cursor: 'pointer',
            padding: 0,
            color: '#666',
          }}
        >
          ×
        </button>
      </div>

      {/* Content */}
      <div style={contentStyle}>
        {isLoading && (
          <p style={{ margin: 0, fontSize: 13, color: '#888' }}>Loading...</p>
        )}

        {error && (
          <p style={{ margin: 0, fontSize: 13, color: '#d9534f' }}>{error}</p>
        )}

        {!isLoading && !error && totalCount === 0 && (
          <p style={{ margin: 0, fontSize: 13, color: '#888' }}>No prompts yet.</p>
        )}

        {!isLoading && !error && totalCount > 0 && currentPrompt && (
          <>
            {/* Current item display */}
            <div style={currentItemStyle}>
              <div style={questionStyle}>{currentPrompt.question}</div>
              <div style={answerStyle}>{currentPrompt.answer}</div>
              <div style={sheetNameStyle}>Sheet: {currentPrompt.sheet_name}</div>
              <div style={feedbackStyle}>
                {currentPrompt.feedback === 'up' && '👍'}
                {currentPrompt.feedback === 'down' && '👎'}
              </div>
            </div>

            {/* Navigation */}
            {totalCount > 1 && (
              <div style={navStyle}>
                <button
                  onClick={handlePrev}
                  disabled={currentIndex >= totalCount - 1}
                  style={
                    currentIndex >= totalCount - 1
                      ? navButtonDisabledStyle
                      : navButtonStyle
                  }
                >
                  ◀ prev
                </button>
                <span style={counterStyle}>
                  {currentIndex + 1} of {totalCount}
                </span>
                <button
                  onClick={handleNext}
                  disabled={currentIndex === 0}
                  style={currentIndex === 0 ? navButtonDisabledStyle : navButtonStyle}
                >
                  next ▶
                </button>
              </div>
            )}

            {/* Re-use button */}
            <button
              onClick={handleReuse}
              style={reuseButtonStyle}
            >
              Re-use
            </button>

            {/* History list */}
            {totalCount > 0 && (
              <div style={{ marginTop: 12 }}>
                <div style={historyListStyle}>
                  {history.map((item, idx) => (
                    <div
                      key={item.id}
                      onClick={() => handleSelectFromList(idx)}
                      style={historyItemStyle(idx === currentIndex)}
                      title={item.question}
                    >
                      {item.question} • {formatRelativeTime(item.created_at)}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}

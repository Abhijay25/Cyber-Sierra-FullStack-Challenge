'use client'

import { useState, useEffect, KeyboardEvent } from 'react'
import { querySheet, submitFeedback } from '@/lib/api'

interface Props {
  sheetName: string
  n: number
  onHistoryOpen: () => void
  initialQuestion?: string
}

export default function QueryInterface({ sheetName, n, onHistoryOpen, initialQuestion }: Props) {
  const [question, setQuestion] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [answer, setAnswer] = useState<string | null>(null)
  const [promptId, setPromptId] = useState<number | null>(null)
  const [feedbackGiven, setFeedbackGiven] = useState<'up' | 'down' | null>(null)
  const [showCommentInput, setShowCommentInput] = useState(false)
  const [comment, setComment] = useState('')
  const [error, setError] = useState<string | null>(null)

  // Reset all state when sheetName changes
  useEffect(() => {
    setQuestion('')
    setIsLoading(false)
    setAnswer(null)
    setPromptId(null)
    setFeedbackGiven(null)
    setShowCommentInput(false)
    setComment('')
    setError(null)
  }, [sheetName])

  // Set question when initialQuestion changes
  useEffect(() => {
    if (initialQuestion) {
      setQuestion(initialQuestion)
    }
  }, [initialQuestion])

  const handleSubmit = async () => {
    if (!question.trim() || isLoading) return

    setAnswer(null)
    setPromptId(null)
    setFeedbackGiven(null)
    setShowCommentInput(false)
    setComment('')
    setError(null)
    setIsLoading(true)

    try {
      const result = await querySheet(sheetName, question, n)
      setAnswer(result.answer)
      setPromptId(result.prompt_id)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to get an answer.')
    } finally {
      setIsLoading(false)
    }
  }

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      void handleSubmit()
    }
  }

  const handleThumbsUp = async () => {
    if (promptId === null) return
    try {
      await submitFeedback(promptId, 'up')
    } catch {
      // best-effort; don't surface feedback errors
    }
    setFeedbackGiven('up')
  }

  const handleThumbsDown = () => {
    setShowCommentInput(true)
  }

  const handleCommentSubmit = async () => {
    if (promptId === null) return
    try {
      await submitFeedback(promptId, 'down', comment)
    } catch {
      // best-effort
    }
    setFeedbackGiven('down')
    setShowCommentInput(false)
  }

  return (
    <div style={{ marginBottom: 32 }}>
      {/* Input row */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
        <input
          type="text"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={isLoading}
          placeholder={`Ask a question about ${sheetName}...`}
          style={{
            flex: 1,
            padding: '8px 12px',
            border: '1px solid #ccc',
            borderRadius: 6,
            fontSize: 14,
            color: '#333',
            backgroundColor: isLoading ? '#f5f5f5' : '#fff',
            outline: 'none',
          }}
        />
        <button
          onClick={() => { void handleSubmit() }}
          disabled={isLoading || !question.trim()}
          style={{
            padding: '8px 18px',
            backgroundColor: isLoading || !question.trim() ? '#aaa' : '#2563eb',
            color: '#fff',
            border: 'none',
            borderRadius: 6,
            fontSize: 14,
            fontWeight: 500,
            cursor: isLoading || !question.trim() ? 'not-allowed' : 'pointer',
            whiteSpace: 'nowrap',
          }}
        >
          {isLoading ? '...' : 'Send'}
        </button>
      </div>

      {/* History button */}
      <div style={{ marginBottom: 16 }}>
        <button
          onClick={onHistoryOpen}
          style={{
            padding: '6px 14px',
            backgroundColor: 'transparent',
            border: '1px solid #ccc',
            borderRadius: 6,
            fontSize: 13,
            cursor: 'pointer',
            color: '#555',
          }}
        >
          📋 History
        </button>
      </div>

      {/* Loading indicator */}
      {isLoading && (
        <p style={{ color: '#888', fontSize: 14, margin: '0 0 12px' }}>Thinking...</p>
      )}

      {/* Error */}
      {error && !isLoading && (
        <p style={{ color: '#d9534f', fontSize: 14, margin: '0 0 12px' }}>{error}</p>
      )}

      {/* Answer card */}
      {answer && !isLoading && (
        <div
          style={{
            border: '1px solid #e0e0e0',
            borderRadius: 8,
            padding: '16px 20px',
            backgroundColor: '#fafafa',
          }}
        >
          <p style={{ margin: '0 0 16px', fontSize: 14, color: '#333', lineHeight: 1.6 }}>
            {answer}
          </p>

          {/* Feedback */}
          {feedbackGiven !== null ? (
            <p style={{ margin: 0, fontSize: 13, color: '#4caf50' }}>Feedback recorded ✓</p>
          ) : (
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span style={{ fontSize: 13, color: '#888' }}>Was this helpful?</span>
              <button
                onClick={() => { void handleThumbsUp() }}
                style={{
                  background: 'none',
                  border: '1px solid #ccc',
                  borderRadius: 4,
                  padding: '2px 8px',
                  cursor: 'pointer',
                  fontSize: 16,
                }}
                title="Thumbs up"
              >
                👍
              </button>
              <button
                onClick={handleThumbsDown}
                style={{
                  background: 'none',
                  border: '1px solid #ccc',
                  borderRadius: 4,
                  padding: '2px 8px',
                  cursor: 'pointer',
                  fontSize: 16,
                }}
                title="Thumbs down"
              >
                👎
              </button>
            </div>
          )}

          {/* Comment input after thumbs down */}
          {showCommentInput && feedbackGiven === null && (
            <div style={{ display: 'flex', gap: 8, marginTop: 12 }}>
              <input
                type="text"
                value={comment}
                onChange={(e) => setComment(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') void handleCommentSubmit()
                }}
                placeholder="What went wrong? (optional)"
                style={{
                  flex: 1,
                  padding: '6px 10px',
                  border: '1px solid #ccc',
                  borderRadius: 6,
                  fontSize: 13,
                  color: '#333',
                }}
              />
              <button
                onClick={() => { void handleCommentSubmit() }}
                style={{
                  padding: '6px 14px',
                  backgroundColor: '#2563eb',
                  color: '#fff',
                  border: 'none',
                  borderRadius: 6,
                  fontSize: 13,
                  cursor: 'pointer',
                }}
              >
                Submit
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

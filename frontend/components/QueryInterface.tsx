'use client'

import { useState, useEffect, useRef, KeyboardEvent } from 'react'
import ReactMarkdown from 'react-markdown'
import type { ConversationTurn } from '@/lib/api'
import { querySheet, submitFeedback } from '@/lib/api'

interface Props {
  sheetName: string
  n: number
  initialQuestion?: string
}

interface Turn extends ConversationTurn {
  promptId: number
  feedback: 'up' | 'down' | null
}

export default function QueryInterface({ sheetName, n, initialQuestion }: Props) {
  const [question, setQuestion] = useState('')
  const [turns, setTurns] = useState<Turn[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [showCommentFor, setShowCommentFor] = useState<number | null>(null)
  const [comment, setComment] = useState('')
  const [error, setError] = useState<string | null>(null)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    setQuestion('')
    setTurns([])
    setIsLoading(false)
    setShowCommentFor(null)
    setComment('')
    setError(null)
  }, [sheetName])

  useEffect(() => {
    if (initialQuestion) setQuestion(initialQuestion)
  }, [initialQuestion])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [turns, isLoading])

  const handleSubmit = async () => {
    if (!question.trim() || isLoading) return
    const q = question.trim()
    setQuestion('')
    setError(null)
    setIsLoading(true)

    try {
      const history: ConversationTurn[] = turns.map(t => ({ question: t.question, answer: t.answer }))
      const result = await querySheet(sheetName, q, n, history)
      setTurns(prev => [...prev, { question: q, answer: result.answer, promptId: result.prompt_id, feedback: null }])
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to get an answer.')
    } finally {
      setIsLoading(false)
    }
  }

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') void handleSubmit()
  }

  const handleThumbsUp = async (idx: number) => {
    const turn = turns[idx]
    if (!turn || turn.feedback !== null) return
    try { await submitFeedback(turn.promptId, 'up') } catch { /* best-effort */ }
    setTurns(prev => prev.map((t, i) => i === idx ? { ...t, feedback: 'up' } : t))
  }

  const handleThumbsDown = (idx: number) => {
    setShowCommentFor(idx)
    setComment('')
  }

  const handleCommentSubmit = async (idx: number) => {
    const turn = turns[idx]
    if (!turn) return
    try { await submitFeedback(turn.promptId, 'down', comment) } catch { /* best-effort */ }
    setTurns(prev => prev.map((t, i) => i === idx ? { ...t, feedback: 'down' } : t))
    setShowCommentFor(null)
  }

  return (
    <div style={{ marginBottom: 32 }}>
      {/* Conversation thread */}
      {turns.length > 0 && (
        <div style={{ marginBottom: 16, display: 'flex', flexDirection: 'column', gap: 16 }}>
          {turns.map((turn, idx) => (
            <div key={idx}>
              {/* Question bubble */}
              <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 6 }}>
                <div style={{
                  background: '#2563eb',
                  color: '#fff',
                  borderRadius: '12px 12px 4px 12px',
                  padding: '8px 14px',
                  fontSize: 14,
                  maxWidth: '70%',
                }}>
                  {turn.question}
                </div>
              </div>

              {/* Answer bubble */}
              <div style={{
                border: '1px solid #e0e0e0',
                borderRadius: '4px 12px 12px 12px',
                padding: '12px 16px',
                backgroundColor: '#fafafa',
                fontSize: 14,
                color: '#333',
                lineHeight: 1.6,
                maxWidth: '85%',
              }}>
                <ReactMarkdown>{turn.answer}</ReactMarkdown>

                {/* Feedback row */}
                <div style={{ marginTop: 10, borderTop: '1px solid #eee', paddingTop: 8 }}>
                  {turn.feedback !== null ? (
                    <span style={{ fontSize: 12, color: '#4caf50' }}>Feedback recorded ✓</span>
                  ) : showCommentFor === idx ? (
                    <div style={{ display: 'flex', gap: 6 }}>
                      <input
                        type="text"
                        value={comment}
                        onChange={(e) => setComment(e.target.value)}
                        onKeyDown={(e) => { if (e.key === 'Enter') void handleCommentSubmit(idx) }}
                        placeholder="What went wrong? (optional)"
                        style={{
                          flex: 1, padding: '4px 8px', border: '1px solid #ccc',
                          borderRadius: 4, fontSize: 12, color: '#333',
                        }}
                      />
                      <button
                        onClick={() => void handleCommentSubmit(idx)}
                        style={{
                          padding: '4px 10px', background: '#2563eb', color: '#fff',
                          border: 'none', borderRadius: 4, fontSize: 12, cursor: 'pointer',
                        }}
                      >Submit</button>
                    </div>
                  ) : (
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                      <span style={{ fontSize: 12, color: '#888' }}>Helpful?</span>
                      <button onClick={() => void handleThumbsUp(idx)} style={feedbackBtnStyle} title="Thumbs up">👍</button>
                      <button onClick={() => handleThumbsDown(idx)} style={feedbackBtnStyle} title="Thumbs down">👎</button>
                    </div>
                  )}
                </div>
              </div>
            </div>
          ))}

          {isLoading && (
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: '#888', fontSize: 13 }}>
              <span style={{ width: 8, height: 8, borderRadius: '50%', background: '#888', display: 'inline-block', animation: 'pulse 1s infinite' }} />
              Thinking…
            </div>
          )}
          <div ref={bottomRef} />
        </div>
      )}

      {error && (
        <p style={{ color: '#d9534f', fontSize: 14, marginBottom: 12 }}>{error}</p>
      )}

      {/* Input row */}
      <div style={{ display: 'flex', gap: 8 }}>
        <input
          type="text"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={isLoading}
          placeholder={turns.length > 0 ? 'Ask a follow-up…' : `Ask a question about ${sheetName}…`}
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
          {isLoading ? '…' : 'Send'}
        </button>
      </div>
    </div>
  )
}

const feedbackBtnStyle: React.CSSProperties = {
  background: 'none',
  border: '1px solid #ddd',
  borderRadius: 4,
  padding: '1px 6px',
  cursor: 'pointer',
  fontSize: 14,
}

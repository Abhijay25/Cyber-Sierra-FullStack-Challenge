'use client'

import { useState, useEffect, useRef, KeyboardEvent } from 'react'
import ReactMarkdown from 'react-markdown'
import type { ConversationTurn, Turn } from '@/lib/api'
import { querySheetStream, submitFeedback } from '@/lib/api'

interface Props {
  sheetName: string
  n: number
  initialQuestion?: string
  turns: Turn[]
  onTurnsChange: (turns: Turn[]) => void
}

export default function QueryInterface({ sheetName, n, initialQuestion, turns, onTurnsChange }: Props) {
  const [question, setQuestion] = useState('')
  const [pendingQuestion, setPendingQuestion] = useState<string | null>(null)
  const [streamingAnswer, setStreamingAnswer] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [showCommentFor, setShowCommentFor] = useState<number | null>(null)
  const [comment, setComment] = useState('')
  const [error, setError] = useState<string | null>(null)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    setQuestion('')
    setPendingQuestion(null)
    setStreamingAnswer('')
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
  }, [turns, streamingAnswer, isLoading])

  const handleSubmit = async () => {
    if (!question.trim() || isLoading || pendingQuestion !== null) return
    const q = question.trim()
    setQuestion('')
    setError(null)
    setIsLoading(true)
    setPendingQuestion(q)
    setStreamingAnswer('')

    let fullAnswer = ''
    let promptId: number | null = null

    try {
      const history: ConversationTurn[] = turns.map(t => ({ question: t.question, answer: t.answer }))

      await querySheetStream(
        sheetName, q, n, history,
        (token) => {
          setIsLoading(false)
          fullAnswer += token
          setStreamingAnswer(s => s + token)
        },
        (pid) => { promptId = pid },
      )

      if (promptId !== null) {
        onTurnsChange([...turns, { question: q, answer: fullAnswer, promptId: promptId!, feedback: null }])
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to get an answer.')
    } finally {
      setIsLoading(false)
      setPendingQuestion(null)
      setStreamingAnswer('')
    }
  }

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') void handleSubmit()
  }

  const handleThumbsUp = async (idx: number) => {
    const turn = turns[idx]
    if (!turn || turn.feedback !== null) return
    try { await submitFeedback(turn.promptId, 'up') } catch { /* best-effort */ }
    onTurnsChange(turns.map((t, i) => i === idx ? { ...t, feedback: 'up' } : t))
  }

  const handleThumbsDown = (idx: number) => {
    setShowCommentFor(idx)
    setComment('')
  }

  const handleCommentSubmit = async (idx: number) => {
    const turn = turns[idx]
    if (!turn) return
    try { await submitFeedback(turn.promptId, 'down', comment) } catch { /* best-effort */ }
    onTurnsChange(turns.map((t, i) => i === idx ? { ...t, feedback: 'down' } : t))
    setShowCommentFor(null)
  }

  return (
    <div style={{ marginBottom: 32 }}>
      {/* Completed turns */}
      {(turns.length > 0 || pendingQuestion) && (
        <div style={{ marginBottom: 16, display: 'flex', flexDirection: 'column', gap: 16 }}>
          {turns.map((turn, idx) => (
            <div key={idx}>
              <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 6 }}>
                <div style={questionBubbleStyle}>{turn.question}</div>
              </div>
              <div style={answerBubbleStyle}>
                <ReactMarkdown>{turn.answer}</ReactMarkdown>
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
                        maxLength={200}
                        style={commentInputStyle}
                      />
                      <button onClick={() => void handleCommentSubmit(idx)} style={submitBtnStyle}>
                        Submit
                      </button>
                    </div>
                  ) : (
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                      <span style={{ fontSize: 12, color: '#888' }}>Helpful?</span>
                      <button onClick={() => void handleThumbsUp(idx)} style={feedbackBtnStyle}>👍</button>
                      <button onClick={() => handleThumbsDown(idx)} style={feedbackBtnStyle}>👎</button>
                    </div>
                  )}
                </div>
              </div>
            </div>
          ))}

          {/* In-flight turn */}
          {pendingQuestion && (
            <div>
              <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 6 }}>
                <div style={questionBubbleStyle}>{pendingQuestion}</div>
              </div>
              {isLoading && !streamingAnswer ? (
                <div style={{ color: '#888', fontSize: 13, padding: '8px 0' }}>Thinking…</div>
              ) : streamingAnswer ? (
                <div style={{ ...answerBubbleStyle, borderStyle: 'dashed' }}>
                  <ReactMarkdown>{streamingAnswer}</ReactMarkdown>
                  <span style={{ display: 'inline-block', width: 2, height: '1em', background: '#888', marginLeft: 1, verticalAlign: 'text-bottom', animation: 'blink 1s step-end infinite' }} />
                </div>
              ) : null}
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
          disabled={isLoading || pendingQuestion !== null}
          placeholder={turns.length > 0 ? 'Ask a follow-up…' : `Ask a question about ${sheetName}…`}
          style={{
            flex: 1,
            padding: '8px 12px',
            border: '1px solid #ccc',
            borderRadius: 6,
            fontSize: 14,
            color: '#333',
            backgroundColor: (isLoading || pendingQuestion !== null) ? '#f5f5f5' : '#fff',
            outline: 'none',
          }}
        />
        <button
          onClick={() => { void handleSubmit() }}
          disabled={isLoading || pendingQuestion !== null || !question.trim()}
          style={{
            padding: '8px 18px',
            backgroundColor: (isLoading || pendingQuestion !== null || !question.trim()) ? '#aaa' : '#2563eb',
            color: '#fff',
            border: 'none',
            borderRadius: 6,
            fontSize: 14,
            fontWeight: 500,
            cursor: (isLoading || pendingQuestion !== null || !question.trim()) ? 'not-allowed' : 'pointer',
            whiteSpace: 'nowrap',
          }}
        >
          Send
        </button>
      </div>
    </div>
  )
}

const questionBubbleStyle: React.CSSProperties = {
  background: '#2563eb',
  color: '#fff',
  borderRadius: '12px 12px 4px 12px',
  padding: '8px 14px',
  fontSize: 14,
  maxWidth: '70%',
}

const answerBubbleStyle: React.CSSProperties = {
  border: '1px solid #e0e0e0',
  borderRadius: '4px 12px 12px 12px',
  padding: '12px 16px',
  backgroundColor: '#fafafa',
  fontSize: 14,
  color: '#333',
  lineHeight: 1.6,
  maxWidth: '85%',
}

const feedbackBtnStyle: React.CSSProperties = {
  background: 'none',
  border: '1px solid #ddd',
  borderRadius: 4,
  padding: '1px 6px',
  cursor: 'pointer',
  fontSize: 14,
}

const commentInputStyle: React.CSSProperties = {
  flex: 1,
  padding: '4px 8px',
  border: '1px solid #ccc',
  borderRadius: 4,
  fontSize: 12,
  color: '#333',
}

const submitBtnStyle: React.CSSProperties = {
  padding: '4px 10px',
  background: '#2563eb',
  color: '#fff',
  border: 'none',
  borderRadius: 4,
  fontSize: 12,
  cursor: 'pointer',
}

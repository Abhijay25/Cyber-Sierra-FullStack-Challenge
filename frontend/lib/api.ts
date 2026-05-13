const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

// Types
export interface SheetMeta {
  name: string
  row_count: number
  columns: string[]
}

export interface UploadResponse {
  sheets: SheetMeta[]
}

export interface DataResponse {
  rows: Record<string, unknown>[]
  columns: string[]
}

export interface PromptRecord {
  id: number
  sheet_name: string
  question: string
  answer: string
  feedback: 'up' | 'down' | null
  comment: string | null
  created_at: string
}

export interface HistoryResponse {
  history: PromptRecord[]
}

export interface QueryResponse {
  prompt_id: number
  answer: string
}

// Helper function for JSON requests
async function jsonFetch<T>(
  endpoint: string,
  options: RequestInit & { method: string }
): Promise<T> {
  const response = await fetch(`${BASE_URL}${endpoint}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
    credentials: 'include',
  })

  if (!response.ok) {
    let errorMessage = `HTTP ${response.status}`
    try {
      const errorData = await response.json()
      errorMessage = errorData.detail || errorData.message || errorMessage
    } catch {
      // If response body is not JSON, use default message
    }
    throw new Error(errorMessage)
  }

  return response.json()
}

// API functions
export async function uploadFiles(files: File[]): Promise<UploadResponse> {
  const formData = new FormData()
  files.forEach((file) => {
    formData.append('files', file)
  })

  const response = await fetch(`${BASE_URL}/api/upload`, {
    method: 'POST',
    body: formData,
    credentials: 'include',
  })

  if (!response.ok) {
    let errorMessage = `HTTP ${response.status}`
    try {
      const errorData = await response.json()
      errorMessage = errorData.detail || errorData.message || errorMessage
    } catch {
      // If response body is not JSON, use default message
    }
    throw new Error(errorMessage)
  }

  return response.json()
}

export async function getSheets(): Promise<UploadResponse> {
  return jsonFetch<UploadResponse>('/api/sheets', {
    method: 'GET',
  })
}

export async function getData(
  sheetName: string,
  n: number
): Promise<DataResponse> {
  const encodedSheet = encodeURIComponent(sheetName)
  return jsonFetch<DataResponse>(`/api/data/${encodedSheet}?n=${n}`, {
    method: 'GET',
  })
}

export interface ConversationTurn {
  question: string
  answer: string
}

export interface Turn extends ConversationTurn {
  promptId: number
  feedback: 'up' | 'down' | null
}

export async function querySheetStream(
  sheetName: string,
  question: string,
  n: number,
  history: ConversationTurn[],
  onToken: (token: string) => void,
  onDone: (promptId: number) => void,
): Promise<void> {
  const response = await fetch(`${BASE_URL}/api/query`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify({ sheet_name: sheetName, question, n, history }),
  })

  if (!response.ok) {
    let errorMessage = `HTTP ${response.status}`
    try {
      const errorData = await response.json()
      errorMessage = errorData.detail || errorMessage
    } catch { /* ignore */ }
    throw new Error(errorMessage)
  }

  const reader = response.body!.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  try {
    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() ?? ''

      for (const line of lines) {
        if (!line.startsWith('data: ')) continue
        const jsonStr = line.slice(6).trim()
        if (!jsonStr) continue
        let data: { token?: string; done?: boolean; prompt_id?: number; error?: string }
        try {
          data = JSON.parse(jsonStr)
        } catch {
          continue
        }
        if (data.error) throw new Error(data.error)
        if (data.done && data.prompt_id !== undefined) onDone(data.prompt_id)
        else if (data.token) onToken(data.token)
      }
    }
  } finally {
    reader.releaseLock()
  }
}

export async function deleteSheet(sheetName: string): Promise<void> {
  const encodedSheet = encodeURIComponent(sheetName)
  await jsonFetch<{ deleted: string }>(`/api/sheets/${encodedSheet}`, {
    method: 'DELETE',
  })
}

export async function getHistory(): Promise<HistoryResponse> {
  return jsonFetch<HistoryResponse>('/api/history', {
    method: 'GET',
  })
}

export async function submitFeedback(
  promptId: number,
  feedback: 'up' | 'down',
  comment?: string
): Promise<void> {
  await jsonFetch<void>('/api/feedback', {
    method: 'POST',
    body: JSON.stringify({
      prompt_id: promptId,
      feedback: feedback,
      comment: comment ?? null,
    }),
  })
}

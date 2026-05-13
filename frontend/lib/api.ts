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

export async function querySheet(
  sheetName: string,
  question: string,
  n: number,
): Promise<QueryResponse> {
  return jsonFetch<QueryResponse>('/api/query', {
    method: 'POST',
    body: JSON.stringify({
      sheet_name: sheetName,
      question: question,
      n,
    }),
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

'use client'

import { useRef, useState, DragEvent, ChangeEvent } from 'react'
import type { SheetMeta } from '@/lib/api'
import { uploadFiles } from '@/lib/api'

interface Props {
  onUpload: (sheets: SheetMeta[]) => void
  isUploading: boolean
  setIsUploading: (v: boolean) => void
}

const ACCEPTED_EXTENSIONS = ['.csv', '.xls', '.xlsx']
const ACCEPTED_MIME = [
  'text/csv',
  'application/vnd.ms-excel',
  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
]

function isValidFile(file: File): boolean {
  const nameLower = file.name.toLowerCase()
  return ACCEPTED_EXTENSIONS.some((ext) => nameLower.endsWith(ext)) ||
    ACCEPTED_MIME.includes(file.type)
}

export default function FileUpload({ onUpload, isUploading, setIsUploading }: Props) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [dragOver, setDragOver] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleFiles(files: File[]) {
    const valid = files.filter(isValidFile)
    if (valid.length === 0) {
      setError('Only .csv, .xls, and .xlsx files are accepted.')
      return
    }
    if (valid.length < files.length) {
      setError(`${files.length - valid.length} file(s) skipped — unsupported format.`)
    } else {
      setError(null)
    }

    setIsUploading(true)
    try {
      const result = await uploadFiles(valid)
      onUpload(result.sheets)
      // Reset input so the same file can be re-uploaded
      if (inputRef.current) {
        inputRef.current.value = ''
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed.')
    } finally {
      setIsUploading(false)
    }
  }

  function onDrop(e: DragEvent<HTMLDivElement>) {
    e.preventDefault()
    setDragOver(false)
    if (isUploading) return
    const files = Array.from(e.dataTransfer.files)
    void handleFiles(files)
  }

  function onDragOver(e: DragEvent<HTMLDivElement>) {
    e.preventDefault()
    if (!isUploading) setDragOver(true)
  }

  function onDragLeave() {
    setDragOver(false)
  }

  function onInputChange(e: ChangeEvent<HTMLInputElement>) {
    const files = Array.from(e.target.files ?? [])
    if (files.length > 0) {
      void handleFiles(files)
    }
  }

  function onClick() {
    if (!isUploading) {
      inputRef.current?.click()
    }
  }

  const dropZoneStyle: React.CSSProperties = {
    border: `2px dashed ${dragOver ? '#0070f3' : '#ccc'}`,
    borderRadius: 8,
    padding: '40px 24px',
    textAlign: 'center',
    cursor: isUploading ? 'not-allowed' : 'pointer',
    backgroundColor: dragOver ? '#f0f7ff' : '#fafafa',
    transition: 'border-color 0.2s, background-color 0.2s',
    userSelect: 'none',
    marginBottom: 12,
    opacity: isUploading ? 0.6 : 1,
  }

  return (
    <div style={{ marginBottom: 24 }}>
      <div
        style={dropZoneStyle}
        onDrop={onDrop}
        onDragOver={onDragOver}
        onDragLeave={onDragLeave}
        onClick={onClick}
        role="button"
        tabIndex={0}
        aria-label="File upload drop zone"
        onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') onClick() }}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".csv,.xls,.xlsx"
          multiple
          style={{ display: 'none' }}
          onChange={onInputChange}
        />
        <p style={{ margin: 0, color: '#555', fontSize: 15 }}>
          {isUploading
            ? 'Uploading...'
            : 'Drop CSV or Excel files here, or click to browse'}
        </p>
        <p style={{ margin: '6px 0 0', color: '#999', fontSize: 12 }}>
          Supported formats: .csv, .xls, .xlsx
        </p>
      </div>
      {error && (
        <p style={{ color: '#d9534f', fontSize: 13, margin: '4px 0 0' }}>{error}</p>
      )}
    </div>
  )
}

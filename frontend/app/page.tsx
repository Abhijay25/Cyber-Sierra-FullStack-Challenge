'use client'

import { useState } from 'react'
import type { SheetMeta } from '@/lib/api'
import FileUpload from '@/components/FileUpload'
import SheetTabs from '@/components/SheetTabs'
import DataPreview from '@/components/DataPreview'
import QueryInterface from '@/components/QueryInterface'
import HistoryPanel from '@/components/HistoryPanel'

export default function Home() {
  const [sheets, setSheets] = useState<SheetMeta[]>([])
  const [activeSheet, setActiveSheet] = useState<string | null>(null)
  const [isUploading, setIsUploading] = useState(false)
  const [historyOpen, setHistoryOpen] = useState(false)
  const [reuseQuestion, setReuseQuestion] = useState('')
  const [previewN, setPreviewN] = useState(25)

  const handleUpload = (newSheets: SheetMeta[]) => {
    setSheets(prev => {
      const existing = new Map(prev.map(s => [s.name, s]))
      newSheets.forEach(s => existing.set(s.name, s))
      return Array.from(existing.values())
    })
    if (newSheets.length > 0 && !activeSheet) {
      setActiveSheet(newSheets[0].name)
    }
  }

  const hasFiles = sheets.length > 0

  return (
    <main style={{ maxWidth: 1600, margin: '0 auto', padding: '24px 24px' }}>
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        marginBottom: 24,
      }}>
        <h1 style={{ margin: 0, fontSize: 24, fontWeight: 600 }}>
          CSV / Excel Analyser
        </h1>
        {hasFiles && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 13, color: '#555' }}>
              Rows to analyse:
              <input
                type="number"
                min={1}
                max={500}
                value={previewN}
                onChange={(e) => setPreviewN(Math.min(500, Math.max(1, Number(e.target.value))))}
                style={{
                  width: 64,
                  padding: '4px 6px',
                  border: '1px solid #ccc',
                  borderRadius: 4,
                  fontSize: 13,
                }}
              />
            </label>
            <FileUpload
              onUpload={handleUpload}
              isUploading={isUploading}
              setIsUploading={setIsUploading}
              mode="button"
            />
          </div>
        )}
      </div>

      {!hasFiles && (
        <FileUpload
          onUpload={handleUpload}
          isUploading={isUploading}
          setIsUploading={setIsUploading}
        />
      )}

      {hasFiles && (
        <>
          <SheetTabs sheets={sheets} activeSheet={activeSheet} onSelect={setActiveSheet} />
          {activeSheet && <DataPreview sheetName={activeSheet} n={previewN} />}
          {activeSheet && (
            <QueryInterface
              sheetName={activeSheet}
              n={previewN}
              onHistoryOpen={() => setHistoryOpen(true)}
              initialQuestion={reuseQuestion}
            />
          )}
        </>
      )}

      <HistoryPanel
        isOpen={historyOpen}
        onClose={() => setHistoryOpen(false)}
        onReuse={(q) => {
          setReuseQuestion(q)
          setHistoryOpen(false)
        }}
      />
    </main>
  )
}

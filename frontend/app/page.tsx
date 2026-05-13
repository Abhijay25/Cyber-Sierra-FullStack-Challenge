'use client'

import { useState } from 'react'
import type { SheetMeta } from '@/lib/api'
import FileUpload from '@/components/FileUpload'
import SheetTabs from '@/components/SheetTabs'
import DataPreview from '@/components/DataPreview'

export default function Home() {
  const [sheets, setSheets] = useState<SheetMeta[]>([])
  const [activeSheet, setActiveSheet] = useState<string | null>(null)
  const [isUploading, setIsUploading] = useState(false)

  const handleUpload = (newSheets: SheetMeta[]) => {
    setSheets(prev => {
      // Merge: keep existing sheets, add/update new ones
      const existing = new Map(prev.map(s => [s.name, s]))
      newSheets.forEach(s => existing.set(s.name, s))
      return Array.from(existing.values())
    })
    if (newSheets.length > 0 && !activeSheet) {
      setActiveSheet(newSheets[0].name)
    }
  }

  return (
    <main style={{ maxWidth: 1200, margin: '0 auto', padding: '24px 16px' }}>
      <h1 style={{ marginBottom: 24, fontSize: 24, fontWeight: 600 }}>
        CSV / Excel Analyser
      </h1>
      <FileUpload onUpload={handleUpload} isUploading={isUploading} setIsUploading={setIsUploading} />
      {sheets.length > 0 && (
        <>
          <SheetTabs sheets={sheets} activeSheet={activeSheet} onSelect={setActiveSheet} />
          {activeSheet && <DataPreview sheetName={activeSheet} />}
        </>
      )}
    </main>
  )
}

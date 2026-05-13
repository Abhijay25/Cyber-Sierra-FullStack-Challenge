'use client'

import { useState } from 'react'
import type { SheetMeta } from '@/lib/api'

export default function Home() {
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const [sheets, setSheets] = useState<SheetMeta[]>([])
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const [activeSheet, setActiveSheet] = useState<string | null>(null)

  return (
    <main style={{ maxWidth: 1200, margin: '0 auto', padding: '24px 16px' }}>
      <h1 style={{ marginBottom: 24, fontSize: 24, fontWeight: 600 }}>
        CSV / Excel Analyser
      </h1>
      {/* Components will be added here in subsequent tasks */}
      <p style={{ color: '#6c757d' }}>Upload a file to begin.</p>
    </main>
  )
}

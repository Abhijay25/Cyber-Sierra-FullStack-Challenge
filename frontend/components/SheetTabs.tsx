'use client'

import type { SheetMeta } from '@/lib/api'

interface Props {
  sheets: SheetMeta[]
  activeSheet: string | null
  onSelect: (sheetName: string) => void
}

export default function SheetTabs({ sheets, activeSheet, onSelect }: Props) {
  if (sheets.length === 0) return null

  return (
    <div
      style={{
        display: 'flex',
        flexWrap: 'wrap',
        gap: 4,
        borderBottom: '2px solid #e0e0e0',
        marginBottom: 20,
        paddingBottom: 0,
      }}
      role="tablist"
    >
      {sheets.map((sheet) => {
        const isActive = sheet.name === activeSheet
        return (
          <button
            key={sheet.name}
            role="tab"
            aria-selected={isActive}
            onClick={() => onSelect(sheet.name)}
            style={{
              padding: '8px 16px',
              border: 'none',
              borderBottom: isActive ? '2px solid #0070f3' : '2px solid transparent',
              background: 'none',
              cursor: 'pointer',
              fontWeight: isActive ? 700 : 400,
              color: isActive ? '#0070f3' : '#444',
              fontSize: 14,
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'flex-start',
              lineHeight: 1.4,
              marginBottom: -2,
              transition: 'color 0.15s',
            }}
          >
            <span>{sheet.name}</span>
            <span style={{ fontSize: 11, color: '#999', fontWeight: 400 }}>
              {sheet.row_count.toLocaleString()} rows
            </span>
          </button>
        )
      })}
    </div>
  )
}

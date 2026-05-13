'use client'

import { useState, useEffect, useMemo } from 'react'
import {
  useReactTable,
  getCoreRowModel,
  flexRender,
  createColumnHelper,
} from '@tanstack/react-table'
import type { DataResponse } from '@/lib/api'
import { getData } from '@/lib/api'

interface Props {
  sheetName: string
}

const columnHelper = createColumnHelper<Record<string, unknown>>()

export default function DataPreview({ sheetName }: Props) {
  const [n] = useState(25)
  const [maximized, setMaximized] = useState(false)
  const [data, setData] = useState<DataResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)

    getData(sheetName, n)
      .then((result) => {
        if (!cancelled) setData(result)
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(err instanceof Error ? err.message : 'Failed to fetch data.')
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })

    return () => { cancelled = true }
  }, [sheetName, n])

  const columns = useMemo(() => {
    if (!data) return []
    return data.columns.map((col) =>
      columnHelper.accessor((row) => row[col], {
        id: col,
        header: col,
        cell: (info) => {
          const val = info.getValue()
          return val === null || val === undefined ? '' : String(val)
        },
      })
    )
  }, [data])

  const tableData = useMemo(() => data?.rows ?? [], [data])

  const table = useReactTable({
    data: tableData,
    columns,
    getCoreRowModel: getCoreRowModel(),
  })

  return (
    <div style={{ marginBottom: 32 }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 }}>
        <span style={{ fontSize: 13, color: '#666' }}>
          {loading ? 'Loading…' : data ? `${data.rows.length} rows` : ''}
        </span>
        {data && (
          <button
            onClick={() => setMaximized((m) => !m)}
            style={{
              padding: '4px 12px',
              fontSize: 12,
              border: '1px solid #ccc',
              borderRadius: 4,
              background: '#fff',
              cursor: 'pointer',
              color: '#444',
            }}
          >
            {maximized ? '⊟ Minimise' : '⊞ Maximise'}
          </button>
        )}
      </div>

      {error && !loading && (
        <p style={{ color: '#d9534f', fontSize: 14 }}>{error}</p>
      )}

      {!error && data && (
        <div
          style={{
            overflowX: 'auto',
            overflowY: 'auto',
            border: '1px solid #e0e0e0',
            borderRadius: 6,
            maxHeight: maximized ? 'none' : 300,
            transition: 'max-height 0.2s ease',
          }}
        >
          <table
            style={{
              borderCollapse: 'collapse',
              width: '100%',
              fontSize: 13,
              minWidth: 'max-content',
            }}
          >
            <thead style={{ position: 'sticky', top: 0, zIndex: 1 }}>
              {table.getHeaderGroups().map((headerGroup) => (
                <tr key={headerGroup.id} style={{ backgroundColor: '#f5f5f5' }}>
                  {headerGroup.headers.map((header) => (
                    <th
                      key={header.id}
                      style={{
                        padding: '8px 12px',
                        textAlign: 'left',
                        fontWeight: 600,
                        whiteSpace: 'nowrap',
                        borderBottom: '2px solid #ddd',
                        borderRight: '1px solid #e8e8e8',
                        color: '#333',
                        backgroundColor: '#f5f5f5',
                      }}
                    >
                      {header.isPlaceholder
                        ? null
                        : flexRender(header.column.columnDef.header, header.getContext())}
                    </th>
                  ))}
                </tr>
              ))}
            </thead>
            <tbody>
              {table.getRowModel().rows.map((row, rowIndex) => (
                <tr
                  key={row.id}
                  style={{ backgroundColor: rowIndex % 2 === 0 ? '#ffffff' : '#f9f9f9' }}
                >
                  {row.getVisibleCells().map((cell) => (
                    <td
                      key={cell.id}
                      style={{
                        padding: '6px 12px',
                        borderBottom: '1px solid #ebebeb',
                        borderRight: '1px solid #ebebeb',
                        whiteSpace: 'nowrap',
                        maxWidth: 220,
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        color: '#555',
                      }}
                    >
                      {flexRender(cell.column.columnDef.cell, cell.getContext())}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
          {table.getRowModel().rows.length === 0 && (
            <p style={{ padding: '16px', color: '#888', textAlign: 'center', margin: 0 }}>
              No data available.
            </p>
          )}
        </div>
      )}
    </div>
  )
}

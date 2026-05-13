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
  const [n, setN] = useState(10)
  const [data, setData] = useState<DataResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)

    getData(sheetName, n)
      .then((result) => {
        if (!cancelled) {
          setData(result)
        }
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Failed to fetch data.')
        }
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
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 16 }}>
        <label
          htmlFor="preview-n"
          style={{ fontSize: 14, color: '#444', fontWeight: 500 }}
        >
          Show top N rows:
        </label>
        <input
          id="preview-n"
          type="number"
          min={1}
          max={500}
          value={n}
          onChange={(e) => {
            const val = Math.min(500, Math.max(1, Number(e.target.value)))
            setN(val)
          }}
          style={{
            width: 80,
            padding: '4px 8px',
            border: '1px solid #ccc',
            borderRadius: 4,
            fontSize: 14,
          }}
        />
      </div>

      {loading && (
        <p style={{ color: '#888', fontSize: 14 }}>Loading...</p>
      )}

      {error && !loading && (
        <p style={{ color: '#d9534f', fontSize: 14 }}>{error}</p>
      )}

      {!loading && !error && data && (
        <div style={{ overflowX: 'auto', border: '1px solid #e0e0e0', borderRadius: 6 }}>
          <table
            style={{
              borderCollapse: 'collapse',
              width: '100%',
              fontSize: 13,
              minWidth: 'max-content',
            }}
          >
            <thead>
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
                  style={{
                    backgroundColor: rowIndex % 2 === 0 ? '#ffffff' : '#f9f9f9',
                  }}
                >
                  {row.getVisibleCells().map((cell) => (
                    <td
                      key={cell.id}
                      style={{
                        padding: '7px 12px',
                        borderBottom: '1px solid #ebebeb',
                        borderRight: '1px solid #ebebeb',
                        whiteSpace: 'nowrap',
                        maxWidth: 300,
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

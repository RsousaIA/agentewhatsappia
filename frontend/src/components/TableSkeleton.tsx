import React from 'react'

interface TableSkeletonProps {
  className?: string
  rows?: number
  columns?: number
  showHeader?: boolean
}

const TableSkeleton: React.FC<TableSkeletonProps> = ({
  className = '',
  rows = 5,
  columns = 4,
  showHeader = true
}) => {
  return (
    <div className={`overflow-hidden rounded-lg shadow-sm ${className}`}>
      <table className="min-w-full divide-y divide-gray-200">
        {showHeader && (
          <thead className="bg-gray-50">
            <tr>
              {Array.from({ length: columns }).map((_, index) => (
                <th
                  key={`header-${index}`}
                  className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
                >
                  <div className="h-4 bg-gray-200 rounded w-24 animate-pulse" />
                </th>
              ))}
            </tr>
          </thead>
        )}
        <tbody className="bg-white divide-y divide-gray-200">
          {Array.from({ length: rows }).map((_, rowIndex) => (
            <tr key={`row-${rowIndex}`}>
              {Array.from({ length: columns }).map((_, colIndex) => (
                <td
                  key={`cell-${rowIndex}-${colIndex}`}
                  className="px-6 py-4 whitespace-nowrap"
                >
                  <div className="h-4 bg-gray-200 rounded w-32 animate-pulse" />
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export default TableSkeleton 
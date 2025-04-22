import React from 'react'

interface ChartSkeletonProps {
  className?: string
  height?: number
}

const ChartSkeleton: React.FC<ChartSkeletonProps> = ({
  className = '',
  height = 300
}) => {
  return (
    <div className={`bg-white rounded-lg shadow-md p-6 ${className}`}>
      <div className="h-6 bg-gray-200 rounded w-1/3 mb-4 animate-pulse" />
      <div className="flex items-end space-x-2" style={{ height: `${height}px` }}>
        {Array.from({ length: 7 }).map((_, index) => (
          <div
            key={`bar-${index}`}
            className="flex-1 bg-gray-100 rounded-t animate-pulse"
            style={{
              height: `${Math.random() * 80 + 20}%`
            }}
          />
        ))}
      </div>
      <div className="mt-4 flex justify-between">
        {Array.from({ length: 7 }).map((_, index) => (
          <div
            key={`label-${index}`}
            className="h-4 bg-gray-200 rounded w-12 animate-pulse"
          />
        ))}
      </div>
    </div>
  )
}

export default ChartSkeleton 
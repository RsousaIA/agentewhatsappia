import React from 'react'

interface ListSkeletonProps {
  className?: string
  items?: number
  showAvatar?: boolean
}

const ListSkeleton: React.FC<ListSkeletonProps> = ({
  className = '',
  items = 5,
  showAvatar = true
}) => {
  return (
    <div className={`space-y-4 ${className}`}>
      {Array.from({ length: items }).map((_, index) => (
        <div
          key={`item-${index}`}
          className="bg-white rounded-lg shadow-sm p-4 animate-pulse"
        >
          <div className="flex items-center space-x-4">
            {showAvatar && (
              <div className="h-10 w-10 bg-gray-200 rounded-full" />
            )}
            <div className="flex-1 space-y-2">
              <div className="h-4 bg-gray-200 rounded w-3/4" />
              <div className="h-3 bg-gray-100 rounded w-1/2" />
            </div>
            <div className="h-4 bg-gray-200 rounded w-16" />
          </div>
        </div>
      ))}
    </div>
  )
}

export default ListSkeleton 
import React from 'react'

interface CardSkeletonProps {
  className?: string
  showHeader?: boolean
  showFooter?: boolean
  showImage?: boolean
}

const CardSkeleton: React.FC<CardSkeletonProps> = ({
  className = '',
  showHeader = true,
  showFooter = true,
  showImage = true
}) => {
  return (
    <div className={`bg-white rounded-lg shadow-sm overflow-hidden ${className}`}>
      {showHeader && (
        <div className="p-4 border-b">
          <div className="h-6 bg-gray-200 rounded w-1/4 animate-pulse" />
        </div>
      )}
      
      {showImage && (
        <div className="h-48 bg-gray-200 animate-pulse" />
      )}
      
      <div className="p-4">
        <div className="space-y-3">
          <div className="h-4 bg-gray-200 rounded w-3/4 animate-pulse" />
          <div className="h-4 bg-gray-200 rounded w-1/2 animate-pulse" />
          <div className="h-4 bg-gray-200 rounded w-2/3 animate-pulse" />
        </div>
      </div>
      
      {showFooter && (
        <div className="p-4 border-t">
          <div className="flex justify-between">
            <div className="h-4 bg-gray-200 rounded w-24 animate-pulse" />
            <div className="h-4 bg-gray-200 rounded w-24 animate-pulse" />
          </div>
        </div>
      )}
    </div>
  )
}

export default CardSkeleton 
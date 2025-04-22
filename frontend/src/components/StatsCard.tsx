import React from 'react';
import { 
  ChatBubbleLeftIcon, 
  ChatBubbleLeftRightIcon, 
  CheckCircleIcon, 
  ClockIcon, 
  StarIcon 
} from '@heroicons/react/24/outline';

interface StatsCardProps {
  title: string;
  value: string | number;
  icon: string;
  className?: string;
}

const StatsCard: React.FC<StatsCardProps> = ({ title, value, icon, className = '' }) => {
  const renderIcon = () => {
    switch (icon) {
      case 'chat':
        return <ChatBubbleLeftIcon className="h-6 w-6 text-blue-500" />;
      case 'active':
        return <ChatBubbleLeftRightIcon className="h-6 w-6 text-green-500" />;
      case 'closed':
        return <CheckCircleIcon className="h-6 w-6 text-orange-500" />;
      case 'star':
        return <StarIcon className="h-6 w-6 text-purple-500" />;
      default:
        return <ClockIcon className="h-6 w-6 text-gray-500" />;
    }
  };

  return (
    <div className={`bg-white rounded-lg shadow p-6 ${className}`}>
      <div className="flex items-center">
        <div className="p-3 rounded-full bg-opacity-10">
          {renderIcon()}
        </div>
        <div className="ml-4">
          <p className="text-sm font-medium text-gray-500">{title}</p>
          <p className="text-2xl font-semibold text-gray-900">{value}</p>
        </div>
      </div>
    </div>
  );
};

export default StatsCard; 
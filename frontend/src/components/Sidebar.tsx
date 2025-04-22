import { Link, useLocation } from 'react-router-dom'
import { 
  HomeIcon,
  ChatBubbleLeftRightIcon,
  ChartBarIcon,
  Cog6ToothIcon
} from '@heroicons/react/24/outline'

const Sidebar = () => {
  const location = useLocation()

  const menuItems = [
    { path: '/', label: 'Dashboard', icon: HomeIcon },
    { path: '/messages', label: 'Mensagens', icon: ChatBubbleLeftRightIcon },
    { path: '/reports', label: 'Relatórios', icon: ChartBarIcon },
    { path: '/settings', label: 'Configurações', icon: Cog6ToothIcon },
  ]

  return (
    <div className="w-64 bg-white shadow-sm">
      <div className="h-full px-3 py-4">
        <ul className="space-y-2">
          {menuItems.map((item) => {
            const Icon = item.icon
            return (
              <li key={item.path}>
                <Link
                  to={item.path}
                  className={`flex items-center p-2 text-base font-normal rounded-lg hover:bg-gray-100 ${
                    location.pathname === item.path
                      ? 'text-primary bg-gray-100'
                      : 'text-gray-700'
                  }`}
                >
                  <Icon className="h-5 w-5 mr-3" />
                  <span>{item.label}</span>
                </Link>
              </li>
            )
          })}
        </ul>
      </div>
    </div>
  )
}

export default Sidebar 
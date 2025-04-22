import { Outlet, Link, useLocation } from 'react-router-dom';
import { HomeIcon, ChatBubbleLeftRightIcon } from '@heroicons/react/24/outline';

const Layout = () => {
    const location = useLocation();

    return (
        <div className="min-h-screen bg-gray-100">
            {/* Header */}
            <header className="bg-white shadow-sm">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                    <div className="flex justify-between h-16">
                        <div className="flex">
                            <div className="flex-shrink-0 flex items-center">
                                <h1 className="text-xl font-bold text-blue-600">Suporte WhatsApp</h1>
                            </div>
                            <nav className="ml-6 flex space-x-4">
                                <Link
                                    to="/"
                                    className={`inline-flex items-center px-3 py-2 text-sm font-medium rounded-md ${
                                        location.pathname === '/'
                                            ? 'bg-blue-100 text-blue-900'
                                            : 'text-gray-600 hover:bg-gray-50'
                                    }`}
                                >
                                    <HomeIcon className="h-5 w-5 mr-2" />
                                    Dashboard
                                </Link>
                                <Link
                                    to="/mensagens"
                                    className={`inline-flex items-center px-3 py-2 text-sm font-medium rounded-md ${
                                        location.pathname === '/mensagens'
                                            ? 'bg-blue-100 text-blue-900'
                                            : 'text-gray-600 hover:bg-gray-50'
                                    }`}
                                >
                                    <ChatBubbleLeftRightIcon className="h-5 w-5 mr-2" />
                                    Mensagens
                                </Link>
                            </nav>
                        </div>
                    </div>
                </div>
            </header>

            {/* Main content */}
            <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
                <Outlet />
            </main>
        </div>
    );
};

export default Layout; 
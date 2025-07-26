import React, { useState, useEffect, lazy, Suspense } from 'react';
import { BrowserRouter as Router, Route, Routes, NavLink, useLocation } from 'react-router-dom';
import { HomeIcon, SparklesIcon, FolderIcon, Cog6ToothIcon, WrenchScrewdriverIcon, SunIcon, MoonIcon, PaintBrushIcon, Bars3Icon, XMarkIcon, DocumentTextIcon } from '@heroicons/react/24/outline';

// 懒加载页面组件，减少初始加载时间
const HomePage = lazy(() => import('./pages/HomePage'));
const HdReplacePage = lazy(() => import('./pages/HdReplacePage'));
const SettingsPage = lazy(() => import('./pages/SettingsPage'));
const FileManagerPage = lazy(() => import('./pages/FileManagerPage'));
const ManualProcessPage = lazy(() => import('./pages/ManualProcessPage'));
const HandmadeCorrectionPage = lazy(() => import('./pages/HandmadeCorrectionPage'));
const SystemLogsPage = lazy(() => import('./pages/SystemLogsPage'));

// 加载提示组件
const LoadingFallback = () => (
  <div className="flex items-center justify-center h-full">
    <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-[var(--color-primary-accent)]"></div>
  </div>
);

const navigation = [
  { name: '最新入库', href: '/', icon: HomeIcon },
  { name: '高清替换', href: '/hd-replace', icon: SparklesIcon },
  { name: '文件管理', href: '/file-manager', icon: FolderIcon },
  { name: '数据清洗', href: '/manual-process', icon: WrenchScrewdriverIcon },
  { name: '手作修正', href: '/handmade-correction', icon: PaintBrushIcon },
  { name: '系统日志', href: '/system-logs', icon: DocumentTextIcon },
  { name: '系统设置', href: '/settings', icon: Cog6ToothIcon },
];

// --- 侧边栏组件 ---
const Sidebar = React.memo(({ theme, toggleTheme }) => {
    return (
        <div className="w-64 bg-[var(--color-sidebar-bg)] flex flex-col h-full">
            <div className="h-16 flex items-center justify-center text-2xl font-bold text-[var(--color-primary-accent)] border-b border-[var(--color-border)] flex-shrink-0">
                Jassistant
            </div>
            <nav className="flex-1 px-4 py-6 space-y-2 overflow-y-auto">
                {navigation.map((item) => (
                    <NavLink
                        key={item.name}
                        to={item.href}
                        end={item.href === '/'}
                        className={({ isActive }) =>
                            `flex items-center px-4 py-2 text-lg rounded-md transition-colors duration-200 ${
                                isActive
                                ? 'bg-[var(--color-primary-accent)] text-white'
                                : 'text-[var(--color-secondary-text)] hover:bg-[var(--color-secondary-bg)] hover:text-[var(--color-primary-text)]'
                            }`
                        }
                    >
                        <item.icon className="h-6 w-6 mr-3" />
                        {item.name}
                    </NavLink>
                ))}
            </nav>
            <div className="p-4 border-t border-[var(--color-border)] flex-shrink-0">
                <button onClick={toggleTheme} className="w-full flex items-center justify-center gap-2 p-2 rounded-md text-[var(--color-secondary-text)] hover:bg-[var(--color-secondary-bg)] hover:text-[var(--color-primary-text)]">
                    {theme === 'dark' ? <SunIcon className="h-6 w-6"/> : <MoonIcon className="h-6 w-6"/>}
                    <span>切换{theme === 'dark' ? '白天' : '夜间'}模式</span>
                </button>
            </div>
        </div>
    );
});

// 用于在路由变化时（例如点击菜单项）自动关闭侧边栏
const SidebarCloser = ({ setSidebarOpen }) => {
    const location = useLocation();
    useEffect(() => {
        setSidebarOpen(false);
    }, [location, setSidebarOpen]);
    return null;
}

function App() {
  const [theme, setTheme] = useState(() => localStorage.getItem('theme') || 'dark');
  const [sidebarOpen, setSidebarOpen] = useState(false);

  // 使用useEffect设置主题，但优化为只在主题变化时才操作DOM
  useEffect(() => {
    const root = window.document.documentElement;
    if (theme === 'dark') {
      root.classList.add('dark');
    } else {
      root.classList.remove('dark');
    }
    localStorage.setItem('theme', theme);
  }, [theme]);

  const toggleTheme = () => {
    setTheme(prevTheme => prevTheme === 'dark' ? 'light' : 'dark');
  };

  // 防止不必要的重复渲染
  const handleSidebarToggle = () => setSidebarOpen(!sidebarOpen);
  const handleSidebarClose = () => setSidebarOpen(false);

  return (
    <Router>
      <SidebarCloser setSidebarOpen={setSidebarOpen} />
      <div className="flex h-screen bg-[var(--color-primary-bg)] text-[var(--color-primary-text)]">
        {/* --- 移动端侧边栏 (覆盖层) --- */}
        <div className={`fixed inset-y-0 left-0 z-40 md:hidden transition-transform duration-300 ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'}`}>
            <Sidebar theme={theme} toggleTheme={toggleTheme} />
        </div>
        {sidebarOpen && (
            <div className="fixed inset-0 bg-black/60 z-30 md:hidden" onClick={handleSidebarClose}></div>
        )}

        {/* --- 桌面端侧边栏 (固定) --- */}
        <div className="hidden md:flex md:flex-shrink-0">
            <Sidebar theme={theme} toggleTheme={toggleTheme} />
        </div>
        
        <div className="flex flex-col flex-1 w-0 overflow-hidden">
            {/* --- 移动端顶部栏 --- */}
            <div className="md:hidden relative z-10 flex-shrink-0 h-16 bg-[var(--color-sidebar-bg)] border-b border-[var(--color-border)] flex items-center justify-between px-4">
                <button onClick={handleSidebarToggle} className="text-[var(--color-primary-text)]">
                    <Bars3Icon className="h-6 w-6" />
                </button>
                <div className="text-lg font-bold text-[var(--color-primary-accent)]">Jassistant</div>
            </div>

            <main className="flex-1 relative overflow-y-auto focus:outline-none p-4 sm:p-6 lg:p-8">
                <Suspense fallback={<LoadingFallback />}>
                    <Routes>
                        <Route path="/" element={<HomePage />} />
                        <Route path="/hd-replace" element={<HdReplacePage />} />
                        <Route path="/file-manager" element={<FileManagerPage />} />
                        <Route path="/manual-process" element={<ManualProcessPage />} />
                        <Route path="/handmade-correction" element={<HandmadeCorrectionPage />} />
                        <Route path="/system-logs" element={<SystemLogsPage />} />
                        <Route path="/settings" element={<SettingsPage />} />
                    </Routes>
                </Suspense>
            </main>
        </div>
      </div>
    </Router>
  );
}

export default App;

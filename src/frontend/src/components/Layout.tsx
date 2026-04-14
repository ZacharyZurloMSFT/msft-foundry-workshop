interface LayoutProps {
  children: React.ReactNode;
}

export default function Layout({ children }: LayoutProps): React.ReactElement {
  return (
    <div className="flex h-screen bg-gray-50">
      {/* Sidebar — conversation list placeholder */}
      <aside className="hidden w-64 flex-shrink-0 border-r border-gray-200 bg-white md:block">
        <div className="p-4">
          <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wider">
            Conversations
          </h2>
          <p className="mt-2 text-sm text-gray-400">No conversations yet</p>
        </div>
      </aside>

      {/* Main area */}
      <div className="flex flex-1 flex-col">
        <header className="flex h-14 items-center border-b border-gray-200 bg-white px-6 shadow-sm">
          <h1 className="text-lg font-bold text-gray-900">
            AI Foundry Workshop
          </h1>
        </header>
        <main className="flex-1 overflow-hidden">{children}</main>
      </div>
    </div>
  );
}

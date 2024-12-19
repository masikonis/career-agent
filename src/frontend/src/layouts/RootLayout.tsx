import React from 'react'
import { ThemeProvider } from '../components/theme-provider'

interface RootLayoutProps {
  children: React.ReactNode
}

export function RootLayout({ children }: RootLayoutProps) {
  return (
    <ThemeProvider defaultTheme="system" storageKey="ui-theme">
      <div className="min-h-screen bg-background dark:bg-background">
        <header className="border-b">
          <div className="container flex h-16 items-center px-4">
            <h1 className="text-2xl font-bold">Career Crew</h1>
          </div>
        </header>
        <main className="container px-4 py-6">
          {children}
        </main>
      </div>
    </ThemeProvider>
  )
}
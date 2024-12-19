import React from 'react'
import { Button } from './components/ui/button'
import { RootLayout } from './layouts/RootLayout'
import { ThemeToggle } from './components/theme-toggle'

export default function App() {
  return (
    <RootLayout>
      <div className="space-y-8">
        <div className="flex justify-between items-center">
          <h2 className="text-3xl font-bold tracking-tight">Dashboard</h2>
          <ThemeToggle />
        </div>
        <div className="space-x-4">
          <Button>Default Button</Button>
          <Button variant="destructive">Destructive Button</Button>
          <Button variant="outline">Outline Button</Button>
          <Button variant="secondary">Secondary Button</Button>
          <Button variant="ghost">Ghost Button</Button>
          <Button variant="link">Link Button</Button>
        </div>
      </div>
    </RootLayout>
  )
}

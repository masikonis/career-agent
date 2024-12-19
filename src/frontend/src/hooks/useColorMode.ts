import { useEffect, useState } from 'react';

type ColorMode = 'light' | 'dark' | 'system';

export function useColorMode() {
  const [mode, setMode] = useState<ColorMode>(() => {
    // Check localStorage first
    const savedMode = localStorage.getItem('color-mode') as ColorMode;
    if (savedMode) return savedMode;
    
    // Check system preference
    if (window.matchMedia('(prefers-color-scheme: dark)').matches) {
      return 'dark';
    }
    return 'light';
  });

  useEffect(() => {
    localStorage.setItem('color-mode', mode);
    
    // Handle system preference changes
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
    const handleChange = () => {
      if (mode === 'system') {
        setMode(mediaQuery.matches ? 'dark' : 'light');
      }
    };

    mediaQuery.addEventListener('change', handleChange);
    return () => mediaQuery.removeEventListener('change', handleChange);
  }, [mode]);

  const toggleColorMode = (newMode: ColorMode) => {
    setMode(newMode);
  };

  // Calculate actual mode based on system preference
  const actualMode = mode === 'system' 
    ? window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
    : mode;

  return { mode: actualMode, toggleColorMode };
}

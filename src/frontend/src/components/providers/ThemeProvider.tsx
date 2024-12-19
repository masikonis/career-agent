import React from 'react';
import { ThemeProvider as MuiThemeProvider } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import { ThemeContextProvider, useTheme } from '../../theme/context';
import { getTheme } from '../../theme/theme';

function ThemeContent({ children }: { children: React.ReactNode }) {
  const { mode } = useTheme();
  const theme = getTheme(mode);

  return (
    <MuiThemeProvider theme={theme}>
      <CssBaseline />
      {children}
    </MuiThemeProvider>
  );
}

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  return (
    <ThemeContextProvider>
      <ThemeContent>{children}</ThemeContent>
    </ThemeContextProvider>
  );
}

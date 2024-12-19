import { createTheme, ThemeOptions } from '@mui/material/styles';
import { ColorMode } from './types';

const baseTheme: ThemeOptions = {
  typography: {
    fontFamily: '"Inter", "system-ui", -apple-system, sans-serif',
    h1: {
      fontSize: '2rem',
      fontWeight: 700,
    },
    h2: {
      fontSize: '1.5rem',
      fontWeight: 600,
    },
    button: {
      textTransform: 'none',
      fontWeight: 500,
    },
  },
  shape: {
    borderRadius: 8,
  },
  components: {
    MuiButton: {
      styleOverrides: {
        root: {
          fontWeight: 500,
        },
      },
      defaultProps: {
        disableElevation: true,
      },
    },
    MuiAppBar: {
      defaultProps: {
        elevation: 0,
      },
      styleOverrides: {
        root: {
          borderBottom: '1px solid',
        },
      },
    },
  },
};

const themes: Record<ColorMode, ThemeOptions> = {
  light: {
    ...baseTheme,
    palette: {
      mode: 'light',
      primary: {
        main: '#2C8EBB',
        light: '#5BBED8',
        dark: '#006090',
        contrastText: '#ffffff',
      },
      background: {
        default: '#ffffff',
        paper: '#f8f9fa',
      },
      divider: 'rgba(0, 0, 0, 0.12)',
    },
  },
  dark: {
    ...baseTheme,
    palette: {
      mode: 'dark',
      primary: {
        main: '#5BBED8',
        light: '#8EF1FF',
        dark: '#2C8EBB',
        contrastText: '#000000',
      },
      background: {
        default: '#121212',
        paper: '#1e1e1e',
      },
      divider: 'rgba(255, 255, 255, 0.12)',
    },
  },
};

export const getTheme = (mode: ColorMode) => createTheme(themes[mode]);

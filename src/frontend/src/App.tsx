import React from 'react';
import { Button, Stack, Typography } from '@mui/material';
import { Layout } from './components/Layout';

export default function App() {
  return (
    <Layout>
      <Stack spacing={4}>
        <Typography variant="h4" component="h2">
          Dashboard
        </Typography>
        <Stack direction="row" spacing={2}>
          <Button variant="contained">Primary Button</Button>
          <Button variant="outlined">Secondary Button</Button>
          <Button variant="text">Text Button</Button>
        </Stack>
      </Stack>
    </Layout>
  );
}

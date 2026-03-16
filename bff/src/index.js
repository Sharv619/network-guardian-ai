const express = require('express');
const cors = require('cors');
const { createProxyMiddleware } = require('http-proxy-middleware');
const WebSocket = require('ws');

const app = express();
const PORT = process.env.PORT || 8080;

// CORS configuration
app.use(cors({
  origin: '*',
  methods: ['GET', 'POST', 'PUT', 'DELETE'],
  allowedHeaders: ['Content-Type', 'Authorization']
}));

// Parse JSON
app.use(express.json());

// Health check
app.get('/health', (req, res) => {
  res.json({ status: 'healthy', service: 'bff' });
});

// API Proxy to Backend
app.use('/api', createProxyMiddleware({
  target: process.env.BACKEND_URL || 'http://localhost:8000',
  changeOrigin: true,
  pathRewrite: {
    '^/api': '',
  },
}));

// WebSocket Proxy
const backendWsUrl = process.env.BACKEND_WS_URL || 'ws://localhost:8000';

app.get('/ws', (req, res) => {
  // Redirect to backend WebSocket
  res.redirect(301, `${backendWsUrl}/ws/public`);
});

// Stats proxy endpoint
app.get('/stats', async (req, res) => {
  try {
    const response = await fetch(`${process.env.BACKEND_URL || 'http://localhost:8000'}/api/stats/ml/dashboard`);
    const data = await response.json();
    res.json(data);
  } catch (error) {
    res.status(500).json({ error: 'Failed to fetch stats' });
  }
});

// Test report proxy
app.get('/test-report', async (req, res) => {
  try {
    const response = await fetch(`${process.env.BACKEND_URL || 'http://localhost:8000'}/api/test-report`);
    const data = await response.json();
    res.json(data);
  } catch (error) {
    res.status(500).json({ error: 'Failed to fetch test report' });
  }
});

// Start server
app.listen(PORT, () => {
  console.log(`🚀 BFF Server running on port ${PORT}`);
  console.log(`📡 Proxying to backend: ${process.env.BACKEND_URL || 'http://localhost:8000'}`);
});

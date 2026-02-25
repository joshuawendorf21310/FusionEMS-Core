import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { VitePWA } from 'vite-plugin-pwa'

export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: 'autoUpdate',
      includeAssets: ['favicon.svg'],
      manifest: {
        name: 'FusionEMS Quantum',
        short_name: 'FusionEMS',
        start_url: '/',
        display: 'standalone',
        background_color: '#0b0d10',
        theme_color: '#0b0d10',
        icons: [
          { src: '/favicon.svg', sizes: '192x192', type: 'image/svg+xml' }
        ]
      },
      workbox: {
        runtimeCaching: [
          {
            urlPattern: ({ url }) => url.pathname.startsWith('/api/'),
            handler: 'NetworkFirst',
            options: {
              cacheName: 'api-cache',
              expiration: { maxEntries: 200, maxAgeSeconds: 3600 }
            }
          }
        ]
      }
    })
  ],
  server: { port: 3000 }
})

import type { NextConfig } from 'next';

const nextConfig: NextConfig = {
  /* config options here */
  serverExternalPackages: ['livekit-server-sdk'],
  webpack: (config, { isServer }) => {
    // Handle WebRTC and media stream dependencies
    if (!isServer) {
      config.resolve.fallback = {
        ...config.resolve.fallback,
        fs: false,
        net: false,
        tls: false,
      };
    }
    return config;
  },
  // Turbopack configuration
  turbopack: {
    // Enable experimental features
    resolveAlias: {
      // Add any path aliases here if needed
    },
  },
  // Enable source maps for better error debugging
  productionBrowserSourceMaps: process.env.NODE_ENV === 'development',
};

export default nextConfig;

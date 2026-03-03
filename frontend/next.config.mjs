/** @type {import('next').NextConfig} */

const API_BASE = process.env.NEXT_PUBLIC_API_BASE;

// NOTE:
// - In AWS, the ALB/CloudFront path rules route /api/* directly to the backend.
// - In local/docker, we often use http://localhost:8000.
// So we treat NEXT_PUBLIC_API_BASE as optional and only enforce HTTPS for non-local hosts.
const _isLocalHost = (hostname) =>
  hostname === "localhost" ||
  hostname === "127.0.0.1" ||
  hostname === "::1" ||
  hostname === "backend";

const nextConfig = {
  output: "standalone",
  reactStrictMode: true,
  poweredByHeader: false,
  compress: true,

  eslint: {
    ignoreDuringBuilds: false,
  },

  typescript: {
    ignoreBuildErrors: false,
  },

  images: {
    formats: ["image/avif", "image/webp"],
    minimumCacheTTL: 60,
    remotePatterns: API_BASE
      ? [
          {
            protocol: new URL(API_BASE).protocol.replace(":", ""),
            hostname: new URL(API_BASE).hostname,
          },
        ]
      : [],
  },

  async rewrites() {
    if (!API_BASE) return [];

    const parsed = new URL(API_BASE);

    if (process.env.NODE_ENV === "production" && parsed.protocol !== "https:" && !_isLocalHost(parsed.hostname)) {
      throw new Error(
        `NEXT_PUBLIC_API_BASE must use HTTPS for non-local hosts (got ${API_BASE}).`
      );
    }

    return [
      {
        source: "/api/:path*",
        destination: `${API_BASE}/api/:path*`,
      },
      {
        source: "/track/:path*",
        destination: `${API_BASE}/track/:path*`,
      },
    ];
  },

  async headers() {
    return [
      {
        source: "/(.*)",
        headers: [
          { key: "X-Frame-Options", value: "DENY" },
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          {
            key: "Permissions-Policy",
            value:
              "camera=(), microphone=(), geolocation=(), interest-cohort=()",
          },
        ],
      },
    ];
  },
};

export default nextConfig;

/** @type {import('next').NextConfig} */

const API_BASE = process.env.NEXT_PUBLIC_API_BASE;

if (!API_BASE && process.env.NODE_ENV === "production") {
  throw new Error("NEXT_PUBLIC_API_BASE must be defined in production");
}

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
            protocol: "https",
            hostname: new URL(API_BASE).hostname,
          },
        ]
      : [],
  },

  async rewrites() {
    if (!API_BASE) return [];

    const parsed = new URL(API_BASE);

    if (parsed.protocol !== "https:") {
      throw new Error("NEXT_PUBLIC_API_BASE must use HTTPS");
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

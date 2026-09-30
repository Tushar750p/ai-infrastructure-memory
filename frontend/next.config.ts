import type { NextConfig } from "next";

const backendUrl = process.env.AIME_BACKEND_URL;

const nextConfig: NextConfig = {
  output: "standalone",
  async rewrites() {
    if (!backendUrl) return [];
    return [
      {
        source: "/api/:path*",
        destination: `${backendUrl.replace(/\/$/, "")}/api/:path*`,
      },
      {
        source: "/health/:path*",
        destination: `${backendUrl.replace(/\/$/, "")}/health/:path*`,
      },
    ];
  },
};

export default nextConfig;

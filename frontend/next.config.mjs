/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  async rewrites() {
    const raw =
      process.env.INTERNAL_API_URL ||
      process.env.NEXT_PUBLIC_API_URL ||
      "http://localhost:8000";
    const api = raw.replace(/\/+$/, "");
    if (!/^https?:\/\//i.test(api)) {
      throw new Error(
        `INTERNAL_API_URL/NEXT_PUBLIC_API_URL must start with http:// or https:// (got: ${raw})`
      );
    }
    return [
      { source: "/api/backend/:path*", destination: `${api}/api/v1/:path*` },
      { source: "/api/backend-root/:path*", destination: `${api}/:path*` },
    ];
  },
};

export default nextConfig;

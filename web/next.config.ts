import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /* config options here */
  cacheComponents: true,
  // phone mode (scripts/phone_mode.sh) sets LAN_HOST to this Mac's Wi-Fi address
  allowedDevOrigins: process.env.LAN_HOST ? [process.env.LAN_HOST] : [],
  async redirects() {
    return [{ source: "/", destination: "/ko", permanent: false }];
  },
  partialPrefetching: true,
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};

export default nextConfig;

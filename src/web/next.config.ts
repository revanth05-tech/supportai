import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  turbopack: {
    // Keep discovery inside this standalone frontend rather than walking to
    // an unrelated lockfile in the user profile's parent directory.
    root: process.cwd(),
  },
};

export default nextConfig;

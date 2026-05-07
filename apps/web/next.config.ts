import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Standalone output is required for the Docker production image.
  // Disabled locally on Windows where unprivileged symlink creation fails.
  output: process.env.NEXT_STANDALONE === "1" ? "standalone" : undefined,
};

export default nextConfig;

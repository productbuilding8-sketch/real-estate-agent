import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  // typedRoutes requires all Link hrefs to be statically known — re-enable when
  // the route set is stable.
};

export default nextConfig;

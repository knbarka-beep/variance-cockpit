import type { NextConfig } from "next";

// Static site: all data is read at build time, no server and no live AI.
const nextConfig: NextConfig = {
  output: "export",
  trailingSlash: true, // /method/ is written as method/index.html, so any static server finds it
};

export default nextConfig;

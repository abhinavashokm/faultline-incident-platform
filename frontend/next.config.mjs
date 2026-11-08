/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  async redirects() {
    return [
      {
        source: "/onboarding/create-project",
        destination: "/login",
        permanent: false,
      },
      {
        source: "/onboarding/install-sdk",
        destination: "/login",
        permanent: false,
      },
    ];
  },
};

export default nextConfig;

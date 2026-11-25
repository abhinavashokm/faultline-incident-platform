import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import "./globals.css";
import { QueryProvider } from "@/lib/query-provider";
import { AuthProvider } from "@/features/auth/auth-context";
import { GlobalLoadingProvider } from "@/components/layout/global-loading-provider";
import { Toaster } from "@/components/ui/toaster";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-sans",
  display: "swap",
});

const jetBrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Faultline",
  description: "Error tracking and incident response platform",
  icons: {
    icon: "/icon.png",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={`${inter.variable} ${jetBrainsMono.variable}`}>
      <body className="min-h-screen bg-canvas font-sans text-text-primary antialiased">
        <QueryProvider>
          <AuthProvider>
            <GlobalLoadingProvider>
              {children}
              <Toaster />
            </GlobalLoadingProvider>
          </AuthProvider>
        </QueryProvider>
      </body>
    </html>
  );
}

import type { Metadata } from "next";
import { Rubik, Roboto_Mono } from "next/font/google";
import "./globals.css";
import { QueryProvider } from "@/lib/query-provider";
import { AuthProvider } from "@/features/auth/auth-context";
import { GlobalLoadingProvider } from "@/components/layout/global-loading-provider";
import { Toaster } from "@/components/ui/toaster";

const rubik = Rubik({
  subsets: ["latin"],
  variable: "--font-sans",
  display: "swap",
});

const robotoMono = Roboto_Mono({
  subsets: ["latin"],
  variable: "--font-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Faultline",
  description: "Error tracking and incident response platform",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={`${rubik.variable} ${robotoMono.variable}`}>
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

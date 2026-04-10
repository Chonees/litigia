import type { Metadata } from "next";
import { Newsreader, Inter } from "next/font/google";
import { AuthProvider } from "@/lib/auth";
import { AppShell } from "@/components/app-shell";
import "./globals.css";

const newsreader = Newsreader({
  subsets: ["latin"],
  variable: "--font-newsreader",
  display: "swap",
});

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

export const metadata: Metadata = {
  title: "LITIGIA — Institutional Grade Legal Tech",
  description: "Jurisprudencia, escritos y analisis para abogados argentinos",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="es" className={`${newsreader.variable} ${inter.variable}`}>
      <body className="min-h-screen flex flex-col">
        <AuthProvider>
          <AppShell>{children}</AppShell>
        </AuthProvider>
      </body>
    </html>
  );
}

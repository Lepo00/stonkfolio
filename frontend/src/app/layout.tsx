import type { Metadata } from "next";
import "./globals.css";
import { Providers } from "@/lib/providers";

export const metadata: Metadata = {
  title: "Stonkfolio",
  description: "Portfolio tracker for your investments",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="antialiased">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
import type { Metadata } from "next";

import "./globals.css";

export const metadata: Metadata = {
  title: "BitonX Quant",
  description: "AI-powered construction quantity takeoff platform.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}


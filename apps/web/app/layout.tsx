import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Geopolitical State Engine",
  description: "Real-time geopolitical sensing and scenario engine"
};

export default function RootLayout({
  children
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}


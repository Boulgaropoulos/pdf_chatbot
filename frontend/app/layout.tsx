import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "PDF QA",
  description: "Ask grounded questions about uploaded PDF documents",
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


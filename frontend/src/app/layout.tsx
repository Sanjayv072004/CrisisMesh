import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "CrisisMesh | Autonomous Emergency Coordination Command Centre",
  description: "Bengaluru Multi-Agent Emergency Command and Resource Coordination Centre",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body className="bg-ops-bg text-ops-text antialiased selection:bg-ops-cyan selection:text-black">
        {children}
      </body>
    </html>
  );
}

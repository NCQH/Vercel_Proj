import type { Metadata } from "next";
import "./globals.css";
import { Providers } from "../components/providers";

export const metadata: Metadata = {
  title: "AI Teaching Assistant",
  description:
    "Student and lecturer interface for personalized review and Q&A.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}

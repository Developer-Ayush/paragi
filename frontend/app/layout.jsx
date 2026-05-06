import "./globals.css";
import { Space_Grotesk, IBM_Plex_Mono } from "next/font/google";

const display = Space_Grotesk({ subsets: ["latin"], variable: "--font-display" });
const mono = IBM_Plex_Mono({ subsets: ["latin"], weight: ["400", "500"], variable: "--font-mono" });

export const metadata = {
  title: "Paragi Studio",
  description: "Local AI chat with personal and main memory graphs",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body className={`${display.variable} ${mono.variable}`}>{children}</body>
    </html>
  );
}

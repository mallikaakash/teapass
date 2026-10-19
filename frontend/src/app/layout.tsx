import type { Metadata } from "next";
import { Fraunces, Libre_Baskerville, Literata, Newsreader, Source_Sans_3 } from "next/font/google";
import "./globals.css";

const fraunces = Fraunces({ subsets: ["latin"], variable: "--font-fraunces" });
const literata = Literata({ subsets: ["latin"], variable: "--font-literata" });
const newsreader = Newsreader({ subsets: ["latin"], variable: "--font-newsreader" });
const libre = Libre_Baskerville({ subsets: ["latin"], weight: ["400", "700"], variable: "--font-libre" });
const source = Source_Sans_3({ subsets: ["latin"], variable: "--font-source" });

export const metadata: Metadata = {
  title: "TeaPass",
  description: "Every cup has a story. Now it has proof.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="en"
      className={`${fraunces.variable} ${literata.variable} ${newsreader.variable} ${libre.variable} ${source.variable} h-full antialiased`}
    >
      <body className="min-h-full">{children}</body>
    </html>
  );
}

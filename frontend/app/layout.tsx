import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'Agent Airlock — Security Console',
  description: 'The security checkpoint between AI agents and the outside world. Replay attacks and inspect real Clocked enforcement decisions.',
  icons: { icon: '/icon.svg' },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>;
}

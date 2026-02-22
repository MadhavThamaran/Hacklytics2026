import './globals.css'

export const metadata = {
  title: 'Gaitkeepr',
  description: 'An AI-powered running form coach to help you go the extra mile',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        {children}
      </body>
    </html>
  )
}

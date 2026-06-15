import { LazyMotion, domAnimation, m } from 'framer-motion'

export function LoadingScreen() {
  return (
    <LazyMotion features={domAnimation}>
      <div className="flex min-h-screen items-center justify-center bg-[#0B132B]">
        <m.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="text-center"
        >
          <div className="logo-container pulse-glow mx-auto mb-4">
            <img src="/logo.png" alt="HAW Logo" className="h-12 w-auto" />
          </div>
          <div className="inline-block size-8 animate-spin rounded-full border-4 border-solid border-[#00FF73] border-r-transparent"></div>
          <p className="mt-4 text-[#B0B3C5]">Cargando…</p>
        </m.div>
      </div>
    </LazyMotion>
  )
}

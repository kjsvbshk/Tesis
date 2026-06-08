import { useToast } from "@/hooks/use-toast"
import {
  Toast,
  ToastClose,
  ToastDescription,
  ToastProvider,
  ToastTitle,
  ToastViewport,
} from "@/components/ui/toast"
import { useEffect } from "react"

export function Toaster() {
  const { toasts } = useToast()

  useEffect(() => {
    // Eliminar atributos del wrapper div sin mover nodos (para evitar conflictos con React)
    const removeWrapperAttributes = () => {
      // Buscar el ol del viewport primero
      const viewport = document.querySelector('ol[class*="fixed top-4 right-4"]')
      if (!viewport) return

      // Buscar el div padre que tiene pointer-events: none
      let parent = viewport.parentElement
      while (parent && parent !== document.body) {
        if (parent.tagName === 'DIV') {
          // Eliminar atributos problemáticos sin mover el nodo
          parent.removeAttribute('role')
          parent.removeAttribute('aria-label')
          parent.removeAttribute('tabindex')
          // Aplicar estilos inline para que no afecte el layout
          if (parent.getAttribute('style')?.includes('pointer-events: none')) {
            parent.setAttribute('style', 'display: contents !important; pointer-events: none !important;')
          }
        }
        parent = parent.parentElement
      }
    }

    // Ejecutar después de que React termine de renderizar
    const timeout = setTimeout(removeWrapperAttributes, 0)
    const timeout2 = setTimeout(removeWrapperAttributes, 100)

    return () => {
      clearTimeout(timeout)
      clearTimeout(timeout2)
    }
  }, [toasts])

  return (
    <ToastProvider swipeDirection="right">
      {toasts.map(function ({ id, title, description, action, ...props }) {
        return (
          <Toast key={id} {...props}>
            <div className="grid gap-1">
              {title && <ToastTitle>{title}</ToastTitle>}
              {description && (
                <ToastDescription>{description}</ToastDescription>
              )}
            </div>
            {action}
            <ToastClose />
          </Toast>
        )
      })}
      <ToastViewport />
    </ToastProvider>
  )
}

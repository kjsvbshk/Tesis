import * as React from "react"
import * as ToastPrimitives from "@radix-ui/react-toast"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "@/lib/utils"
import { X } from "lucide-react"

const ToastProvider = ToastPrimitives.Provider

const ToastViewport = ({
  className,
  ref,
  ...props
}: React.ComponentPropsWithoutRef<typeof ToastPrimitives.Viewport> & { ref?: React.Ref<React.ElementRef<typeof ToastPrimitives.Viewport>> }) => (
  <ToastPrimitives.Viewport
    ref={ref}
    className={cn(
      "fixed top-4 right-4 z-[100] flex max-h-screen w-full flex-col gap-2 p-0 sm:max-w-[420px]",
      className
    )}
    {...props}
  />
)
ToastViewport.displayName = ToastPrimitives.Viewport.displayName

const toastVariants = cva(
  "group pointer-events-auto relative flex w-full items-start gap-3 overflow-hidden rounded-sm border p-4 shadow-lg transition-all data-[swipe=cancel]:translate-x-0 data-[swipe=end]:translate-x-[var(--radix-toast-swipe-end-x)] data-[swipe=move]:translate-x-[var(--radix-toast-swipe-move-x)] data-[swipe=move]:transition-none data-[state=open]:animate-in data-[state=closed]:animate-out data-[swipe=end]:animate-out data-[state=closed]:fade-out-80 data-[state=closed]:slide-out-to-right-full data-[state=open]:slide-in-from-right-full",
  {
    variants: {
      variant: {
        default: "border-white/10 bg-metal-900 text-white shadow-[0_0_20px_rgba(0,0,0,0.5)]",
        destructive:
          "destructive group border-red-500/50 bg-metal-900 text-white shadow-[0_0_20px_rgba(255,51,51,0.2)]",
        success:
          "border-acid-500/50 bg-metal-900 text-white shadow-[0_0_20px_rgba(204,255,0,0.15)]",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
)

const Toast = ({
  className,
  variant,
  ref,
  ...props
}: React.ComponentPropsWithoutRef<typeof ToastPrimitives.Root> &
  VariantProps<typeof toastVariants> & { ref?: React.Ref<React.ElementRef<typeof ToastPrimitives.Root>> }) => {
  return (
    <ToastPrimitives.Root
      ref={ref}
      className={cn(toastVariants({ variant }), className)}
      {...props}
    />
  )
}
Toast.displayName = ToastPrimitives.Root.displayName

const ToastAction = ({
  className,
  ref,
  ...props
}: React.ComponentPropsWithoutRef<typeof ToastPrimitives.Action> & { ref?: React.Ref<React.ElementRef<typeof ToastPrimitives.Action>> }) => (
  <ToastPrimitives.Action
    ref={ref}
    className={cn(
      "inline-flex h-8 shrink-0 items-center justify-center rounded-sm border border-white/10 bg-transparent px-3 text-xs font-mono font-medium transition-colors hover:bg-white/10 focus:outline-none focus:ring-1 focus:ring-acid-500 disabled:pointer-events-none disabled:opacity-50 group-[.destructive]:border-red-500/30 group-[.destructive]:hover:border-red-500/50 group-[.destructive]:hover:bg-red-500/10 group-[.destructive]:focus:ring-red-500 group-[.success]:border-acid-500/30 group-[.success]:hover:border-acid-500/50 group-[.success]:hover:bg-acid-500/10",
      className
    )}
    {...props}
  />
)
ToastAction.displayName = ToastPrimitives.Action.displayName

const ToastClose = ({
  className,
  ref,
  ...props
}: React.ComponentPropsWithoutRef<typeof ToastPrimitives.Close> & { ref?: React.Ref<React.ElementRef<typeof ToastPrimitives.Close>> }) => (
  <ToastPrimitives.Close
    ref={ref}
    className={cn(
      "absolute right-2 top-2 rounded-md p-1 text-muted-foreground opacity-0 transition-opacity hover:text-white focus:opacity-100 focus:outline-none focus:ring-1 group-hover:opacity-100 group-[.destructive]:text-red-500 group-[.destructive]:hover:text-red-400 group-[.destructive]:focus:ring-red-400 group-[.success]:text-acid-500 group-[.success]:hover:text-acid-400",
      className
    )}
    toast-close=""
    {...props}
  >
    <X className="size-4" />
  </ToastPrimitives.Close>
)
ToastClose.displayName = ToastPrimitives.Close.displayName

const ToastTitle = ({
  className,
  ref,
  ...props
}: React.ComponentPropsWithoutRef<typeof ToastPrimitives.Title> & { ref?: React.Ref<React.ElementRef<typeof ToastPrimitives.Title>> }) => (
  <ToastPrimitives.Title
    ref={ref}
    className={cn("text-sm font-display font-bold uppercase tracking-wide", className)}
    {...props}
  />
)
ToastTitle.displayName = ToastPrimitives.Title.displayName

const ToastDescription = ({
  className,
  ref,
  ...props
}: React.ComponentPropsWithoutRef<typeof ToastPrimitives.Description> & { ref?: React.Ref<React.ElementRef<typeof ToastPrimitives.Description>> }) => (
  <ToastPrimitives.Description
    ref={ref}
    className={cn("text-xs font-mono text-muted-foreground", className)}
    {...props}
  />
)
ToastDescription.displayName = ToastPrimitives.Description.displayName

type ToastProps = React.ComponentPropsWithoutRef<typeof Toast>

type ToastActionElement = React.ReactElement<typeof ToastAction>

export {
  type ToastProps,
  type ToastActionElement,
  ToastProvider,
  ToastViewport,
  Toast,
  ToastTitle,
  ToastDescription,
  ToastClose,
  ToastAction,
}

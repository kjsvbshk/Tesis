import * as React from "react"
import { Slot } from "@radix-ui/react-slot"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap text-sm font-medium transition-all focus-visible:outline-none disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0 relative overflow-hidden group font-display tracking-wider uppercase",
  {
    variants: {
      variant: {
        default:
          "bg-acid-500 text-metal-900 cut-corners hover:shadow-[0_0_20px_rgba(204,255,0,0.6)] hover:translate-y-[-2px] active:translate-y-[0px] font-bold border border-transparent",
        destructive:
          "bg-alert-red text-white cut-corners hover:bg-red-600 shadow-sm",
        outline:
          "border border-acid-500/50 bg-transparent text-acid-500 hover:bg-acid-500/10 hover:border-acid-500 cut-corners",
        secondary:
          "bg-metal-500 text-foreground border border-chrome-grey hover:bg-metal-500/80 hover:border-acid-500/30 cut-corners",
        ghost: "hover:bg-acid-500/10 hover:text-acid-500 text-muted-foreground",
        link: "text-acid-500 underline-offset-4 hover:underline",
        neon: "bg-transparent border border-violet-500 text-violet-500 shadow-[0_0_10px_rgba(179,102,255,0.3)] hover:bg-violet-500 hover:text-white hover:shadow-[0_0_20px_rgba(179,102,255,0.6)] cut-corners transition-all duration-300"
      },
      size: {
        default: "h-10 px-6 py-2",
        sm: "h-8 px-4 text-xs",
        lg: "h-12 px-10 text-base",
        icon: "h-10 w-10",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
)

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
  VariantProps<typeof buttonVariants> {
  asChild?: boolean
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : "button"
    return (
      <Comp
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        {...props}
      />
    )
  }
)
Button.displayName = "Button"

export { Button, buttonVariants }

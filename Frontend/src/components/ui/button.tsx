import * as React from "react"
import { Slot } from "@radix-ui/react-slot"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-lg text-sm font-medium transition-all duration-300 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0",
  {
    variants: {
      variant: {
        default:
          "bg-gradient-to-r from-[#00FF73] to-[#00D95F] text-[#0B132B] font-semibold shadow-lg hover:shadow-[0_0_20px_rgba(0,255,115,0.5)] hover:scale-105 active:scale-95",
        destructive:
          "bg-[#FF4C4C] text-white shadow-sm hover:bg-[#FF3333] hover:shadow-[0_0_15px_rgba(255,76,76,0.4)]",
        outline:
          "border border-[#1C2541] bg-transparent text-foreground shadow-sm hover:bg-[#1C2541] hover:border-[#00FF73] hover:text-[#00FF73]",
        secondary:
          "bg-[#1C2541] text-foreground shadow-sm hover:bg-[#25304A] hover:border-[#00FF73]/30 border border-transparent",
        ghost: "hover:bg-[#1C2541] hover:text-[#00FF73] text-muted-foreground",
        link: "text-[#00FF73] underline-offset-4 hover:underline hover:text-[#00D95F]",
      },
      size: {
        default: "h-9 px-4 py-2",
        sm: "h-8 rounded-md px-3 text-xs",
        lg: "h-10 rounded-md px-8",
        icon: "h-9 w-9",
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

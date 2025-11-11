import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"

const badgeVariants = cva(
  "inline-flex items-center rounded-lg border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-[#00FF73] focus:ring-offset-2",
  {
    variants: {
      variant: {
        default:
          "border-transparent bg-[#00FF73] text-[#0B132B] shadow-lg hover:bg-[#00D95F] neon-glow-green",
        secondary:
          "border-transparent bg-[#1C2541] text-white hover:bg-[#25304A]",
        destructive:
          "border-transparent bg-[#FF4C4C] text-white shadow hover:bg-[#FF3333]",
        outline: "text-white border-[#1C2541]",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
)

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return (
    <div className={cn(badgeVariants({ variant }), className)} {...props} />
  )
}

export { Badge, badgeVariants }

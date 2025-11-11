import * as React from "react"

import { cn } from "@/lib/utils"

const Input = React.forwardRef<HTMLInputElement, React.ComponentProps<"input">>(
  ({ className, type, ...props }, ref) => {
    return (
      <input
        type={type}
        className={cn(
          "flex h-9 w-full rounded-lg border border-[#1C2541] bg-[#0B132B] px-3 py-1 text-base text-white shadow-sm transition-all duration-300 file:border-0 file:bg-transparent file:text-sm file:font-medium file:text-foreground placeholder:text-[#B0B3C5] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#00FF73] focus-visible:border-[#00FF73] disabled:cursor-not-allowed disabled:opacity-50 md:text-sm",
          className
        )}
        ref={ref}
        {...props}
      />
    )
  }
)
Input.displayName = "Input"

export { Input }

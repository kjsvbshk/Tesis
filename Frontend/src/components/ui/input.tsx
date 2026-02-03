import * as React from "react"

import { cn } from "@/lib/utils"

const Input = React.forwardRef<HTMLInputElement, React.ComponentProps<"input">>(
  ({ className, type, ...props }, ref) => {
    return (
      <div className="relative group w-full">
        <input
          type={type}
          className={cn(
            "flex h-10 w-full bg-metal-900 border-b border-chrome-grey px-3 py-2 text-base text-foreground file:border-0 file:bg-transparent file:text-sm file:font-medium file:text-foreground placeholder:text-muted-foreground focus-visible:outline-none focus:border-acid-500 focus:shadow-[0_1px_10px_rgba(204,255,0,0.1)] transition-all duration-300 font-mono text-sm disabled:cursor-not-allowed disabled:opacity-50",
            className
          )}
          ref={ref}
          {...props}
        />
        {/* Corner accent */}
        <div className="absolute top-0 right-0 w-2 h-2 border-t border-r border-transparent group-focus-within:border-acid-500 transition-colors duration-300" />
      </div>
    )
  }
)
Input.displayName = "Input"

export { Input }

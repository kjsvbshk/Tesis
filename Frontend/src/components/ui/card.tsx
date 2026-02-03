import * as React from "react"

import { cn } from "@/lib/utils"

const Card = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn(
      "relative border border-chrome-grey/40 bg-metal-500/80 text-card-foreground shadow-none backdrop-blur-md overflow-hidden",
      className
    )}
    {...props}
  >
    {/* Decorative Technical Corners */}
    <div className="absolute top-0 left-0 w-3 h-3 border-l-2 border-t-2 border-acid-500/30 -translate-x-[1px] -translate-y-[1px]" />
    <div className="absolute top-0 right-0 w-3 h-3 border-r-2 border-t-2 border-acid-500/30 translate-x-[1px] -translate-y-[1px]" />
    <div className="absolute bottom-0 left-0 w-3 h-3 border-l-2 border-b-2 border-acid-500/30 -translate-x-[1px] translate-y-[1px]" />
    <div className="absolute bottom-0 right-0 w-3 h-3 border-r-2 border-b-2 border-acid-500/30 translate-x-[1px] translate-y-[1px]" />

    {props.children}
  </div>
))
Card.displayName = "Card"

const CardHeader = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn("flex flex-col space-y-1.5 p-6 border-b border-chrome-grey/20", className)}
    {...props}
  />
))
CardHeader.displayName = "CardHeader"

const CardTitle = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn("font-display text-lg font-bold uppercase tracking-widest text-foreground", className)}
    {...props}
  />
))
CardTitle.displayName = "CardTitle"

const CardDescription = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn("text-sm text-muted-foreground font-mono", className)}
    {...props}
  />
))
CardDescription.displayName = "CardDescription"

const CardContent = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div ref={ref} className={cn("p-6", className)} {...props} />
))
CardContent.displayName = "CardContent"

const CardFooter = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn("flex items-center p-6 pt-0 border-t border-chrome-grey/20 bg-black/20 mt-auto", className)}
    {...props}
  />
))
CardFooter.displayName = "CardFooter"

export { Card, CardHeader, CardFooter, CardTitle, CardDescription, CardContent }

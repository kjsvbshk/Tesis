import * as React from "react"

import { cn } from "@/lib/utils"

const Table = ({
  className,
  ref,
  ...props
}: React.HTMLAttributes<HTMLTableElement> & { ref?: React.Ref<HTMLTableElement> }) => (
  <div className="relative w-full overflow-auto">
    <table
      ref={ref}
      className={cn("w-full caption-bottom text-sm", className)}
      {...props}
    />
  </div>
)
Table.displayName = "Table"

const TableHeader = ({
  className,
  ref,
  ...props
}: React.HTMLAttributes<HTMLTableSectionElement> & { ref?: React.Ref<HTMLTableSectionElement> }) => (
  <thead ref={ref} className={cn("[&_tr]:border-b", className)} {...props} />
)
TableHeader.displayName = "TableHeader"

const TableBody = ({
  className,
  ref,
  ...props
}: React.HTMLAttributes<HTMLTableSectionElement> & { ref?: React.Ref<HTMLTableSectionElement> }) => (
  <tbody
    ref={ref}
    className={cn("[&_tr:last-child]:border-0", className)}
    {...props}
  />
)
TableBody.displayName = "TableBody"

const TableFooter = ({
  className,
  ref,
  ...props
}: React.HTMLAttributes<HTMLTableSectionElement> & { ref?: React.Ref<HTMLTableSectionElement> }) => (
  <tfoot
    ref={ref}
    className={cn(
      "border-t bg-muted/50 font-medium [&>tr]:last:border-b-0",
      className
    )}
    {...props}
  />
)
TableFooter.displayName = "TableFooter"

const TableRow = ({
  className,
  ref,
  ...props
}: React.HTMLAttributes<HTMLTableRowElement> & { ref?: React.Ref<HTMLTableRowElement> }) => (
  <tr
    ref={ref}
    className={cn(
      "border-b border-[#1C2541]/50 transition-colors hover:bg-[#1C2541]/30 data-[state=selected]:bg-[#1C2541]",
      className
    )}
    {...props}
  />
)
TableRow.displayName = "TableRow"

const TableHead = ({
  className,
  ref,
  ...props
}: React.ThHTMLAttributes<HTMLTableCellElement> & { ref?: React.Ref<HTMLTableCellElement> }) => (
  <th
    ref={ref}
    className={cn(
      "h-10 px-2 text-left align-middle font-medium text-muted-foreground [&:has([role=checkbox])]:pr-0 [&>[role=checkbox]]:translate-y-[2px]",
      className
    )}
    {...props}
  />
)
TableHead.displayName = "TableHead"

const TableCell = ({
  className,
  ref,
  ...props
}: React.TdHTMLAttributes<HTMLTableCellElement> & { ref?: React.Ref<HTMLTableCellElement> }) => (
  <td
    ref={ref}
    className={cn(
      "p-2 align-middle [&:has([role=checkbox])]:pr-0 [&>[role=checkbox]]:translate-y-[2px]",
      className
    )}
    {...props}
  />
)
TableCell.displayName = "TableCell"

const TableCaption = ({
  className,
  ref,
  ...props
}: React.HTMLAttributes<HTMLTableCaptionElement> & { ref?: React.Ref<HTMLTableCaptionElement> }) => (
  <caption
    ref={ref}
    className={cn("mt-4 text-sm text-muted-foreground", className)}
    {...props}
  />
)
TableCaption.displayName = "TableCaption"

export {
  Table,
  TableHeader,
  TableBody,
  TableFooter,
  TableHead,
  TableRow,
  TableCell,
  TableCaption,
}

import { Button } from "@/components/ui/button";
import { ChevronLeft, ChevronRight } from "lucide-react";

interface TablePaginationProps {
  page: number;
  totalPages: number;
  onPageChange: (page: number) => void;
  totalItems?: number;
  pageSize?: number;
}

// Build a windowed list of page numbers (max 5) centred on the current page.
function pageWindow(page: number, totalPages: number): number[] {
  const max = 5;
  if (totalPages <= max) {
    return Array.from({ length: totalPages }, (_, i) => i + 1);
  }
  let start = Math.max(1, page - 2);
  let end = start + max - 1;
  if (end > totalPages) {
    end = totalPages;
    start = end - max + 1;
  }
  return Array.from({ length: end - start + 1 }, (_, i) => start + i);
}

export function TablePagination({
  page,
  totalPages,
  onPageChange,
  totalItems,
  pageSize,
}: TablePaginationProps) {
  if (!totalItems) return null;

  const showRange = totalItems != null && pageSize != null;
  const from = (page - 1) * (pageSize ?? 0) + 1;
  const to = Math.min(page * (pageSize ?? 0), totalItems ?? 0);

  return (
    <div className="flex flex-col items-center justify-between gap-3 border-t border-border px-4 py-3 sm:flex-row">
      {showRange && (
        <p className="text-sm text-muted-foreground">
          Showing <span className="font-medium text-foreground">{from}</span>–
          <span className="font-medium text-foreground">{to}</span> of{" "}
          <span className="font-medium text-foreground">{totalItems}</span>
        </p>
      )}

      {totalPages > 1 && (
        <div className="flex items-center gap-1">
          <Button
            variant="outline"
            size="icon"
            className="h-8 w-8"
            disabled={page <= 1}
            onClick={() => onPageChange(page - 1)}
            aria-label="Previous page"
          >
            <ChevronLeft className="h-4 w-4" />
          </Button>
          {pageWindow(page, totalPages).map((p) => (
            <Button
              key={p}
              variant={p === page ? "default" : "outline"}
              size="icon"
              className="h-8 w-8"
              onClick={() => onPageChange(p)}
              aria-current={p === page ? "page" : undefined}
            >
              {p}
            </Button>
          ))}
          <Button
            variant="outline"
            size="icon"
            className="h-8 w-8"
            disabled={page >= totalPages}
            onClick={() => onPageChange(page + 1)}
            aria-label="Next page"
          >
            <ChevronRight className="h-4 w-4" />
          </Button>
        </div>
      )}
    </div>
  );
}

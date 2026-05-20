/**
 * cn - A standard lightweight className merger.
 * Filters out falsy values and joins classes with a space.
 * When you install clsx and tailwind-merge later, you can replace this
 * with the standard shadcn definition: twMerge(clsx(inputs))
 */
export function cn(...inputs: any[]): string {
  return inputs.filter(Boolean).join(" ");
}

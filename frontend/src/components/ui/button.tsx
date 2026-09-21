import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import type { ButtonHTMLAttributes } from "react";
import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 rounded-lg text-sm font-medium transition-[background-color,color,box-shadow,transform] duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--indigo)] focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 active:translate-y-px",
  {
    variants: {
      variant: {
        primary:
          "bg-[var(--indigo)] px-4 py-2.5 text-white shadow-[0_8px_20px_rgba(74,79,139,0.18)] hover:bg-[#4d528e]",
        secondary:
          "border border-[var(--line)] bg-white/60 px-4 py-2.5 text-[var(--ink)] shadow-sm backdrop-blur-md hover:bg-white/85",
        ghost: "px-3 py-2 text-[var(--muted)] hover:bg-white/55 hover:text-[var(--ink)]",
      },
      size: {
        default: "h-10",
        small: "h-8 text-xs",
      },
    },
    defaultVariants: { variant: "primary", size: "default" },
  },
);

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> &
  VariantProps<typeof buttonVariants> & { asChild?: boolean };

export function Button({ className, variant, size, asChild, ...props }: ButtonProps) {
  const Component = asChild ? Slot : "button";
  return <Component className={cn(buttonVariants({ variant, size }), className)} {...props} />;
}

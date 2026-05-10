import { cn } from "@/lib/utils";

interface DatachatLogoProps {
  className?: string;
  size?: number;
}

/**
 * Datachat logo: a chat bubble containing a bar chart,
 * representing an AI-powered data conversation tool.
 */
export function DatachatLogo({ className, size = 24 }: DatachatLogoProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={cn("shrink-0", className)}
    >
      {/* Chat bubble */}
      <path
        d="M4 4h16a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2h-4l-4 4v-4H4a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2z"
        fill="currentColor"
        opacity="0.15"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinejoin="round"
      />
      {/* Bar chart inside bubble */}
      <rect x="7" y="12" width="2.5" height="3" rx="0.5" fill="currentColor" />
      <rect x="10.75" y="9" width="2.5" height="6" rx="0.5" fill="currentColor" />
      <rect x="14.5" y="7" width="2.5" height="8" rx="0.5" fill="currentColor" />
    </svg>
  );
}
